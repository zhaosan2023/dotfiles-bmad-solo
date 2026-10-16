"""类型化单测纵向闭环反例；真实子进程，项目内独立临时工作区。

仅覆盖本机 Python 后端，不证明容器、权限隔离或远程自主运行。
"""
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
import bmad_supervisor as supervisor


class ExecutionGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="sandbox-execution-", dir=SUITE.parent / "tests"
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace with 'quote'"
        self.root.mkdir()
        self.tests = self.root / "tests"
        self.tests.mkdir()
        self.manifest = ".bmad-control/environment.json"
        environment.register(self.root, self.manifest, sys.executable)
        self.fixture("        self.assertEqual(2 + 2, 4)\n")

    def fixture(self, body, header=""):
        path = self.tests / "test_sample.py"
        path.write_text(
            "import unittest\n" + header +
            "\nclass Sample(unittest.TestCase):\n"
            "    def test_sample(self):\n" + body,
            encoding="utf-8",
        )
        return path

    def execute(self, **kwargs):
        arguments = dict(
            workspace=self.root, environment_file=self.manifest,
            directory="tests", pattern="test_*.py",
            required_tests=("test_sample.Sample.test_sample",),
        )
        arguments.update(kwargs)
        return execution.unit_test(**arguments)

    def receipts(self):
        return list((self.root / ".bmad-runtime").glob("*.json"))

    def assert_blocked(self, verdict):
        self.assertEqual(verdict["status"], "BLOCKED", verdict)
        self.assertTrue(verdict["reason"])
        saved = json.loads((self.root / verdict["verdict_path"]).read_bytes())
        self.assertEqual(saved, verdict)

    def test_real_pass_has_separate_process_and_verdict_receipts(self):
        verdict = self.execute()
        self.assertEqual(verdict["status"], "PASS", verdict)
        self.assertEqual(verdict["result"]["tests_run"], 1)
        self.assertEqual(verdict["evidence_before"], verdict["evidence_after"])
        self.assertNotEqual(verdict["process_receipt"], verdict["verdict_path"])
        process = json.loads((self.root / verdict["process_receipt"]).read_bytes())
        self.assertEqual(process["returncode"], 0)
        self.assertEqual(process["process_status"], "PASS")
        self.assertEqual(process["cwd"], str(self.root.resolve()))
        self.assertEqual(len(self.receipts()), 2)

    def test_assertion_failure_is_not_receipt_save_success(self):
        self.fixture("        self.fail('actual failure')\n")
        verdict = self.execute()
        self.assert_blocked(verdict)
        process = json.loads((self.root / verdict["process_receipt"]).read_bytes())
        self.assertNotEqual(process["returncode"], 0)
        self.assertEqual(process["process_status"], "BLOCKED")

    def test_zero_match_blocks(self):
        verdict = self.execute(pattern="test_missing_*.py")
        self.assert_blocked(verdict)

    def test_required_identifier_missing_blocks(self):
        verdict = self.execute(required_tests=("test_sample.Sample.test_missing",))
        self.assert_blocked(verdict)

    def test_minimum_count_is_not_relaxed(self):
        self.assert_blocked(self.execute(minimum_tests=2))

    def test_skipped_required_test_blocks(self):
        self.fixture("        self.skipTest('required asset absent')\n")
        self.assert_blocked(self.execute())

    def test_exit_zero_without_test_result_blocks(self):
        self.fixture("        import os\n        os._exit(0)\n")
        verdict = self.execute()
        self.assert_blocked(verdict)
        process = json.loads((self.root / verdict["process_receipt"]).read_bytes())
        self.assertEqual(process["returncode"], 0)
        self.assertIn("缺少真实测试结果", verdict["reason"])

    def test_duplicate_result_marker_blocks(self):
        self.fixture(
            "        print('BMAD_TEST_RESULT {}', flush=True)\n"
            "        self.assertTrue(True)\n"
        )
        verdict = self.execute()
        self.assert_blocked(verdict)
        self.assertIn("重复", verdict["reason"])

    def test_long_log_truncation_does_not_discard_real_result(self):
        self.fixture("        print('中文' * 20000)\n        self.assertTrue(True)\n")
        verdict = self.execute()
        self.assertEqual(verdict["status"], "PASS", verdict)
        process = json.loads((self.root / verdict["process_receipt"]).read_bytes())
        self.assertTrue(process["summary"]["truncated"])
        self.assertLessEqual(process["summary"]["summary_bytes"], 8192)
        self.assertEqual(verdict["result"]["tests_run"], 1)

    def test_test_directory_mutation_invalidates_current_pass(self):
        self.fixture(
            "        from pathlib import Path\n"
            "        Path('tests/new-asset.txt').write_text('new evidence')\n"
            "        self.assertTrue(True)\n"
        )
        verdict = self.execute()
        self.assert_blocked(verdict)
        self.assertIn("证据失效", verdict["reason"])
        self.assertTrue((self.tests / "new-asset.txt").exists())

    def test_explicit_implementation_mutation_invalidates_current_pass(self):
        source = self.root / "implementation.py"
        source.write_text("VALUE = 1\n", encoding="utf-8")
        self.fixture(
            "        from pathlib import Path\n"
            "        Path('implementation.py').write_text('VALUE = 2\\n')\n"
            "        self.assertTrue(True)\n"
        )
        verdict = self.execute(inputs=("implementation.py",))
        self.assert_blocked(verdict)
        self.assertIn("证据失效", verdict["reason"])
        self.assertEqual(source.read_text(encoding="utf-8"), "VALUE = 2\n")

    def test_unrelated_document_change_does_not_invalidate_selected_evidence(self):
        self.fixture(
            "        from pathlib import Path\n"
            "        Path('notes.md').write_text('unrelated notes')\n"
            "        self.assertTrue(True)\n"
        )
        verdict = self.execute()
        self.assertEqual(verdict["status"], "PASS", verdict)
        self.assertEqual(verdict["evidence_before"], verdict["evidence_after"])

    def test_environment_manifest_mutation_invalidates_current_pass(self):
        self.fixture(
            "        from pathlib import Path\n"
            "        path = Path('.bmad-control/environment.json')\n"
            "        path.write_bytes(path.read_bytes() + b'\\n')\n"
            "        self.assertTrue(True)\n"
        )
        verdict = self.execute()
        self.assert_blocked(verdict)
        self.assertIn("环境登记变化", verdict["reason"])

    def test_real_timeout_blocks_verdict_and_preserves_process_evidence(self):
        self.fixture(
            "        import time\n"
            "        print('before verification timeout', flush=True)\n"
            "        time.sleep(5)\n"
        )
        with patch.dict(supervisor.TIERS, {"verify": 0.5}):
            verdict = self.execute()
        self.assert_blocked(verdict)
        process = json.loads((self.root / verdict["process_receipt"]).read_bytes())
        self.assertTrue(process["timed_out"])
        self.assertFalse(process["cancelled"])
        self.assertTrue(process["cleanup_ok"])
        self.assertIsNotNone(process["returncode"])
        self.assertEqual(process["process_status"], "BLOCKED")
        self.assertIn("before verification timeout", process["summary"]["text"])
        self.assertIsNone(verdict["result"])
        self.assertIsNone(verdict["evidence_after"])
        self.assertEqual(len(self.receipts()), 2)
        checked = execution.check_evidence(
            workspace=self.root, verdict_file=verdict["verdict_path"],
        )
        self.assertEqual(checked["status"], "BLOCKED")
        self.assertIs(checked["business_reexecuted"], False)
        self.assertEqual(len(self.receipts()), 2)

    def test_real_cancel_signal_blocks_verdict_after_process_cleanup(self):
        self.fixture(
            "        import os, signal, time\n"
            "        print('before verification cancellation', flush=True)\n"
            "        os.kill(os.getppid(), signal.SIGTERM)\n"
            "        time.sleep(5)\n"
        )
        verdict = self.execute()
        self.assert_blocked(verdict)
        process = json.loads((self.root / verdict["process_receipt"]).read_bytes())
        self.assertTrue(process["cancelled"])
        self.assertFalse(process["timed_out"])
        self.assertTrue(process["cleanup_ok"])
        self.assertIsNotNone(process["returncode"])
        self.assertEqual(process["process_status"], "BLOCKED")
        self.assertIn("before verification cancellation", process["summary"]["text"])
        self.assertIsNone(verdict["result"])
        self.assertIsNone(verdict["evidence_after"])
        self.assertEqual(len(self.receipts()), 2)
        checked = execution.check_evidence(
            workspace=self.root, verdict_file=verdict["verdict_path"],
        )
        self.assertEqual(checked["status"], "BLOCKED")
        self.assertIs(checked["business_reexecuted"], False)
        self.assertEqual(len(self.receipts()), 2)

    def test_cleanup_failure_propagates_to_verdict_without_false_pass(self):
        # 实际清理进程后注入清理失败回执，避免反例遗留在途进程。
        self.fixture("        import time\n        time.sleep(5)\n")
        actual_cleanup = supervisor.stop_group

        def cleanup_but_report_failure(process):
            self.assertTrue(actual_cleanup(process))
            return False

        with patch.dict(supervisor.TIERS, {"verify": 0.5}), patch.object(
            supervisor, "stop_group", side_effect=cleanup_but_report_failure,
        ):
            verdict = self.execute()
        self.assert_blocked(verdict)
        process = json.loads((self.root / verdict["process_receipt"]).read_bytes())
        self.assertTrue(process["timed_out"])
        self.assertFalse(process["cleanup_ok"])
        self.assertIsNotNone(process["returncode"])
        self.assertEqual(process["process_status"], "BLOCKED")
        self.assertIn("清理", verdict["reason"])
        self.assertIsNone(verdict["result"])
        self.assertIsNone(verdict["evidence_after"])
        self.assertEqual(len(self.receipts()), 2)

    def test_missing_l0_blocks_before_business_process(self):
        (self.root / self.manifest).unlink()
        with patch.object(execution, "run") as run:
            with self.assertRaises(environment.EnvironmentNotReady):
                self.execute()
        run.assert_not_called()
        self.assertFalse((self.root / ".bmad-runtime").exists())

    def test_missing_explicit_input_blocks_before_business_process(self):
        with patch.object(execution, "run") as run:
            with self.assertRaises(supervisor.SupervisorError):
                self.execute(inputs=("missing.py",))
        run.assert_not_called()

    def test_runtime_inside_selected_tests_is_rejected(self):
        with patch.object(execution, "run") as run:
            with self.assertRaises(supervisor.SupervisorError):
                self.execute(runtime_directory="tests/logs")
        run.assert_not_called()
        self.assertFalse((self.tests / "logs").exists())

    def test_symlink_in_test_evidence_blocks_before_execution(self):
        (self.tests / "alias.py").symlink_to(self.tests / "test_sample.py")
        with patch.object(execution, "run") as run:
            with self.assertRaises(supervisor.SupervisorError):
                self.execute()
        run.assert_not_called()

    def test_verdict_save_failure_cannot_return_pass_or_reexecute_tests(self):
        actual_run = execution.run
        with patch.object(execution, "run", wraps=actual_run) as run, \
                patch.object(execution, "save_receipt", side_effect=OSError("save failed")):
            with self.assertRaisesRegex(OSError, "save failed"):
                self.execute()
        self.assertEqual(run.call_count, 1)
        self.assertEqual(len(list((self.root / ".bmad-runtime").glob("*.log"))), 1)
        self.assertEqual(len(self.receipts()), 1)

    def test_changed_test_requires_new_execution_not_old_pass(self):
        first = self.execute()
        self.assertEqual(first["status"], "PASS", first)
        self.fixture("        self.fail('current implementation fails')\n")
        second = self.execute()
        self.assert_blocked(second)
        self.assertNotEqual(first["process_receipt"], second["process_receipt"])
        self.assertNotEqual(first["evidence_before"], second["evidence_before"])


if __name__ == "__main__":
    unittest.main()
