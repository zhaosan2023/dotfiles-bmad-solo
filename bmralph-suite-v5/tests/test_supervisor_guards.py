"""监督器真实子进程反例；只使用项目内临时工作区，不证明宿主权限。"""
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest.mock import patch


SUITE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "bmad_supervisor_under_test", SUITE / "scripts/bmad_supervisor.py"
)
supervisor = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = supervisor
SPEC.loader.exec_module(supervisor)


class SupervisorGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="sandbox-supervisor-", dir=SUITE.parent / "tests"
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace with 'quote'"
        self.root.mkdir()

    def spec(self, code="print('actual output')", runtime=".bmad-runtime"):
        return supervisor.RunSpec(
            operation="unit-test", argv=(sys.executable, "-B", "-c", code),
            workspace=self.root, runtime_directory=runtime,
            target="isolated supervisor fixture", tier="verify",
        )

    def execute(self, code="print('actual output')", runtime=".bmad-runtime"):
        return supervisor.run(self.spec(code, runtime))

    def saved_receipt(self, receipt):
        path = self.root / receipt["receipt_path"]
        return json.loads(path.read_text(encoding="utf-8"))

    def test_real_success_has_command_cwd_exit_and_complete_log(self):
        receipt = self.execute()
        self.assertEqual(receipt["returncode"], 0)
        self.assertEqual(receipt["process_status"], "PASS")
        self.assertEqual(receipt["cwd"], str(self.root.resolve()))
        self.assertEqual(receipt["argv"], list(self.spec().argv))
        self.assertTrue(receipt["cleanup_ok"])
        self.assertEqual(self.saved_receipt(receipt), receipt)
        self.assertEqual((self.root / receipt["log_path"]).read_bytes(),
                         b"actual output\n")
        self.assertIn("另判", receipt["evidence_boundary"])

    def test_real_failure_remains_blocked_after_receipt_saved(self):
        receipt = self.execute("print('failure evidence'); raise SystemExit(7)")
        self.assertEqual(receipt["returncode"], 7)
        self.assertEqual(receipt["process_status"], "BLOCKED")
        self.assertEqual(self.saved_receipt(receipt)["process_status"], "BLOCKED")
        self.assertIn("failure evidence", receipt["summary"]["text"])

    def test_stdin_is_closed_and_environment_is_noninteractive(self):
        receipt = self.execute(
            "import os, sys; "
            "assert sys.stdin.read() == ''; "
            "assert os.environ['GIT_TERMINAL_PROMPT'] == '0'; "
            "assert os.environ['PIP_NO_INPUT'] == '1'; print('closed stdin')"
        )
        self.assertEqual(receipt["process_status"], "PASS", receipt)

    def test_long_single_line_summary_is_bounded_and_marked(self):
        receipt = self.execute("print('a' * 20000 + 'failure tail'); raise SystemExit(2)")
        summary = receipt["summary"]
        self.assertEqual(receipt["process_status"], "BLOCKED")
        self.assertTrue(summary["truncated"])
        self.assertIn("TRUNCATED", summary["text"])
        self.assertIn("failure tail", summary["text"])
        self.assertLessEqual(summary["summary_bytes"], supervisor.SUMMARY_BYTES)
        self.assertGreater((self.root / receipt["log_path"]).stat().st_size,
                           supervisor.SUMMARY_BYTES)

    def test_multibyte_summary_does_not_exceed_byte_budget(self):
        receipt = self.execute("print('中文' * 10000)")
        summary = receipt["summary"]
        self.assertTrue(summary["truncated"])
        self.assertLessEqual(len(summary["text"].encode("utf-8")),
                             supervisor.SUMMARY_BYTES)
        self.assertEqual(receipt["process_status"], "PASS")

    def test_timeout_terminates_process_before_returning(self):
        handlers = {sig: signal.getsignal(sig)
                    for sig in (signal.SIGINT, signal.SIGTERM)}
        with patch.dict(supervisor.TIERS, {"verify": 0.1}):
            receipt = self.execute("import time; time.sleep(5)")
        self.assertTrue(receipt["timed_out"])
        self.assertTrue(receipt["cleanup_ok"])
        self.assertIsNotNone(receipt["returncode"])
        self.assertEqual(receipt["process_status"], "BLOCKED")
        self.assertLess(receipt["elapsed_seconds"], 3)
        self.assertEqual({sig: signal.getsignal(sig) for sig in handlers}, handlers)

    def test_cleanup_failure_cannot_generate_pass(self):
        original = supervisor.stop_group

        def cleanup_but_report_failure(process):
            original(process)
            return False

        with patch.dict(supervisor.TIERS, {"verify": 0.1}), patch.object(
            supervisor, "stop_group", side_effect=cleanup_but_report_failure
        ):
            receipt = self.execute("import time; time.sleep(5)")
        self.assertFalse(receipt["cleanup_ok"])
        self.assertEqual(receipt["process_status"], "BLOCKED")
        self.assertIn("清理", receipt["reason"])

    def test_real_cancel_signal_stops_child_and_preserves_failure_receipt(self):
        handlers = {sig: signal.getsignal(sig)
                    for sig in (signal.SIGINT, signal.SIGTERM)}
        receipt = self.execute(
            "import os, signal, time; "
            "print('before cancellation', flush=True); time.sleep(0.05); "
            "os.kill(os.getppid(), signal.SIGTERM); time.sleep(5)"
        )
        self.assertTrue(receipt["cancelled"])
        self.assertFalse(receipt["timed_out"])
        self.assertTrue(receipt["cleanup_ok"])
        self.assertIsNotNone(receipt["returncode"])
        self.assertEqual(receipt["process_status"], "BLOCKED")
        self.assertIn("before cancellation", receipt["summary"]["text"])
        self.assertEqual(self.saved_receipt(receipt), receipt)
        self.assertEqual({sig: signal.getsignal(sig) for sig in handlers}, handlers)

    def test_timeout_escalates_to_sigkill_when_process_ignores_sigterm(self):
        # 真实单进程拒绝 SIGTERM；不外推为脱离进程组的后代或容器清理。
        handlers = {sig: signal.getsignal(sig)
                    for sig in (signal.SIGINT, signal.SIGTERM)}
        code = (
            "import signal, time; "
            "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            "print('SIGTERM ignored', flush=True); time.sleep(10)"
        )
        with patch.dict(supervisor.TIERS, {"verify": 1.0}):
            receipt = self.execute(code)
        self.assertIn("SIGTERM ignored", receipt["summary"]["text"])
        self.assertTrue(receipt["timed_out"])
        self.assertFalse(receipt["cancelled"])
        self.assertEqual(receipt["returncode"], -signal.SIGKILL)
        self.assertTrue(receipt["cleanup_ok"])
        self.assertEqual(receipt["process_status"], "BLOCKED")
        self.assertIn("超时", receipt["reason"])
        self.assertLess(receipt["elapsed_seconds"], 5)
        self.assertEqual(self.saved_receipt(receipt), receipt)
        self.assertEqual({sig: signal.getsignal(sig) for sig in handlers}, handlers)

    def test_timeout_cleans_child_process_group_with_cooperative_parent(self):
        code = (
            "import signal, subprocess, sys, time\n"
            "child = subprocess.Popen([sys.executable, '-B', '-c', "
            "'import time; time.sleep(5)'])\n"
            "def stop(signum, frame):\n"
            "    child.terminate()\n"
            "    child.wait(timeout=1)\n"
            "    raise SystemExit(0)\n"
            "signal.signal(signal.SIGTERM, stop)\n"
            "print('child group started', flush=True)\n"
            "time.sleep(5)\n"
        )
        with patch.dict(supervisor.TIERS, {"verify": 0.2}):
            receipt = self.execute(code)
        self.assertTrue(receipt["timed_out"])
        self.assertTrue(receipt["cleanup_ok"])
        self.assertEqual(receipt["process_status"], "BLOCKED")
        self.assertIn("child group started", receipt["summary"]["text"])

    def test_log_capacity_exhaustion_blocks_even_when_child_exits_zero(self):
        with patch.object(supervisor, "MAX_LOG_BYTES", 1024):
            receipt = self.execute("print('capacity evidence ' * 3000)")
        self.assertEqual(receipt["process_status"], "BLOCKED")
        self.assertIn("保留容量", receipt["reason"])
        self.assertGreater((self.root / receipt["log_path"]).stat().st_size, 1024)
        self.assertTrue(receipt["cleanup_ok"])
        self.assertEqual(self.saved_receipt(receipt), receipt)

    def test_receipt_save_does_not_launch_another_business_process(self):
        receipt = self.execute()
        with patch.object(supervisor.subprocess, "Popen") as process:
            supervisor.save_receipt(self.root / "copied-receipt.json", receipt)
        process.assert_not_called()
        self.assertEqual(len(list((self.root / ".bmad-runtime").glob("run-*.log"))), 1)

    def test_missing_executable_is_blocked_with_actual_receipt(self):
        spec = supervisor.RunSpec(
            operation="unit-test", argv=(str(self.root / "missing-program"),),
            workspace=self.root, runtime_directory=".bmad-runtime",
            target="missing executable fixture", tier="verify",
        )
        receipt = supervisor.run(spec)
        self.assertIsNone(receipt["returncode"])
        self.assertEqual(receipt["process_status"], "BLOCKED")
        self.assertEqual(self.saved_receipt(receipt), receipt)

    def test_existing_receipt_never_overwritten(self):
        path = self.root / "receipt.json"
        supervisor.save_receipt(path, {"original": True})
        original = path.read_bytes()
        with self.assertRaises(FileExistsError):
            supervisor.save_receipt(path, {"replacement": True})
        self.assertEqual(path.read_bytes(), original)

    def test_single_flight_rejects_same_runtime_directory(self):
        directory = self.root / ".bmad-control"
        directory.mkdir()
        with supervisor.verification_lock(directory):
            with self.assertRaises(supervisor.SupervisorError):
                self.execute()
        self.assertEqual(list(directory.glob("run-*")), [])
        self.assertFalse((self.root / ".bmad-runtime").exists())

    def test_single_flight_cannot_be_bypassed_with_second_runtime_directory(self):
        original = supervisor.verification_lock

        @contextmanager
        def nested_probe(directory):
            with original(directory):
                with self.assertRaises(supervisor.SupervisorError):
                    with patch.object(supervisor, "verification_lock", original):
                        self.execute(runtime="other-evidence")
                yield

        with patch.object(supervisor, "verification_lock", nested_probe):
            receipt = self.execute()
        self.assertEqual(receipt["process_status"], "PASS")

    def test_runtime_escape_root_and_symlink_are_rejected(self):
        alias = self.root / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        for runtime in ("../outside", str(self.root / "absolute"), ".", "alias/logs"):
            with self.subTest(runtime=runtime):
                with self.assertRaises(supervisor.SupervisorError):
                    self.execute(runtime=runtime)

    def test_runtime_never_writes_into_distribution_source(self):
        # 目录名仅用于临时工作区内的拒绝写入负例，不读取任何旧套件资产。
        for source_name in ("bmralph-suite-v5", "bmad-suite-v4"):
            runtime = (Path(source_name) / "logs").as_posix()
            with self.subTest(runtime=runtime):
                with self.assertRaises(supervisor.SupervisorError):
                    self.execute(runtime=runtime)
                self.assertFalse((self.root / runtime).exists())

    def test_agent_call_uses_closed_stdin_and_preserves_actual_exit_verdict(self):
        for exit_code in (0, 7):
            with self.subTest(exit_code=exit_code):
                spec = supervisor.RunSpec(
                    operation="agent-call",
                    argv=(sys.executable, "-B", "-c",
                          "import sys; assert sys.stdin.read() == ''; "
                          "print('agent fixture receipt'); "
                          "raise SystemExit(" + str(exit_code) + ")"),
                    workspace=self.root, runtime_directory=".bmad-runtime",
                    target="isolated agent-call supervisor fixture", tier="verify",
                )
                receipt = supervisor.run(spec)
                self.assertEqual(receipt["returncode"], exit_code)
                self.assertEqual(receipt["process_status"],
                                 "PASS" if exit_code == 0 else "BLOCKED")
                self.assertTrue(receipt["cleanup_ok"])
                self.assertEqual(receipt["argv"], list(spec.argv))
                self.assertEqual(receipt["cwd"], str(self.root.resolve()))
                self.assertEqual(self.saved_receipt(receipt), receipt)
                self.assertIn("agent fixture receipt", receipt["summary"]["text"])

    def test_unsupported_operation_rejected_before_file_creation(self):
        spec = supervisor.RunSpec(
            operation="shell", argv=(sys.executable, "-B", "-c", "print('no')"),
            workspace=self.root, runtime_directory=".bmad-runtime",
            target="unapproved operation", tier="verify",
        )
        with self.assertRaises(supervisor.SupervisorError):
            supervisor.run(spec)
        self.assertFalse((self.root / ".bmad-runtime").exists())


if __name__ == "__main__":
    unittest.main()
