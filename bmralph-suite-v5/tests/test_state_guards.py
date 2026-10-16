"""类型化任务清单只读投影反例；项目内独立夹具，不迁移活动计划。

完成项使用真实本机单测回执；查询不重跑业务、不保存第二份状态。
通过不证明宿主权限、远程运行时或当前全计划已经完成。
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "scripts"))
import bmad_environment as environment
import bmad_execution as execution
import bmad_state as state


class StateGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="sandbox-state-", dir=SUITE.parent / "tests"
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace with 'quote'"
        self.root.mkdir()
        self.plan_file = "plan.md"
        self.plan_path = self.root / self.plan_file
        self.plan_id = "STATE-GUARDS-LOCAL-01"
        self.data = {
            "schema_version": 1, "plan_id": self.plan_id,
            "tasks": [self.task("T1"), self.task("T2", depends_on=["T1"])],
        }
        self.write_plan()

    def task(self, key, *, depends_on=None, status="PENDING", verdict_file=None):
        return {
            "task_id": key, "title": "保留未完成任务 " + key,
            "depends_on": [] if depends_on is None else depends_on,
            "status": status,
            "verification": {
                "operation": "unit-test",
                "environment_file": ".bmad-control/environment.json",
                "directory": "tests", "pattern": "test_*.py",
                "minimum_tests": 1,
                "required_tests": ["test_sample.Sample.test_sample"],
                "inputs": ["implementation.py"],
            },
            "verdict_file": verdict_file,
        }

    def write_plan(self, data=None, *, frontmatter_id=None, suffix=""):
        data = self.data if data is None else data
        plan_id = self.plan_id if frontmatter_id is None else frontmatter_id
        self.plan_path.write_text(
            "---\nplan_id: " + json.dumps(plan_id) + "\nstatus: READY\n---\n"
            "\n# 只读状态夹具\n\n```bmad-tasks\n" +
            json.dumps(data, ensure_ascii=False) + "\n```\n" + suffix,
            encoding="utf-8",
        )

    def files(self):
        return {
            path.relative_to(self.root).as_posix(): path.read_bytes()
            for path in self.root.rglob("*") if path.is_file()
        }

    def render(self, **kwargs):
        before = self.files()
        with patch.object(execution, "run") as business:
            result = state.render_state(
                workspace=self.root, plan_file=self.plan_file, **kwargs
            )
        business.assert_not_called()
        self.assertIs(result["business_reexecuted"], False)
        self.assertIs(result["state_saved"], False)
        self.assertEqual(self.files(), before)
        return result

    def assert_blocked(self, result):
        self.assertEqual(result["status"], "BLOCKED", result)
        if "view" not in result:
            self.assertTrue(result["reason"])

    def complete_first_with_real_receipt(self):
        tests = self.root / "tests"
        tests.mkdir()
        (tests / "test_sample.py").write_text(
            "import unittest\n\nclass Sample(unittest.TestCase):\n"
            "    def test_sample(self):\n"
            "        self.assertEqual(2 + 2, 4)\n", encoding="utf-8",
        )
        (self.root / "implementation.py").write_text("VALUE = 1\n", encoding="utf-8")
        manifest = ".bmad-control/environment.json"
        environment.register(self.root, manifest, sys.executable)
        verdict = execution.unit_test(
            workspace=self.root, environment_file=manifest,
            directory="tests", pattern="test_*.py",
            required_tests=("test_sample.Sample.test_sample",),
            inputs=("implementation.py",),
        )
        self.assertEqual(verdict["status"], "PASS", verdict)
        self.data["tasks"][0].update(
            status="COMPLETED", verdict_file=verdict["verdict_path"]
        )
        self.write_plan()
        return verdict

    def test_pending_tasks_remain_visible_and_only_dependency_ready_task_selected(self):
        result = self.render()
        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["ready_tasks"], ["T1"])
        self.assertEqual(result["unfinished_count"], 2)
        self.assertIn("T1 [READY]", result["view"])
        self.assertIn("T2 [PENDING]", result["view"])
        self.assertLessEqual(result["view_lines"], 80)
        self.assertEqual(result["view_bytes"], len(result["view"].encode("utf-8")))
        self.assertFalse((self.root / ".bmad-control").exists())

    def test_real_completed_evidence_releases_only_its_dependant_without_retesting(self):
        verdict = self.complete_first_with_real_receipt()
        result = self.render()
        self.assertEqual(result["ready_tasks"], ["T2"], result)
        self.assertEqual(result["unfinished_count"], 1)
        self.assertIn("T1 [COMPLETED]", result["view"])
        self.assertIn(verdict["verdict_path"], result["view"])
        self.assertEqual(len(list((self.root / ".bmad-runtime").glob("*.log"))), 1)

    def test_changed_source_blocks_old_completion_and_dependant(self):
        self.complete_first_with_real_receipt()
        (self.root / "implementation.py").write_text("VALUE = 2\n", encoding="utf-8")
        result = self.render()
        self.assert_blocked(result)
        self.assertEqual(result["ready_tasks"], [])
        self.assertEqual(result["unfinished_count"], 2)
        self.assertIn("T1 [BLOCKED]", result["view"])
        self.assertIn("T2 [PENDING]", result["view"])

    def test_current_task_contract_must_exactly_match_receipt(self):
        self.complete_first_with_real_receipt()
        original = copy.deepcopy(self.data)
        for change in (
            {"pattern": "test_sample.py"}, {"minimum_tests": 2},
            {"required_tests": []}, {"inputs": []},
            {"environment_file": ".bmad-control/other.json"},
        ):
            with self.subTest(change=change):
                self.data = copy.deepcopy(original)
                self.data["tasks"][0]["verification"].update(change)
                self.write_plan()
                result = self.render()
                self.assert_blocked(result)
                self.assertEqual(result["ready_tasks"], [])

    def test_valid_receipt_alone_does_not_complete_pending_task(self):
        self.complete_first_with_real_receipt()
        self.data["tasks"][0]["status"] = "PENDING"
        self.write_plan()
        result = self.render()
        self.assertEqual(result["ready_tasks"], ["T1"])
        self.assertEqual(result["unfinished_count"], 2)
        self.assertNotIn("[COMPLETED]", result["view"])

    def test_unrelated_notes_do_not_invalidate_completion(self):
        self.complete_first_with_real_receipt()
        (self.root / "notes.md").write_text("unrelated notes\n", encoding="utf-8")
        result = self.render()
        self.assertEqual(result["ready_tasks"], ["T2"], result)

    def test_completed_item_without_receipt_is_not_a_completion_fact(self):
        self.data["tasks"][0]["status"] = "COMPLETED"
        self.write_plan()
        self.assert_blocked(self.render())

    def test_missing_receipt_blocks_completed_item_and_preserves_all_tasks(self):
        self.data["tasks"][0].update(
            status="COMPLETED", verdict_file=".bmad-runtime/missing.verdict.json"
        )
        self.write_plan()
        result = self.render()
        self.assert_blocked(result)
        self.assertEqual(result["unfinished_count"], 2)
        self.assertIn("T1 [BLOCKED]", result["view"])
        self.assertIn("T2 [PENDING]", result["view"])

    def test_invalid_completed_dependency_propagates_without_claiming_downstream_pass(self):
        for task in self.data["tasks"]:
            task.update(status="COMPLETED", verdict_file="missing.verdict.json")
        self.write_plan()
        result = self.render()
        self.assert_blocked(result)
        self.assertEqual(result["unfinished_count"], 2)
        self.assertEqual(result["ready_tasks"], [])
        self.assertNotIn("[COMPLETED]", result["view"])

    def test_suspended_tasks_do_not_become_ready_or_resume_implicitly(self):
        self.data["tasks"][0]["status"] = "SUSPENDED"
        self.write_plan()
        result = self.render()
        self.assertEqual(result["status"], "SUSPENDED")
        self.assertEqual(result["ready_tasks"], [])
        self.assertEqual(result["unfinished_count"], 2)
        self.assertIn("T1 [SUSPENDED]", result["view"])

    def test_explicit_blocked_task_does_not_release_dependant(self):
        self.data["tasks"][0]["status"] = "BLOCKED"
        self.write_plan()
        result = self.render()
        self.assert_blocked(result)
        self.assertEqual(result["ready_tasks"], [])

    def test_eighty_line_boundary_retains_every_pending_task(self):
        self.data["tasks"] = [self.task(f"T{index}") for index in range(77)]
        self.write_plan()
        result = self.render()
        self.assertEqual(result["view_lines"], 80, result)
        self.assertEqual(result["unfinished_count"], 77)
        self.assertEqual(len(result["ready_tasks"]), 77)
        self.assertIn("T76 [READY]", result["view"])

    def test_line_overflow_blocks_instead_of_truncating_unfinished_tasks(self):
        self.data["tasks"] = [self.task(f"T{index}") for index in range(78)]
        self.write_plan()
        result = self.render()
        self.assert_blocked(result)
        self.assertNotIn("view", result)
        self.assertEqual(len(self.data["tasks"]), 78)

    def test_multibyte_byte_budget_blocks_even_when_line_count_fits(self):
        self.data["tasks"][0]["title"] = "中文预算" * 100
        self.write_plan()
        result = self.render(maximum_bytes=256)
        self.assert_blocked(result)
        self.assertNotIn("view", result)

    def test_invalid_or_increased_budgets_fail_closed(self):
        for budgets in (
            {"maximum_lines": 81}, {"maximum_lines": 0},
            {"maximum_lines": True}, {"maximum_bytes": 16385},
            {"maximum_bytes": 255}, {"maximum_bytes": True},
        ):
            with self.subTest(budgets=budgets):
                self.assert_blocked(self.render(**budgets))

    def test_duplicate_missing_self_and_cyclic_dependencies_are_rejected(self):
        original = copy.deepcopy(self.data)
        for variant in ("duplicate", "missing", "self", "cycle"):
            with self.subTest(variant=variant):
                self.data = copy.deepcopy(original)
                if variant == "duplicate":
                    self.data["tasks"][1]["task_id"] = "T1"
                elif variant == "missing":
                    self.data["tasks"][1]["depends_on"] = ["ABSENT"]
                elif variant == "self":
                    self.data["tasks"][0]["depends_on"] = ["T1"]
                else:
                    self.data["tasks"][0]["depends_on"] = ["T2"]
                self.write_plan()
                self.assert_blocked(self.render())

    def test_unsupported_operation_and_schema_do_not_silently_fall_back(self):
        original = copy.deepcopy(self.data)
        for mutate in (
            lambda data: data.update(schema_version=True),
            lambda data: data.update(schema_version=2),
            lambda data: data.update(tasks=[]),
            lambda data: data.update(extra="unsupported"),
            lambda data: data["tasks"][0]["verification"].update(operation="shell"),
            lambda data: data["tasks"][0].update(status="READY"),
        ):
            with self.subTest(mutate=mutate):
                self.data = copy.deepcopy(original)
                mutate(self.data)
                self.write_plan()
                self.assert_blocked(self.render())

    def test_task_count_budget_is_enforced_before_view_construction(self):
        self.data["tasks"] = [self.task(f"T{index}") for index in range(257)]
        self.write_plan()
        self.assert_blocked(self.render())

    def test_duplicate_json_keys_are_rejected(self):
        text = self.plan_path.read_text(encoding="utf-8")
        self.plan_path.write_text(
            text.replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1'),
            encoding="utf-8",
        )
        self.assert_blocked(self.render())

    def test_plain_legacy_plan_is_not_migrated_or_interpreted_as_typed_progress(self):
        self.plan_path.write_text(
            '---\nplan_id: "STATE-GUARDS-LOCAL-01"\n---\n\n- [x] old completion\n',
            encoding="utf-8",
        )
        result = self.render()
        self.assert_blocked(result)
        self.assertIn("平台记录", result["reason"])

    def test_multiple_task_blocks_are_rejected(self):
        self.write_plan(suffix="\n```bmad-tasks\n{}\n```\n")
        self.assert_blocked(self.render())

    def test_frontmatter_and_task_plan_identity_must_match(self):
        self.write_plan(frontmatter_id="DIFFERENT-PLAN")
        self.assert_blocked(self.render())

    def test_duplicate_frontmatter_plan_identity_is_rejected(self):
        text = self.plan_path.read_text(encoding="utf-8")
        self.plan_path.write_text(
            text.replace("status: READY", 'plan_id: "DUPLICATE"\nstatus: READY'),
            encoding="utf-8",
        )
        self.assert_blocked(self.render())

    def test_missing_explicit_plan_does_not_select_another_candidate(self):
        self.plan_path.unlink()
        alternate = self.root / "_bmad-output"
        alternate.mkdir()
        (alternate / "pending_implementation_plan.md").write_text(
            "unrelated candidate\n", encoding="utf-8"
        )
        self.assert_blocked(self.render())
        self.assertFalse(self.plan_path.exists())

    def test_symlink_and_escape_plan_paths_are_rejected(self):
        alias = self.root / "alias.md"
        alias.symlink_to(self.plan_path)
        for relative in ("alias.md", "../outside.md", str(self.plan_path)):
            with self.subTest(relative=relative):
                result = state.render_state(workspace=self.root, plan_file=relative)
                self.assert_blocked(result)
                self.assertIs(result["state_saved"], False)

    def test_control_characters_and_escape_inputs_do_not_enter_view(self):
        original = copy.deepcopy(self.data)
        for mutate in (
            lambda task: task.update(title="hidden\nconstraint"),
            lambda task: task.update(title="terminal\x1b[31m"),
            lambda task: task["verification"].update(inputs=["../outside.py"]),
            lambda task: task["verification"].update(minimum_tests=True),
            lambda task: task["verification"].update(required_tests=["same", "same"]),
        ):
            with self.subTest(mutate=mutate):
                self.data = copy.deepcopy(original)
                mutate(self.data["tasks"][0])
                self.write_plan()
                self.assert_blocked(self.render())

    def test_plan_byte_budget_blocks_without_rewriting_source(self):
        with patch.object(state, "MAX_PLAN_BYTES", 32):
            self.assert_blocked(self.render())

    def test_plan_change_during_projection_blocks_and_preserves_external_change(self):
        self.data["tasks"][0].update(
            status="COMPLETED", verdict_file="existing.verdict.json"
        )
        self.write_plan()
        external = self.plan_path.read_bytes() + b"\nexternal change\n"

        def change_plan(root, task):
            self.plan_path.write_bytes(external)
            return {"status": "PASS"}

        with patch.object(state, "completed_evidence", side_effect=change_plan):
            result = state.render_state(workspace=self.root, plan_file=self.plan_file)
        self.assert_blocked(result)
        self.assertNotIn("view", result)
        self.assertEqual(self.plan_path.read_bytes(), external)
        self.assertIs(result["state_saved"], False)


if __name__ == "__main__":
    unittest.main()
