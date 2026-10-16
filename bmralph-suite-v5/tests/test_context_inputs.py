"""当前计划和定向源码的只读输入组装反例；不启动 Agent。

仅使用项目内、套件源外的临时工作区。本地通过不证明宿主加载、
认证、远程新会话或调用方声明的授权与反馈有效性。
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "scripts"))
import bmad_context as context
import bmad_context_inputs as inputs
import bmad_environment as environment
import bmad_execution as execution
from bmad_supervisor import SupervisorError


class ContextInputGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="sandbox-context-input-", dir=SUITE.parent / "tests",
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace with 'quote'"
        self.root.mkdir()
        (self.root / "tests").mkdir()
        (self.root / "tests/test_sample.py").write_text(
            "import unittest\n\nclass Sample(unittest.TestCase):\n"
            "    def test_sample(self):\n        self.assertTrue(True)\n",
            encoding="utf-8",
        )
        (self.root / "implementation.py").write_text("VALUE = 1\n", encoding="utf-8")
        (self.root / "unfinished.py").write_text("# 保留未提交成果\n", encoding="utf-8")
        self.manifest = ".bmad-control/environment.json"
        verification = {
            "operation": "unit-test", "environment_file": self.manifest,
            "directory": "tests", "pattern": "test_sample.py",
            "minimum_tests": 1,
            "required_tests": ["test_sample.Sample.test_sample"],
            "inputs": ["implementation.py"],
        }
        self.plan = {
            "schema_version": 1, "plan_id": "CONTEXT-INPUT-LOCAL-01",
            "tasks": [
                {"task_id": "T1", "title": "当前任务", "depends_on": [],
                 "status": "PENDING", "verification": copy.deepcopy(verification),
                 "verdict_file": None},
                {"task_id": "T2", "title": "保留未完成依赖任务", "depends_on": ["T1"],
                 "status": "PENDING", "verification": copy.deepcopy(verification),
                 "verdict_file": None},
            ],
        }
        self.request = {
            "goal": "完成当前获准任务并保留其余待办",
            "authorization": "仅本地项目内实施；不提交、不启动远程任务",
            "task_id": "T1", "constraints": ["不修改 V4 对照源码"],
            "capabilities": ["按需定位当前源码和相关测试"],
            "code_files": ["implementation.py"],
            "unfinished_files": ["unfinished.py"],
            "feedback": ["调用方已核验的最近失败反馈"],
            "observed_host_bytes": None,
        }
        self.save_plan()
        self.save_request()

    def save_plan(self):
        (self.root / "plan.md").write_text(
            '---\nplan_id: "CONTEXT-INPUT-LOCAL-01"\nstatus: READY\n---\n\n'
            '# 本地输入夹具\n\n```bmad-tasks\n' +
            json.dumps(self.plan, ensure_ascii=False) + "\n```\n",
            encoding="utf-8",
        )

    def save_request(self):
        (self.root / "request.json").write_text(
            json.dumps(self.request, ensure_ascii=False), encoding="utf-8",
        )

    def snapshot(self):
        return {
            path.relative_to(self.root).as_posix(): path.read_bytes()
            for path in self.root.rglob("*") if path.is_file()
        }

    def assemble(self, **changes):
        arguments = {
            "workspace": self.root, "plan_file": "plan.md",
            "request_file": "request.json",
        }
        arguments.update(changes)
        before = self.snapshot()
        try:
            return inputs.assemble_plan_input(**arguments)
        finally:
            self.assertEqual(self.snapshot(), before)

    def test_current_task_contract_sources_and_all_pending_items_are_preserved(self):
        result = self.assemble()
        data = json.loads(result["payload"])
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["task_id"], "T1")
        self.assertEqual(data["task"]["verification"], self.plan["tasks"][0]["verification"])
        self.assertIn("T2 [PENDING]", data["state_projection"]["view"])
        self.assertEqual(data["code"], ["来源：implementation.py\nVALUE = 1\n"])
        self.assertEqual(data["unfinished_changes"], ["来源：unfinished.py\n# 保留未提交成果\n"])
        self.assertEqual(data["feedback"], self.request["feedback"])
        self.assertIs(result["business_reexecuted"], False)
        self.assertIs(result["state_saved"], False)
        self.assertEqual(result["host_input_coverage"], "UNKNOWN")
        self.assertIn("仍须调用方核验", result["evidence_boundary"])
        self.assertFalse((self.root / ".bmad-control").exists())
        self.assertFalse((self.root / ".bmad-runtime").exists())

    def test_same_file_in_code_and_unfinished_inputs_remains_in_both_sections(self):
        self.request["unfinished_files"] = ["implementation.py"]
        self.save_request()
        result = self.assemble()
        data = json.loads(result["payload"])
        self.assertEqual(data["code"], data["unfinished_changes"])

    def test_unknown_or_dependency_unready_task_is_not_substituted(self):
        for task_id in ("UNKNOWN", "T2"):
            with self.subTest(task_id=task_id):
                self.request["task_id"] = task_id
                self.save_request()
                with self.assertRaises(context.ContextBlocked):
                    self.assemble()

    def test_suspended_and_blocked_tasks_are_not_resumed(self):
        for status in ("SUSPENDED", "BLOCKED"):
            with self.subTest(status=status):
                self.plan["tasks"][0]["status"] = status
                self.save_plan()
                with self.assertRaises(context.ContextBlocked):
                    self.assemble()

    def test_completed_task_without_receipt_cannot_supply_dependency_readiness(self):
        self.plan["tasks"][0]["status"] = "COMPLETED"
        self.request["task_id"] = "T2"
        self.save_plan()
        self.save_request()
        with self.assertRaises(SupervisorError):
            self.assemble()

    def test_real_receipt_enables_dependency_without_reexecuting_business(self):
        environment.register(self.root, self.manifest, sys.executable)
        verdict = execution.unit_test(
            workspace=self.root, environment_file=self.manifest,
            directory="tests", pattern="test_sample.py", minimum_tests=1,
            required_tests=("test_sample.Sample.test_sample",),
            inputs=("implementation.py",),
        )
        self.assertEqual(verdict["status"], "PASS", verdict["reason"])
        self.plan["tasks"][0].update(status="COMPLETED", verdict_file=verdict["verdict_path"])
        self.request["task_id"] = "T2"
        self.save_plan()
        self.save_request()
        result = self.assemble()
        self.assertEqual(result["task_id"], "T2")
        self.assertEqual(json.loads(result["payload"])["state_projection"]["unfinished_count"], 1)
        self.assertEqual(len(list((self.root / ".bmad-runtime").glob("*.log"))), 1)
        (self.root / "implementation.py").write_text("VALUE = 2\n", encoding="utf-8")
        with self.assertRaises(context.ContextBlocked):
            self.assemble()
        self.assertEqual(len(list((self.root / ".bmad-runtime").glob("*.log"))), 1)

    def test_legacy_plan_is_not_migrated_or_replaced(self):
        (self.root / "plan.md").write_text(
            '---\nplan_id: "CONTEXT-INPUT-LOCAL-01"\n---\n\n- [x] old completion\n',
            encoding="utf-8",
        )
        with self.assertRaises(SupervisorError):
            self.assemble()

    def test_missing_request_or_plan_does_not_create_assets(self):
        for changes in ({"request_file": "missing.json"}, {"plan_file": "missing.md"}):
            with self.subTest(changes=changes):
                with self.assertRaises(SupervisorError):
                    self.assemble(**changes)

    def test_duplicate_json_keys_and_malformed_request_fail_closed(self):
        for content in ('{"goal":"a","goal":"b"}', '[1,2]', '{broken'):
            with self.subTest(content=content):
                (self.root / "request.json").write_text(content, encoding="utf-8")
                with self.assertRaises(context.ContextBlocked):
                    self.assemble()

    def test_request_cannot_supply_state_projection_or_verification(self):
        for field in ("state_projection", "verification", "status"):
            with self.subTest(field=field):
                request = copy.deepcopy(self.request)
                request[field] = "forged completion"
                (self.root / "request.json").write_text(json.dumps(request), encoding="utf-8")
                with self.assertRaises(context.ContextBlocked):
                    self.assemble()

    def test_missing_fields_and_invalid_text_lists_fail_closed(self):
        for field, value in (
            ("goal", ""), ("constraints", "implicit text"),
            ("capabilities", [None]), ("feedback", [""]),
            ("observed_host_bytes", True), ("code_files", [None]),
            ("unfinished_files", ["unfinished.py", "unfinished.py"]),
        ):
            with self.subTest(field=field):
                request = copy.deepcopy(self.request)
                request[field] = value
                (self.root / "request.json").write_text(json.dumps(request), encoding="utf-8")
                with self.assertRaises(SupervisorError):
                    self.assemble()
        request = copy.deepcopy(self.request)
        del request["authorization"]
        (self.root / "request.json").write_text(json.dumps(request), encoding="utf-8")
        with self.assertRaises(context.ContextBlocked):
            self.assemble()

    def test_path_escape_absolute_path_and_symlink_are_rejected(self):
        (self.root / "alias.py").symlink_to(self.root / "implementation.py")
        for relative in ("../outside.py", str(self.root / "implementation.py"), "alias.py"):
            with self.subTest(relative=relative):
                self.request["code_files"] = [relative]
                self.save_request()
                with self.assertRaises(SupervisorError):
                    self.assemble()

    def test_missing_directory_binary_and_empty_source_are_rejected(self):
        (self.root / "binary.py").write_bytes(b"\xff\xfe")
        (self.root / "empty.py").write_text("", encoding="utf-8")
        for relative in ("missing.py", "tests", "binary.py", "empty.py"):
            with self.subTest(relative=relative):
                self.request["code_files"] = [relative]
                self.save_request()
                with self.assertRaises(SupervisorError):
                    self.assemble()

    def test_request_and_source_read_limits_block_without_truncation(self):
        (self.root / "huge.json").write_bytes(b" " * (inputs.MAX_REQUEST_BYTES + 1))
        with self.assertRaises(context.ContextBlocked):
            self.assemble(request_file="huge.json")
        (self.root / "huge.py").write_bytes(b"x" * (inputs.MAX_SOURCE_BYTES + 1))
        self.request["code_files"] = ["huge.py"]
        self.save_request()
        with self.assertRaises(context.ContextBlocked):
            self.assemble()

    def test_cumulative_source_budget_is_not_a_per_file_budget(self):
        for name in ("first.py", "second.py"):
            (self.root / name).write_text("x" * 70000, encoding="utf-8")
        self.request["code_files"] = ["first.py", "second.py"]
        self.save_request()
        with self.assertRaisesRegex(context.ContextBlocked, "累计定向源码"):
            self.assemble(maximum_bytes=context.MAX_STARTUP_BYTES)

    def test_exact_startup_budget_and_observed_host_bytes_are_accounted(self):
        first = self.assemble()
        size = first["accounted_bytes"]
        self.assertEqual(self.assemble(maximum_bytes=size)["accounted_bytes"], size)
        with self.assertRaises(context.ContextBlocked):
            self.assemble(maximum_bytes=size - 1)
        self.request["observed_host_bytes"] = 1000
        self.save_request()
        result = self.assemble()
        self.assertEqual(result["accounted_bytes"], result["controlled_bytes"] + 1000)
        self.assertEqual(result["host_input_coverage"], "PARTIAL_OBSERVATION")

    def test_request_plan_and_source_change_during_assembly_blocks_and_preserves_change(self):
        original = context.assemble_input
        for relative in ("request.json", "plan.md", "implementation.py"):
            with self.subTest(relative=relative):
                self.save_plan()
                self.save_request()
                (self.root / "implementation.py").write_text("VALUE = 1\n", encoding="utf-8")
                def changed(*args, **kwargs):
                    result = original(*args, **kwargs)
                    with (self.root / relative).open("ab") as stream:
                        stream.write(b"\nexternal change\n")
                    return result
                with mock.patch.object(inputs.context, "assemble_input", side_effect=changed):
                    with self.assertRaisesRegex(context.ContextBlocked, "停止对账"):
                        inputs.assemble_plan_input(
                            workspace=self.root, plan_file="plan.md", request_file="request.json",
                        )
                self.assertTrue((self.root / relative).read_bytes().endswith(b"external change\n"))

    def test_no_implicit_history_read_or_verification_execution(self):
        (self.root / "history.txt").write_bytes(b"\xff" * 1000)
        with mock.patch.object(inputs.state.execution, "unit_test", side_effect=AssertionError("must not execute")):
            result = self.assemble()
        self.assertNotIn("history.txt", result["payload"])
        self.assertIs(result["business_reexecuted"], False)


if __name__ == "__main__":
    unittest.main()
