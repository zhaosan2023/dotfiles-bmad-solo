"""保存后证据有效性查询反例；不重跑业务、不写第二份进度。

通过夹具使用真实本机 Python 单测；临时工作区位于项目内、套件源外。
身份复核不等于同账号防篡改，也不覆盖未声明的实现或隐式导入。
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


class EvidenceGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="sandbox-evidence-", dir=SUITE.parent / "tests"
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace with 'quote'"
        self.root.mkdir()
        self.tests = self.root / "tests"
        self.tests.mkdir()
        self.test_file = self.tests / "test_sample.py"
        self.test_file.write_text(
            "import unittest\n\nclass Sample(unittest.TestCase):\n"
            "    def test_sample(self):\n"
            "        self.assertEqual(2 + 2, 4)\n", encoding="utf-8",
        )
        self.source = self.root / "implementation.py"
        self.source.write_text("VALUE = 1\n", encoding="utf-8")
        self.manifest = ".bmad-control/environment.json"
        environment.register(self.root, self.manifest, sys.executable)
        self.verdict = execution.unit_test(
            workspace=self.root, environment_file=self.manifest,
            directory="tests", pattern="test_*.py",
            required_tests=("test_sample.Sample.test_sample",),
            inputs=("implementation.py",),
        )
        self.assertEqual(self.verdict["status"], "PASS", self.verdict)
        self.verdict_file = self.verdict["verdict_path"]
        self.verdict_path = self.root / self.verdict_file
        self.process_path = self.root / self.verdict["process_receipt"]
        self.process = json.loads(self.process_path.read_bytes())
        self.log_path = self.root / self.process["log_path"]

    def query(self):
        with patch.object(execution, "run") as business:
            result = execution.check_evidence(
                workspace=self.root, verdict_file=self.verdict_file,
            )
        business.assert_not_called()
        self.assertIs(result["business_reexecuted"], False)
        return result

    def assert_blocked(self, result):
        self.assertEqual(result["status"], "BLOCKED", result)
        self.assertTrue(result["reason"])

    def revise_verdict(self, mutate):
        data = json.loads(self.verdict_path.read_bytes())
        mutate(data)
        self.verdict_path.write_text(json.dumps(data), encoding="utf-8")

    def revise_process(self, mutate):
        data = json.loads(self.process_path.read_bytes())
        mutate(data)
        self.process_path.write_text(json.dumps(data), encoding="utf-8")
        identity = environment.fingerprint(self.process_path)
        self.revise_verdict(lambda verdict: verdict.update(process_identity=identity))

    def test_unchanged_evidence_queries_pass_without_new_business_or_files(self):
        before = {
            path.relative_to(self.root).as_posix(): path.read_bytes()
            for path in self.root.rglob("*") if path.is_file()
        }
        for _ in range(2):
            result = self.query()
            self.assertEqual(result["status"], "PASS", result)
            self.assertEqual(result["process_receipt"], self.verdict["process_receipt"])
        after = {
            path.relative_to(self.root).as_posix(): path.read_bytes()
            for path in self.root.rglob("*") if path.is_file()
        }
        self.assertEqual(after, before)

    def test_explicit_implementation_edit_invalidates_old_pass(self):
        self.source.write_text("VALUE = 2\n", encoding="utf-8")
        original = self.verdict_path.read_bytes()
        self.assert_blocked(self.query())
        self.assertEqual(self.verdict_path.read_bytes(), original)
        self.assertEqual(self.source.read_text(encoding="utf-8"), "VALUE = 2\n")

    def test_explicit_implementation_deletion_invalidates_old_pass(self):
        self.source.unlink()
        self.assert_blocked(self.query())
        self.assertFalse(self.source.exists())

    def test_test_addition_deletion_and_permission_change_invalidate(self):
        original = self.test_file.read_bytes()
        mode = self.test_file.stat().st_mode & 0o777
        variants = ("addition", "deletion", "permission")
        for variant in variants:
            with self.subTest(variant=variant):
                extra = self.tests / "new-asset.txt"
                if variant == "addition":
                    extra.write_text("new evidence\n", encoding="utf-8")
                elif variant == "deletion":
                    self.test_file.unlink()
                else:
                    self.test_file.chmod(mode ^ 0o100)
                self.assert_blocked(self.query())
                if extra.exists():
                    extra.unlink()
                if not self.test_file.exists():
                    self.test_file.write_bytes(original)
                self.test_file.chmod(mode)
        self.assertEqual(self.query()["status"], "PASS")

    def test_unrelated_notes_and_progress_save_do_not_invalidate(self):
        (self.root / "notes.md").write_text("unrelated notes\n", encoding="utf-8")
        (self.root / "progress.md").write_text("unfinished task remains\n", encoding="utf-8")
        result = self.query()
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(len(list((self.root / ".bmad-runtime").glob("*.log"))), 1)

    def test_environment_manifest_edit_invalidates_without_repair(self):
        path = self.root / self.manifest
        modified = path.read_bytes() + b"\n"
        path.write_bytes(modified)
        self.assert_blocked(self.query())
        self.assertEqual(path.read_bytes(), modified)

    def test_actual_environment_identity_drift_blocks(self):
        actual_check = environment.check

        def changed_environment(*args, **kwargs):
            result = copy.deepcopy(actual_check(*args, **kwargs))
            result["environment"]["details"]["platform"] += " changed"
            return result

        with patch.object(environment, "check", side_effect=changed_environment):
            self.assert_blocked(self.query())

    def test_controller_identity_drift_invalidates_without_editing_source(self):
        actual_collect = execution.collect_evidence

        def changed_controller(*args, **kwargs):
            result = copy.deepcopy(actual_collect(*args, **kwargs))
            result["controller"]["bmad_supervisor.py"]["sha256"] = "0" * 64
            return result

        with patch.object(execution, "collect_evidence", side_effect=changed_controller):
            self.assert_blocked(self.query())

    def test_complete_log_edit_and_deletion_invalidate(self):
        original = self.log_path.read_bytes()
        self.log_path.write_bytes(original + b"external log change\n")
        self.assert_blocked(self.query())
        self.log_path.unlink()
        self.assert_blocked(self.query())
        self.assertFalse(self.log_path.exists())

    def test_process_receipt_edit_and_deletion_invalidate(self):
        self.process_path.write_bytes(self.process_path.read_bytes() + b"\n")
        self.assert_blocked(self.query())
        self.process_path.unlink()
        self.assert_blocked(self.query())
        self.assertFalse(self.process_path.exists())

    def test_missing_verdict_is_not_recreated(self):
        self.verdict_path.unlink()
        self.assert_blocked(self.query())
        self.assertFalse(self.verdict_path.exists())

    def test_old_receipt_without_required_identity_does_not_inherit_pass(self):
        self.revise_verdict(lambda data: data.pop("process_identity"))
        self.assert_blocked(self.query())

    def test_blocked_or_inconsistent_verdict_cannot_become_pass(self):
        original = self.verdict_path.read_bytes()
        for change in (
            lambda data: data.update(status="BLOCKED", reason="actual failure"),
            lambda data: data.update(evidence_after=None),
            lambda data: data.update(cwd=str(self.root / "different-workspace")),
            lambda data: data.update(schema_version=True),
        ):
            with self.subTest(change=change):
                self.verdict_path.write_bytes(original)
                self.revise_verdict(change)
                self.assert_blocked(self.query())

    def test_process_exit_cleanup_and_timeout_contracts_are_rechecked(self):
        original_process = self.process_path.read_bytes()
        original_verdict = self.verdict_path.read_bytes()
        for fields in (
            {"returncode": True}, {"returncode": 7}, {"cleanup_ok": False},
            {"timed_out": True}, {"cancelled": True}, {"timeout_seconds": 600},
        ):
            with self.subTest(fields=fields):
                self.process_path.write_bytes(original_process)
                self.verdict_path.write_bytes(original_verdict)
                self.revise_process(lambda data: data.update(fields))
                self.assert_blocked(self.query())

    def test_process_command_and_target_are_bound_to_selection(self):
        self.revise_process(lambda data: data.update(argv=[sys.executable, "--version"]))
        self.assert_blocked(self.query())

    def test_saved_test_result_must_match_complete_log(self):
        self.revise_verdict(lambda data: data["result"].update(tests_run=2, discovered=2))
        self.assert_blocked(self.query())

    def test_duplicate_and_oversized_verdict_fail_closed(self):
        self.verdict_path.write_text('{"status":"PASS","status":"PASS"}', encoding="utf-8")
        self.assert_blocked(self.query())
        with patch.object(execution, "MAX_RECEIPT_BYTES", 32):
            self.verdict_path.write_bytes(b" " * 33)
            self.assert_blocked(self.query())

    def test_verdict_symlink_is_rejected(self):
        alias = self.root / "verdict-alias.json"
        alias.symlink_to(self.verdict_path)
        result = execution.check_evidence(workspace=self.root, verdict_file="verdict-alias.json")
        self.assert_blocked(result)
        self.assertIs(result["business_reexecuted"], False)

    def test_concurrent_receipt_change_at_query_end_blocks_and_preserves_change(self):
        original_collect = execution.collect_evidence
        modified = self.verdict_path.read_bytes() + b"\n"

        def edit_after_collection(*args, **kwargs):
            result = original_collect(*args, **kwargs)
            self.verdict_path.write_bytes(modified)
            return result

        with patch.object(execution, "collect_evidence", side_effect=edit_after_collection):
            self.assert_blocked(self.query())
        self.assertEqual(self.verdict_path.read_bytes(), modified)


if __name__ == "__main__":
    unittest.main()
