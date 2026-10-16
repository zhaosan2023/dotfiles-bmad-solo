"""任务期 CLI 的真实反例；仅本地受限子进程，不证明 Roo 远程运行时。

Linux 进程树夹具在独立进程中收养孤儿；不把夹具回收能力外推为
生产监督器的 subreaper 或脱离会话清理保证。
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
CLI = SUITE / "scripts/bmad-loop.py"
sys.path.insert(0, str(SUITE / "scripts"))
import bmad_loop as loop
import bmad_supervisor as supervisor

ENVIRONMENT_FILE = ".bmad-control/environment.json"


def wait_file(path, seconds=5):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if path.exists():
            return
        time.sleep(0.01)
    raise RuntimeError("夹具文件等待超时：" + str(path))


def command(root, *extra):
    return [sys.executable, "-B", str(CLI), "start", "--workspace", str(root),
            "--plan-file", "plan.md", "--request-file", "request.json",
            "--backend", "local-verification", "--maximum-rounds", "4",
            "--timeout-seconds", "8", "--no-progress-rounds", "2", *extra]


def stop_tree_fixture(root, requested_signal):
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "isolated subreaper unavailable")
    worker = subprocess.Popen(command(root), cwd=root, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, start_new_session=True)
    children = []
    threads = []
    reaped = {}
    errors = []

    def reap(pid):
        end = time.monotonic() + 8
        while time.monotonic() < end:
            try:
                waited, status = os.waitpid(pid, os.WNOHANG)
                if waited:
                    reaped[pid] = os.waitstatus_to_exitcode(status)
                    return
            except ChildProcessError:
                pass
            time.sleep(0.005)
        errors.append("未收养或回收子进程 " + str(pid))

    try:
        for filename in ("child.pid", "grandchild.pid", "leader.pid"):
            wait_file(root / filename)
        children = [int((root / name).read_text()) for name in ("child.pid", "grandchild.pid")]
        leader = int((root / "leader.pid").read_text())
        for pid in children:
            thread = threading.Thread(target=reap, args=(pid,))
            threads.append(thread)
            thread.start()
        if requested_signal == "stop":
            stopped = subprocess.run(
                [sys.executable, "-B", str(CLI), "stop", "--workspace", str(root),
                 "--wait-seconds", "5"], cwd=root, stdin=subprocess.DEVNULL,
                capture_output=True, text=True, timeout=7,
            )
            if stopped.returncode != 0:
                raise RuntimeError(stopped.stdout + stopped.stderr)
            stop_record = json.loads(stopped.stdout)
        else:
            worker.send_signal(getattr(signal, requested_signal))
            stop_record = None
        output, error = worker.communicate(timeout=7)
        if worker.returncode == 0:
            raise RuntimeError("停止信号被错误地登记为完成")
        result = json.loads(output)
        for thread in threads:
            thread.join(timeout=2)
        if errors or any(thread.is_alive() for thread in threads):
            raise RuntimeError(str(errors))
        if set(reaped) != set(children):
            raise RuntimeError("缺少真实进程回收证据")
        process = json.loads((root / result["last_verdict"]).read_bytes())
        process = json.loads((root / process["process_receipt"]).read_bytes())
        print(json.dumps({"result": result, "stop": stop_record,
                          "group_gone": not supervisor.group_exists(leader),
                          "children": list(reaped.values()),
                          "process": process}, ensure_ascii=False), flush=True)
    finally:
        if worker.poll() is None:
            worker.send_signal(signal.SIGTERM)
            try:
                worker.communicate(timeout=4)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.communicate(timeout=2)
        # 失败路径也清理夹具；不遗留真实在途进程。
        for name in ("leader.pid", "child.pid", "grandchild.pid"):
            path = root / name
            if path.exists():
                try:
                    os.kill(int(path.read_text()), signal.SIGKILL)
                except ProcessLookupError:
                    pass
        for thread in threads:
            thread.join(timeout=2)
        for pid in children:
            if pid not in reaped:
                try:
                    os.waitpid(pid, 0)
                except ChildProcessError:
                    pass


class LoopGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sandbox-loop-", dir=SUITE.parent / "tests")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "tests").mkdir()
        (self.root / "unfinished.py").write_text("# 保留成果\n", encoding="utf-8")
        self.fixture("        self.fail('真实验证失败')\n")
        verification = {
            "operation": "unit-test", "environment_file": ENVIRONMENT_FILE,
            "directory": "tests", "pattern": "test_sample.py", "minimum_tests": 1,
            "required_tests": ["test_sample.Sample.test_sample"], "inputs": ["unfinished.py"],
        }
        self.plan = {"schema_version": 1, "plan_id": "LOCAL-LOOP-01", "tasks": [
            {"task_id": "T1", "title": "当前本地任务", "depends_on": [], "status": "PENDING",
             "verification": verification, "verdict_file": None},
            {"task_id": "T2", "title": "保留全部未完成事项", "depends_on": ["T1"],
             "status": "PENDING", "verification": verification, "verdict_file": None},
        ]}
        self.save_plan()
        self.request = {
            "goal": "仅验证本地循环保护", "authorization": "本地隔离夹具；无提交或公网操作",
            "task_id": "T1", "constraints": ["V4 只读"], "capabilities": [],
            "code_files": [], "unfinished_files": ["unfinished.py"], "feedback": [],
            "observed_host_bytes": None,
        }
        self.save_request()
        prepared = subprocess.run(
            [sys.executable, "-B", str(SUITE / "scripts/bmad-exec.py"), "register-env",
             "--workspace", str(self.root), "--environment-file", ENVIRONMENT_FILE,
             "--backend", "native-python", "--python", sys.executable],
            cwd=self.root, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=5,
        )
        self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)

    def fixture(self, body):
        (self.root / "tests/test_sample.py").write_text(
            "import unittest\n\nclass Sample(unittest.TestCase):\n    def test_sample(self):\n" + body,
            encoding="utf-8",
        )

    def save_plan(self):
        (self.root / "plan.md").write_text(
            '---\nplan_id: "LOCAL-LOOP-01"\nstatus: READY\n---\n\n```bmad-tasks\n' +
            json.dumps(self.plan, ensure_ascii=False) + "\n```\n", encoding="utf-8",
        )

    def save_request(self):
        (self.root / "request.json").write_text(json.dumps(self.request, ensure_ascii=False), encoding="utf-8")

    def invoke(self, *extra):
        result = subprocess.run(command(self.root, *extra), cwd=self.root, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=12)
        self.assertLessEqual(len(result.stdout.encode("utf-8")), 16384)
        return result, json.loads(result.stdout)

    def assert_blocked(self, result, record):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(record["status"], "BLOCKED")
        self.assertTrue(record["reason"])

    def spec(self, **changes):
        values = dict(workspace=self.root, plan_file="plan.md", request_file="request.json",
                      backend="local-verification", maximum_rounds=4, timeout_seconds=8,
                      no_progress_rounds=2)
        values.update(changes)
        return loop.LoopSpec(**values)

    def test_no_progress_auto_stops_nonzero_and_preserves_every_pending_item(self):
        before = (self.root / "plan.md").read_bytes()
        result, record = self.invoke()
        self.assert_blocked(result, record)
        self.assertIn("持续无进展", record["reason"])
        self.assertEqual(record["rounds"], 2)
        self.assertEqual(record["no_progress_count"], 2)
        self.assertTrue(record["cleanup_ok"])
        self.assertFalse(record["task_progress_saved"])
        self.assertEqual((self.root / "plan.md").read_bytes(), before)
        self.assertEqual((self.root / "unfinished.py").read_text(), "# 保留成果\n")
        self.assertEqual(len(list((self.root / ".bmad-runtime").glob("run-*.verdict.json"))), 2)
        saved = json.loads((self.root / record["final_receipt"]).read_bytes())
        self.assertEqual(saved, record)

    def test_real_failure_never_completes_on_maximum_rounds(self):
        result, record = self.invoke("--maximum-rounds", "1", "--no-progress-rounds", "4")
        self.assert_blocked(result, record)
        self.assertEqual(record["rounds"], 1)
        self.assertIn("最大轮次", record["reason"])

    def test_process_deadline_cleans_child_and_keeps_artifacts(self):
        self.fixture("        import pathlib, time\n        pathlib.Path('kept.txt').write_text('成果')\n        time.sleep(5)\n")
        result, record = self.invoke("--timeout-seconds", "0.5")
        self.assert_blocked(result, record)
        self.assertIn("时间预算", record["reason"])
        self.assertTrue(record["cleanup_ok"])
        self.assertEqual(record["rounds"], 1)
        self.assertEqual((self.root / "kept.txt").read_text(), "成果")
        verdict = json.loads((self.root / record["last_verdict"]).read_bytes())
        process = json.loads((self.root / verdict["process_receipt"]).read_bytes())
        self.assertTrue(process["timed_out"])
        self.assertNotEqual(process["returncode"], 0)

    def test_actual_pass_only_completes_requested_local_verification_without_plan_write(self):
        self.fixture("        self.assertTrue(True)\n")
        before = (self.root / "plan.md").read_bytes()
        result, record = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(record["status"], "COMPLETED")
        self.assertEqual(record["rounds"], 1)
        self.assertEqual((self.root / "plan.md").read_bytes(), before)
        verdict = json.loads((self.root / record["last_verdict"]).read_bytes())
        self.assertEqual(verdict["status"], "PASS")
        before_files = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        queried = loop.status(self.root)
        self.assertEqual(queried["status"], "COMPLETED")
        self.assertFalse(queried["writer_active"])
        self.assertEqual({p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}, before_files)

    def test_explicit_progress_write_completes_one_task_and_generates_bounded_card(self):
        self.fixture("        self.assertTrue(True)\n")
        result, record = self.invoke("--save-progress")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(record["task_progress_saved"])
        self.assertLessEqual(record["state_card_lines"], 80)
        self.assertEqual(record["state_card_bytes"], len(record["state_card"].encode("utf-8")))
        self.assertIn("T1 [COMPLETED]", record["state_card"])
        self.assertIn("T2 [READY]", record["state_card"])
        self.assertEqual(record["unfinished_count"], 1)
        self.assertEqual(record["rounds"], 1)
        self.assertEqual(loop.status(self.root, "plan.md")["ready_tasks"], ["T2"])

    def test_failure_with_progress_permission_does_not_check_off_task(self):
        before = (self.root / "plan.md").read_bytes()
        result, record = self.invoke("--save-progress", "--maximum-rounds", "1")
        self.assert_blocked(result, record)
        self.assertFalse(record["task_progress_saved"])
        self.assertEqual((self.root / "plan.md").read_bytes(), before)
        self.assertIn("T2 [PENDING]", record["state_card"])

    def test_plan_query_does_not_create_loop_or_business_receipts(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        result = subprocess.run(
            [sys.executable, "-B", str(CLI), "status", "--workspace", str(self.root),
             "--plan-file", "plan.md"], stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["ready_tasks"], ["T1"])
        self.assertEqual({p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}, before)

    def test_cli_output_overflow_exits_nonzero_and_preserves_receipt_locator(self):
        with loop.writer_lease(self.root):
            loop.save_current(self.root, {
                "status": "COMPLETED", "cleanup_ok": True,
                "state_card": "中文" * 6000, "final_receipt": ".bmad-runtime/loop-test.json",
            })
        result = subprocess.run(
            [sys.executable, "-B", str(CLI), "status", "--workspace", str(self.root)],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=5,
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        record = json.loads(result.stdout)
        self.assertEqual(record["status"], "BLOCKED")
        self.assertTrue(record["output_truncated"])
        self.assertEqual(record["final_receipt"], ".bmad-runtime/loop-test.json")
        self.assertNotIn("state_card", record)
        self.assertLessEqual(len(result.stdout.encode("utf-8")), 16384)
        self.assertEqual(loop.status(self.root)["state_card"], "中文" * 6000)

    def test_idle_status_and_stop_do_not_create_files(self):
        with tempfile.TemporaryDirectory(dir=SUITE.parent / "tests") as temporary:
            root = Path(temporary)
            self.assertEqual(loop.status(root)["status"], "IDLE")
            self.assertEqual(loop.stop(root)["status"], "IDLE")
            self.assertEqual(list(root.iterdir()), [])

    def test_budget_failures_block_without_dropping_constraints(self):
        for args in (("--startup-bytes", "256"), ("--output-bytes", "256")):
            with self.subTest(args=args):
                result, record = self.invoke(*args)
                self.assert_blocked(result, record)
                self.assertIn("预算", record["reason"])

    def test_explicit_suspension_or_legacy_plan_is_not_resumed_or_migrated(self):
        self.plan["tasks"][0]["status"] = "SUSPENDED"
        self.save_plan()
        result, record = self.invoke()
        self.assert_blocked(result, record)
        self.assertEqual(record["rounds"], 0)
        (self.root / "plan.md").write_text('---\nplan_id: "LOCAL-LOOP-01"\n---\n\n- [ ] 未迁移任务\n')
        result, record = self.invoke()
        self.assert_blocked(result, record)
        self.assertEqual(record["rounds"], 0)
        self.assertIn("未迁移任务", (self.root / "plan.md").read_text())

    def test_invalid_budgets_and_unverified_backend_fail_before_writes(self):
        for changes in ({"maximum_rounds": 0}, {"maximum_rounds": True},
                        {"timeout_seconds": float("nan")}, {"timeout_seconds": 601},
                        {"no_progress_rounds": 0}, {"retry_delay": float("inf")},
                        {"backend": "roo"}):
            with self.subTest(changes=changes):
                with self.assertRaises(supervisor.SupervisorError):
                    loop.start(self.spec(**changes))
        self.assertFalse((self.root / ".bmad-runtime").exists())

    def test_single_writer_lease_cannot_be_bypassed_by_different_runtime_directory(self):
        self.fixture("        import pathlib, time\n        pathlib.Path('ready').touch()\n        time.sleep(5)\n")
        worker = subprocess.Popen(command(self.root), cwd=self.root, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            wait_file(self.root / "ready")
            first = (self.root / loop.CURRENT).read_bytes()
            result, record = self.invoke("--runtime-directory", "different-runtime")
            self.assert_blocked(result, record)
            self.assertIn("活动写入者", record["reason"])
            self.assertEqual((self.root / loop.CURRENT).read_bytes(), first)
            self.assertFalse((self.root / "different-runtime").exists())
            stopped = subprocess.run(
                [sys.executable, "-B", str(CLI), "stop", "--workspace", str(self.root), "--wait-seconds", "5"],
                stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=7,
            )
            self.assertEqual(stopped.returncode, 0, stopped.stdout + stopped.stderr)
            out, err = worker.communicate(timeout=3)
            self.assertNotEqual(worker.returncode, 0, out + err)
            self.assertTrue(json.loads(out)["cleanup_ok"])
            self.assertFalse(loop.writer_active(self.root))
        finally:
            if worker.poll() is None:
                worker.send_signal(signal.SIGTERM)
                worker.communicate(timeout=4)

    def test_stale_executing_record_cannot_claim_successful_stop(self):
        with loop.writer_lease(self.root):
            loop.save_current(self.root, {"status": "EXECUTING", "cleanup_ok": True})
        queried = loop.status(self.root)
        self.assertEqual(queried["status"], "BLOCKED")
        self.assertFalse(queried["cleanup_ok"])
        with self.assertRaises(supervisor.SupervisorError):
            loop.stop(self.root)

    def test_writer_lease_replacement_is_detected_without_restoring_external_file(self):
        lock_path = self.root / loop.LOCK
        with self.assertRaises(supervisor.SupervisorError):
            with loop.writer_lease(self.root):
                replacement = lock_path.with_name('external-lock')
                replacement.write_text('第三方替换内容', encoding='utf-8')
                os.replace(replacement, lock_path)
        self.assertEqual(lock_path.read_text(encoding='utf-8'), '第三方替换内容')

    def test_missing_final_cleanup_blocks_restart(self):
        with loop.writer_lease(self.root):
            loop.save_current(self.root, {"status": "EXECUTING", "cleanup_ok": True})
        self.assertEqual(loop.status(self.root)["status"], "BLOCKED")
        with self.assertRaises(supervisor.SupervisorError):
            loop.start(self.spec())

    def test_unknown_cleanup_is_not_reported_as_success_and_cannot_restart(self):
        with patch.object(loop.execution, "unit_test", side_effect=OSError("回执存储失败")):
            record = loop.start(self.spec())
        self.assertEqual(record["status"], "BLOCKED")
        self.assertFalse(record["cleanup_ok"])
        with self.assertRaises(supervisor.SupervisorError):
            loop.start(self.spec())

    def test_stop_and_signal_cleanup_real_inflight_child_and_grandchild_tree(self):
        grandchild = "import os,pathlib,signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); pathlib.Path('grandchild.pid').write_text(str(os.getpid())); time.sleep(20)"
        child = (
            "import os,pathlib,signal,subprocess,sys,time; "
            "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
            "pathlib.Path('child.pid').write_text(str(os.getpid())); "
            f"subprocess.Popen([sys.executable,'-B','-c',{grandchild!r}]); time.sleep(20)"
        )
        self.fixture(
            "        import os, pathlib, subprocess, sys, time\n"
            "        pathlib.Path('leader.pid').write_text(str(os.getpid()))\n"
            f"        subprocess.Popen([sys.executable, '-B', '-c', {child!r}])\n"
            "        time.sleep(20)\n"
        )
        for name in ("stop", "SIGTERM", "SIGINT"):
            with self.subTest(signal=name):
                for path in ("leader.pid", "child.pid", "grandchild.pid"):
                    (self.root / path).unlink(missing_ok=True)
                actual = subprocess.run(
                    [sys.executable, "-B", str(Path(__file__).resolve()), "--stop-tree-fixture", str(self.root), name],
                    cwd=self.root, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=12,
                )
                self.assertEqual(actual.returncode, 0, actual.stdout + actual.stderr)
                data = json.loads(actual.stdout)
                self.assertEqual(data["result"]["status"], "SUSPENDED")
                self.assertTrue(data["result"]["cleanup_ok"])
                self.assertTrue(data["group_gone"])
                self.assertEqual(data["children"], [-signal.SIGKILL, -signal.SIGKILL])
                self.assertTrue(data["process"]["cleanup_ok"])
                self.assertTrue(data["process"]["cancelled"])
                self.assertFalse(data["process"]["timed_out"])
                if name == "stop":
                    self.assertFalse(data["stop"]["writer_active"])
                    self.assertEqual(data["stop"]["run_id"], data["result"]["run_id"])
                self.assertEqual((self.root / "unfinished.py").read_text(), "# 保留成果\n")


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--stop-tree-fixture":
        stop_tree_fixture(Path(sys.argv[2]), sys.argv[3])
    else:
        unittest.main()
