"""Linux 真实进程树反例；隔离收养孤儿，测试后不遗留进程。

夹具的 subreaper 模拟宿主对子进程的回收，不是生产监督器能力。
仅覆盖同一进程组；脱离会话、容器及远程 Agent 不在本测试保证内。
"""
import ctypes
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "scripts"))
import bmad_supervisor as supervisor


def process_tree_fixture(root, scenario):
    # 仅在隔离夹具进程中收养孤儿，避免污染单测运行器或依赖宿主 PID 1。
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # Linux PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), "cannot establish isolated child reaper")
    pid_file = root / "orphan.pid"
    child_code = (
        "import os, pathlib, signal, time; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        "pathlib.Path('orphan.pid').write_text(str(os.getpid())); "
        "time.sleep(20)"
    )
    leader_code = (
        "import os, pathlib, signal, subprocess, sys, time\n"
        f"child = subprocess.Popen([sys.executable, '-B', '-c', {child_code!r}])\n"
        "deadline = time.monotonic() + 3\n"
        "while not pathlib.Path('orphan.pid').exists():\n"
        "    if time.monotonic() >= deadline: raise SystemExit(8)\n"
        "    time.sleep(0.01)\n"
        "print('orphan fixture ready', flush=True)\n"
    )
    if scenario.startswith("cancel-"):
        signal_name = scenario.split("-", 1)[1]
        leader_code += (
            f"os.kill(os.getppid(), signal.{signal_name})\n"
            "time.sleep(20)\n"
        )
    else:
        leader_code += "os._exit(0)\n"
    spec = supervisor.RunSpec(
        operation="unit-test", argv=(sys.executable, "-B", "-c", leader_code),
        workspace=root, runtime_directory=".bmad-runtime",
        target="isolated orphan process-group counterexample", tier="verify",
    )
    actual_stop = supervisor.stop_group
    reaper = None
    reaped = []
    reaper_errors = []
    groups = []
    handlers = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}

    def reap_child(pid):
        # 取消场景下须等待原父进程退出、内核完成收养后才能 waitpid。
        deadline = time.monotonic() + 3
        while True:
            try:
                reaped.append(os.waitpid(pid, 0))
                return
            except ChildProcessError as exc:
                if time.monotonic() >= deadline:
                    reaper_errors.append(str(exc))
                    return
                time.sleep(0.01)
            except BaseException as exc:
                reaper_errors.append(str(exc))
                return

    def stop_with_isolated_reaper(process):
        nonlocal reaper
        groups.append(process.pid)
        pid = int(pid_file.read_text())
        if scenario != "unconfirmed-cleanup":
            reaper = threading.Thread(target=reap_child, args=(pid,))
            reaper.start()
        # 未确认反例故意延迟回收僵尸，不能把已发送信号当作组已消失。
        return actual_stop(process, grace_seconds=0.3)

    child_pid = None
    try:
        with patch.object(supervisor, "stop_group", side_effect=stop_with_isolated_reaper):
            receipt = supervisor.run(spec)
        child_pid = int(pid_file.read_text())
        if scenario == "unconfirmed-cleanup":
            reap_child(child_pid)
        elif reaper is not None:
            reaper.join(timeout=2)
            if reaper.is_alive():
                raise RuntimeError("isolated reaper has not finished")
        if reaper_errors or len(reaped) != 1:
            raise RuntimeError(f"missing actual orphan wait evidence: {reaper_errors}")
        saved = json.loads((root / receipt["receipt_path"]).read_bytes())
        if saved != receipt:
            raise RuntimeError("saved receipt differs from actual result")
        print(json.dumps({
            "receipt": receipt,
            "orphan_pid": child_pid,
            "orphan_wait_pid": reaped[0][0],
            "orphan_signal": os.waitstatus_to_exitcode(reaped[0][1]),
            "group_gone": all(not supervisor.group_exists(group) for group in groups),
            "handlers_restored": all(signal.getsignal(sig) == handler
                                     for sig, handler in handlers.items()),
        }, ensure_ascii=False), flush=True)
    finally:
        # 失败路径也必须实际终止并回收夹具，不能由测试失败遗留孤儿。
        if child_pid is None and pid_file.exists():
            child_pid = int(pid_file.read_text())
        if child_pid is not None and not reaped:
            try:
                os.kill(child_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            if reaper is not None:
                reaper.join(timeout=2)
            if not reaped:
                try:
                    os.waitpid(child_pid, 0)
                except ChildProcessError:
                    pass


class ProcessTreeGuards(unittest.TestCase):
    def fixture(self, scenario):
        with tempfile.TemporaryDirectory(
            prefix="sandbox-process-tree-", dir=SUITE.parent / "tests"
        ) as temporary:
            root = Path(temporary)
            result = subprocess.run(
                [sys.executable, "-B", str(Path(__file__).resolve()),
                 "--process-tree-fixture", str(root), scenario],
                cwd=root, stdin=subprocess.DEVNULL, capture_output=True,
                text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            record = json.loads(result.stdout)
            self.assertEqual(record["orphan_pid"], record["orphan_wait_pid"])
            self.assertEqual(record["orphan_signal"], -signal.SIGKILL)
            self.assertTrue(record["group_gone"])
            self.assertTrue(record["handlers_restored"])
            self.assertEqual(record["receipt"]["process_status"], "BLOCKED")
            self.assertIn("orphan fixture ready", record["receipt"]["summary"]["text"])
            return record["receipt"]

    def test_zero_exit_with_orphan_is_blocked_and_same_group_child_is_killed(self):
        receipt = self.fixture("orphan-exit")
        self.assertEqual(receipt["returncode"], 0)
        self.assertTrue(receipt["cleanup_ok"])
        self.assertFalse(receipt["cancelled"])
        self.assertFalse(receipt["timed_out"])
        self.assertIn("在途子进程", receipt["reason"])

    def test_sigint_and_sigterm_interruptions_kill_child_tree_and_block(self):
        for name in ("SIGINT", "SIGTERM"):
            with self.subTest(signal=name):
                receipt = self.fixture("cancel-" + name)
                self.assertTrue(receipt["cancelled"])
                self.assertFalse(receipt["timed_out"])
                self.assertTrue(receipt["cleanup_ok"])
                self.assertIsNotNone(receipt["returncode"])
                self.assertIn("取消信号", receipt["reason"])

    def test_unconfirmed_orphan_reaping_is_blocked_even_after_leader_exit_zero(self):
        receipt = self.fixture("unconfirmed-cleanup")
        self.assertEqual(receipt["returncode"], 0)
        self.assertFalse(receipt["cleanup_ok"])
        self.assertFalse(receipt["cancelled"])
        self.assertIn("无法确认进程组清理完成", receipt["reason"])


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--process-tree-fixture":
        process_tree_fixture(Path(sys.argv[2]), sys.argv[3])
    else:
        unittest.main()
