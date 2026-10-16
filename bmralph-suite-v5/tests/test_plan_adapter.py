"""活动计划写回的真实证据与反例；不证明账号隔离或全计划完成。"""
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
import bmad_plan_adapter as adapter
import bmad_state as state
from bmad_supervisor import SupervisorError


class PlanAdapterGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sandbox-adapter-", dir=SUITE.parent / "tests")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "tests").mkdir()
        (self.root / "tests/test_sample.py").write_text(
            "import unittest\nclass Sample(unittest.TestCase):\n"
            "    def test_sample(self):\n        self.assertTrue(True)\n", encoding="utf-8")
        (self.root / "implementation.py").write_text("VALUE = 1\n", encoding="utf-8")
        environment.register(self.root, ".bmad-control/environment.json", sys.executable)
        self.verification = {
            "operation": "unit-test", "environment_file": ".bmad-control/environment.json",
            "directory": "tests", "pattern": "test_sample.py", "minimum_tests": 1,
            "required_tests": ["test_sample.Sample.test_sample"], "inputs": ["implementation.py"],
        }
        self.data = {"schema_version": 1, "plan_id": "ADAPTER-01", "tasks": [
            {"task_id": key, "title": "未完成事项 " + key, "depends_on": deps,
             "status": "PENDING", "verification": copy.deepcopy(self.verification), "verdict_file": None}
            for key, deps in (("T1", []), ("T2", ["T1"]))
        ]}
        self.prefix = '---\nplan_id: "ADAPTER-01"\nstatus: READY\n---\n\n# 稳定契约\n\n'
        self.suffix = '\n## 范围外承诺\n- [ ] 不得丢失\n'
        self.write_plan()

    def write_plan(self):
        (self.root / "plan.md").write_text(self.prefix + "```bmad-tasks\n" +
            json.dumps(self.data, ensure_ascii=False) + "\n```\n" + self.suffix, encoding="utf-8")
        self.identity = environment.fingerprint(self.root / "plan.md")

    def verdict(self):
        v = self.verification
        result = execution.unit_test(workspace=self.root, environment_file=v["environment_file"],
            directory=v["directory"], pattern=v["pattern"], minimum_tests=v["minimum_tests"],
            required_tests=tuple(v["required_tests"]), inputs=tuple(v["inputs"]))
        self.assertEqual(result["status"], "PASS", result)
        return result["verdict_path"]

    def complete(self, verdict):
        return adapter.complete(workspace=self.root, plan_file="plan.md", task_id="T1",
            verdict_file=verdict, expected_identity=self.identity)

    def test_real_receipt_saves_only_one_task_and_preserves_contract_without_reexecution(self):
        verdict = self.verdict()
        with patch.object(execution, "run") as business:
            result = self.complete(verdict)
        business.assert_not_called()
        saved, _, _ = state.load_plan(self.root, "plan.md")
        self.assertEqual(saved["tasks"][0]["status"], "COMPLETED")
        self.assertEqual(saved["tasks"][1], self.data["tasks"][1])
        content = (self.root / "plan.md").read_text(encoding="utf-8")
        self.assertTrue(content.startswith(self.prefix))
        self.assertTrue(content.endswith(self.suffix))
        self.assertTrue(result["task_progress_saved"])
        view = adapter.query(workspace=self.root, plan_file="plan.md")
        self.assertEqual(view["ready_tasks"], ["T2"])
        self.assertLessEqual(view["view_lines"], 80)
        self.assertEqual(view["unfinished_count"], 1)

    def test_missing_or_changed_evidence_never_saves_completion(self):
        verdict = self.verdict()
        (self.root / "implementation.py").write_text("VALUE = 2\n", encoding="utf-8")
        original = (self.root / "plan.md").read_bytes()
        for path in (verdict, "missing.json"):
            with self.subTest(path=path), self.assertRaises(SupervisorError):
                self.complete(path)
        self.assertEqual((self.root / "plan.md").read_bytes(), original)

    def test_external_plan_change_is_preserved(self):
        verdict = self.verdict()
        external = (self.root / "plan.md").read_bytes() + b"\nexternal\n"
        (self.root / "plan.md").write_bytes(external)
        with self.assertRaises(SupervisorError):
            self.complete(verdict)
        self.assertEqual((self.root / "plan.md").read_bytes(), external)

    def test_change_during_evidence_check_is_not_overwritten(self):
        verdict = self.verdict()
        original_check = state.completed_evidence
        external = (self.root / "plan.md").read_bytes() + b"\nexternal\n"
        def change(root, task):
            result = original_check(root, task)
            (self.root / "plan.md").write_bytes(external)
            return result
        with patch.object(state, "completed_evidence", side_effect=change):
            with self.assertRaises(SupervisorError):
                self.complete(verdict)
        self.assertEqual((self.root / "plan.md").read_bytes(), external)

    def test_suspended_task_and_mismatched_selection_cannot_be_completed(self):
        verdict = self.verdict()
        for change in ("suspended", "selection"):
            with self.subTest(change=change):
                if change == "suspended":
                    self.data["tasks"][0]["status"] = "SUSPENDED"
                else:
                    self.data["tasks"][0]["status"] = "PENDING"
                    self.data["tasks"][0]["verification"]["minimum_tests"] = 2
                self.write_plan()
                original = (self.root / "plan.md").read_bytes()
                with self.assertRaises(SupervisorError):
                    self.complete(verdict)
                self.assertEqual((self.root / "plan.md").read_bytes(), original)

    def test_atomic_save_failure_preserves_source_and_removes_temporary(self):
        verdict = self.verdict()
        original = (self.root / "plan.md").read_bytes()
        with patch.object(adapter.os, "replace", side_effect=OSError("模拟磁盘保存失败")):
            with self.assertRaises(OSError):
                self.complete(verdict)
        self.assertEqual((self.root / "plan.md").read_bytes(), original)
        self.assertEqual(list(self.root.glob(".bmad-plan-*.tmp")), [])


    def test_refresh_completed_reuses_fresh_evidence_without_business_reexecution(self):
        old_verdict = self.verdict()
        self.complete(old_verdict)
        before, _, identity = state.load_plan(self.root, "plan.md")
        (self.root / "implementation.py").write_text("VALUE = 2\n", encoding="utf-8")
        self.assertEqual(adapter.query(workspace=self.root, plan_file="plan.md")["status"], "BLOCKED")
        fresh = self.verdict()
        with patch.object(execution, "run") as business:
            result = adapter.refresh_completed(
                workspace=self.root, plan_file="plan.md", verdict_files={"T1": fresh},
                expected_identity=identity)
        business.assert_not_called()
        saved, _, _ = state.load_plan(self.root, "plan.md")
        self.assertEqual(saved["tasks"][0]["status"], "COMPLETED")
        self.assertEqual(saved["tasks"][0]["verdict_file"], fresh)
        self.assertEqual(saved["tasks"][1], before["tasks"][1])
        self.assertEqual(result["refreshed_tasks"], ["T1"])
        self.assertFalse(result["business_reexecuted"])
        self.assertEqual(adapter.query(workspace=self.root, plan_file="plan.md")["ready_tasks"], ["T2"])
        content = (self.root / "plan.md").read_text()
        self.assertTrue(content.startswith(self.prefix))
        self.assertTrue(content.endswith(self.suffix))
        self.assertTrue((self.root / old_verdict).exists())

    def test_refresh_cannot_complete_pending_or_suspended_task(self):
        verdict = self.verdict()
        for status in ("PENDING", "SUSPENDED"):
            with self.subTest(status=status):
                self.data["tasks"][0]["status"] = status
                self.write_plan()
                before = (self.root / "plan.md").read_bytes()
                with self.assertRaisesRegex(SupervisorError, "仅接受原完成项"):
                    adapter.refresh_completed(
                        workspace=self.root, plan_file="plan.md", verdict_files={"T1": verdict},
                        expected_identity=self.identity)
                self.assertEqual((self.root / "plan.md").read_bytes(), before)

    def test_refresh_all_affected_completed_dependencies_atomically(self):
        old = self.verdict()
        self.complete(old)
        _, _, identity = state.load_plan(self.root, "plan.md")
        adapter.complete(workspace=self.root, plan_file="plan.md", task_id="T2",
                         verdict_file=old, expected_identity=identity)
        _, _, identity = state.load_plan(self.root, "plan.md")
        (self.root / "implementation.py").write_text("VALUE = 3\n", encoding="utf-8")
        fresh = self.verdict()
        before = (self.root / "plan.md").read_bytes()
        with self.assertRaises(SupervisorError):
            adapter.refresh_completed(workspace=self.root, plan_file="plan.md",
                                      verdict_files={"T2": fresh}, expected_identity=identity)
        self.assertEqual((self.root / "plan.md").read_bytes(), before)
        adapter.refresh_completed(workspace=self.root, plan_file="plan.md",
                                  verdict_files={"T1": fresh, "T2": fresh}, expected_identity=identity)
        self.assertEqual(adapter.query(workspace=self.root, plan_file="plan.md")["status"], "COMPLETED")

    def test_refresh_external_change_and_atomic_failure_preserve_plan(self):
        old = self.verdict()
        self.complete(old)
        _, _, identity = state.load_plan(self.root, "plan.md")
        fresh = self.verdict()
        before = (self.root / "plan.md").read_bytes()
        with patch.object(adapter.os, "replace", side_effect=OSError("刷新保存失败")):
            with self.assertRaises(OSError):
                adapter.refresh_completed(workspace=self.root, plan_file="plan.md",
                                          verdict_files={"T1": fresh}, expected_identity=identity)
        self.assertEqual((self.root / "plan.md").read_bytes(), before)
        self.assertEqual(list(self.root.glob(".bmad-plan-*.tmp")), [])
        external = before + b"\nexternal change\n"
        (self.root / "plan.md").write_bytes(external)
        with self.assertRaisesRegex(SupervisorError, "绑定计划变化"):
            adapter.refresh_completed(workspace=self.root, plan_file="plan.md",
                                      verdict_files={"T1": fresh}, expected_identity=identity)
        self.assertEqual((self.root / "plan.md").read_bytes(), external)


if __name__ == "__main__":
    unittest.main()
