"""来源租约、隔离副本与取消的本地集成反例。

只使用项目内合成部署根及明确的隔离驱动；不启动真实 Agent，
不证明 Roo 权限、关闭客户端后的模型步骤或同账号防篡改。
"""
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import unittest

import test_run_copy as fixtures

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "scripts"))
import bmad_environment as environment
import bmad_suite_source as source
import bmad_supervisor as supervisor

CREDENTIAL = "BMAD_ISOLATED_TEST_CREDENTIAL"


class BatchIsolationGuards(unittest.TestCase):
    setUpSource = fixtures.RunCopyGuards.setUp
    setUpSourceFiles = fixtures.RunCopyGuards.setUpSource
    record = staticmethod(fixtures.RunCopyGuards.record)
    put = fixtures.RunCopyGuards.put
    save_manifests = fixtures.RunCopyGuards.save_manifests
    snapshot = fixtures.RunCopyGuards.snapshot
    assert_writer_available = fixtures.RunCopyGuards.assert_writer_available
    prepare = fixtures.RunCopyGuards.prepare

    def setUp(self):
        # 复用物理来源夹具，而非模拟来源核验或伪装真实后端。
        self.setUpSource = self.setUpSourceFiles
        fixtures.RunCopyGuards.setUp(self)
        self.workspace = self.base
        self.candidate = self.prepare()
        (self.workspace / "business-tests").mkdir()
        (self.workspace / "unfinished.py").write_text("KEEP\n", encoding="utf-8")
        environment.register(self.workspace, ".bmad-control/environment.json", sys.executable)
        verification = {
            "operation": "unit-test", "environment_file": ".bmad-control/environment.json",
            "directory": "business-tests", "pattern": "test_sample.py", "minimum_tests": 1,
            "required_tests": ["test_sample.Sample.test_sample"], "inputs": ["unfinished.py"],
        }
        self.plan = {"schema_version": 1, "plan_id": "ISOLATION-LOCAL-01", "tasks": [
            {"task_id": "T1", "title": "合成部署根隔离验证", "depends_on": [],
             "status": "PENDING", "verification": verification, "verdict_file": None},
            {"task_id": "T2", "title": "保留后续任务", "depends_on": ["T1"],
             "status": "PENDING", "verification": verification, "verdict_file": None},
        ]}
        (self.workspace / "plan.md").write_text(
            '---\nplan_id: "ISOLATION-LOCAL-01"\nstatus: READY\n---\n\n```bmad-tasks\n'
            + json.dumps(self.plan, ensure_ascii=False) + "\n```\n", encoding="utf-8")
        request = {
            "goal": "仅验证本地来源隔离与清理生命周期",
            "authorization": "项目内合成部署根与隔离驱动；无真实 Agent 或宿主激活",
            "task_id": "T1", "constraints": ["V4 只读，不修改验收"],
            "capabilities": [], "code_files": [], "unfinished_files": ["unfinished.py"],
            "feedback": [], "observed_host_bytes": None,
        }
        (self.workspace / "request.json").write_text(json.dumps(request), encoding="utf-8")
        config = {
            "schema_version": 1, "backend": "headless", "protocol": "bmad-headless-json-v1",
            "runtime_kind": "isolated-fixture", "source": "本测试的项目内驱动",
            "version": "fixture-v1", "driver_file": "driver.py", "credential_environment": CREDENTIAL,
            "authorized": True, "authorization": "仅本地反例", "new_session": True,
            "headless": True, "api_timeout_seconds": 5,
        }
        (self.workspace / "backend.json").write_text(json.dumps(config), encoding="utf-8")
        self.business_fixture()
        self.driver("pathlib.Path('unfinished.py').write_text('DONE\\n')\n")

    def business_fixture(self, extra=""):
        (self.workspace / "business-tests/test_sample.py").write_text(
            "import pathlib, unittest\nclass Sample(unittest.TestCase):\n"
            "    def test_sample(self):\n"
            "        self.assertEqual(pathlib.Path('unfinished.py').read_text(), 'DONE\\n')\n"
            + extra, encoding="utf-8")

    def driver(self, body):
        (self.workspace / "driver.py").write_text(
            "import argparse, json, os, pathlib, sys, time\n"
            "p = argparse.ArgumentParser(allow_abbrev=False)\n"
            "p.add_argument('--request-file', required=True)\n"
            "a = p.parse_args()\n"
            "request = json.loads(pathlib.Path(a.request_file).read_bytes())\n"
            "out = {key: request[key] for key in ('session_id', 'plan_id', 'task_id')}\n"
            "out.update(schema_version=1, status='OK')\n"
            + body + "print('BMAD_AGENT_RESULT ' + json.dumps(out), flush=True)\n",
            encoding="utf-8")

    def command(self, entrypoint=None):
        return [sys.executable, "-B", str(entrypoint or self.candidate.entrypoint), "start",
                "--workspace", str(self.workspace), "--plan-file", "plan.md",
                "--request-file", "request.json", "--backend", "headless",
                "--backend-config", "backend.json", "--maximum-rounds", "3",
                "--timeout-seconds", "8", "--no-progress-rounds", "2", "--save-progress",
                "--deployment-root", str(self.root),
                "--run-copy-file", self.candidate.receipt_file]

    def child_environment(self):
        result = dict(os.environ)
        result[CREDENTIAL] = "isolated-fixture-only"
        return result

    def invoke(self, entrypoint=None):
        process = subprocess.run(
            self.command(entrypoint), cwd=self.workspace, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, env=self.child_environment(), timeout=12)
        self.assertLessEqual(len(process.stdout.encode("utf-8")), 16384)
        return process, json.loads(process.stdout)

    def cleanup_records(self):
        directory = self.root / ".bmad-solo-deployment/task-runs"
        return {path: json.loads(path.read_bytes()) for path in directory.glob("*.json")}

    def assert_persistent_block(self):
        repository = SUITE.parent
        command = [sys.executable, "-I", "-B", "-c",
                   "import pathlib,sys; sys.path.insert(0,sys.argv[1]); "
                   "from asset_safety import deployment_lock; "
                   "context=deployment_lock(pathlib.Path(sys.argv[2]),create=False); "
                   "context.__enter__()", str(repository / "scripts"), str(self.lock)]
        result = subprocess.run(command, cwd=self.workspace, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=5)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("任务清理", result.stderr)

    def test_source_lease_covers_calls_and_confirmed_cleanup(self):
        lock = repr(str(self.lock))
        self.driver(
            "import fcntl\n"
            "with open(" + lock + ", 'rb') as stream:\n"
            "    try:\n"
            "        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
            "    except BlockingIOError:\n"
            "        pass\n"
            "    else:\n"
            "        raise AssertionError('Agent 调用期间来源租约缺失')\n"
            "records = list(pathlib.Path(" + repr(str(self.lock.parent / 'task-runs')) + ").glob('*.json'))\n"
            "assert len(records) == 1\n"
            "record = json.loads(records[0].read_bytes())\n"
            "assert record['status'] == 'EXECUTING' and record['cleanup_ok'] is False\n"
            "pathlib.Path('unfinished.py').write_text('DONE\\n')\n")
        self.business_fixture(
            "        import fcntl\n"
            "        with open(" + lock + ", 'rb') as stream:\n"
            "            with self.assertRaises(BlockingIOError):\n"
            "                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)\n")
        process, record = self.invoke()
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        self.assertEqual(record["status"], "COMPLETED")
        self.assertTrue(record["cleanup_ok"])
        self.assertEqual(record["source_commit"], "a" * 40)
        terminal = self.cleanup_records()
        self.assertEqual(len(terminal), 1)
        saved = next(iter(terminal.values()))
        self.assertEqual(saved["run_id"], record["run_id"])
        self.assertEqual(saved["status"], "COMPLETED")
        self.assertTrue(saved["cleanup_ok"])
        self.assertEqual(saved["final_receipt"], record["final_receipt"])
        self.assert_writer_available()

    def test_source_change_blocks_without_restoring_assets(self):
        path = self.root / ".roo/rules/02-bmad-core.md"
        changed = b"external rule change preserved\n"
        self.driver("pathlib.Path(" + repr(str(path)) + ").write_bytes(" + repr(changed) + ")\n")
        process, record = self.invoke()
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(record["status"], "BLOCKED")
        self.assertEqual(path.read_bytes(), changed)
        saved_plan = (self.workspace / "plan.md").read_text(encoding="utf-8")
        saved_tasks = json.loads(saved_plan.split("```bmad-tasks\n", 1)[1].split("\n```", 1)[0])
        self.assertEqual(saved_tasks["tasks"][0]["status"], "PENDING")
        self.assertEqual(saved_tasks["tasks"][1]["status"], "PENDING")
        self.assert_persistent_block()

    def test_source_edit_does_not_hot_replace_running_copy(self):
        before = self.candidate.entrypoint.read_bytes()
        path = self.plugin / "scripts/bmad-loop.py"
        changed = path.read_bytes() + b"\n# preserve source edit\n"
        self.driver("pathlib.Path(" + repr(str(path)) + ").write_bytes(" + repr(changed) + ")\n")
        process, record = self.invoke()
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(record["status"], "BLOCKED")
        self.assertEqual(path.read_bytes(), changed)
        self.assertEqual(self.candidate.entrypoint.read_bytes(), before)
        self.assert_persistent_block()

    def test_cancel_confirms_all_managed_processes_ended(self):
        self.driver("pathlib.Path('driver.pid').write_text(str(os.getpid()))\ntime.sleep(5)\n")
        worker = subprocess.Popen(
            self.command(), cwd=self.workspace, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            env=self.child_environment(), start_new_session=True)
        try:
            deadline = time.monotonic() + 5
            marker = self.workspace / "driver.pid"
            while not marker.exists() and time.monotonic() < deadline:
                if worker.poll() is not None:
                    output, error = worker.communicate(timeout=1)
                    self.fail(output + error)
                time.sleep(0.01)
            self.assertTrue(marker.exists(), "隔离驱动没有启动证据")
            driver_pid = int(marker.read_text())
            stopped = subprocess.run(
                [sys.executable, "-B", str(self.candidate.entrypoint), "stop",
                 "--workspace", str(self.workspace), "--wait-seconds", "5"],
                cwd=self.workspace, stdin=subprocess.DEVNULL,
                capture_output=True, text=True, timeout=7)
            output, error = worker.communicate(timeout=7)
            self.assertEqual(stopped.returncode, 0, stopped.stdout + stopped.stderr)
            self.assertNotEqual(worker.returncode, 0, output + error)
            record = json.loads(output)
            self.assertEqual(record["status"], "SUSPENDED")
            self.assertTrue(record["cleanup_ok"])
            self.assertTrue(record["last_agent"]["cancelled"])
            self.assertFalse(supervisor.group_exists(driver_pid))
            with self.assertRaises(ProcessLookupError):
                os.kill(driver_pid, 0)
            terminal = next(iter(self.cleanup_records().values()))
            self.assertEqual(terminal["status"], "SUSPENDED")
            self.assertTrue(terminal["cleanup_ok"])
            self.assert_writer_available()
        finally:
            if worker.poll() is None:
                worker.send_signal(signal.SIGTERM)
                try:
                    worker.communicate(timeout=4)
                except subprocess.TimeoutExpired:
                    worker.kill()
                    worker.communicate(timeout=2)

    def test_unknown_cleanup_blocks_restart(self):
        process, _ = self.invoke()
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        path, data = next(iter(self.cleanup_records().items()))
        # 明确的记录故障注入；不是实际宿主清理或真实运行时证据。
        data.update(status="BLOCKED", cleanup_ok=False)
        path.write_text(json.dumps(data), encoding="utf-8")
        before = len(list((self.workspace / ".bmad-runtime").glob("agent-input-*.json")))
        process, record = self.invoke()
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(record["status"], "BLOCKED")
        self.assertIn("清理未知", record["reason"])
        self.assertEqual(len(list((self.workspace / ".bmad-runtime").glob("agent-input-*.json"))), before)
        self.assertEqual(json.loads(path.read_bytes()), data)
        self.assert_persistent_block()

    def test_distribution_entry_cannot_claim_isolated_copy(self):
        process, record = self.invoke(SUITE / "scripts/bmad-loop.py")
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(record["status"], "BLOCKED")
        self.assertIn("当前程序不是绑定运行副本", record["reason"])
        self.assertEqual(self.cleanup_records(), {})
        self.assertFalse((self.workspace / ".bmad-runtime").exists())
        self.assert_writer_available()


    def test_isolated_batch_repairs_failure_then_advances_under_same_lease(self):
        verification = dict(self.plan["tasks"][1]["verification"])
        verification.update(directory="next-tests", inputs=["next.txt"])
        self.plan["tasks"][1]["verification"] = verification
        (self.workspace / "next-tests").mkdir()
        (self.workspace / "next.txt").write_text("KEEP\n", encoding="utf-8")
        (self.workspace / "next-tests/test_sample.py").write_text(
            "import pathlib, unittest\nclass Sample(unittest.TestCase):\n"
            "    def test_sample(self):\n"
            "        self.assertEqual(pathlib.Path('next.txt').read_text(), 'DONE\\n')\n",
            encoding="utf-8")
        (self.workspace / "plan.md").write_text(
            '---\nplan_id: "ISOLATION-LOCAL-01"\nstatus: READY\n---\n\n```bmad-tasks\n'
            + json.dumps(self.plan, ensure_ascii=False) + "\n```\n", encoding="utf-8")
        request = json.loads((self.workspace / "request.json").read_bytes())
        request.update(task_id="T2", unfinished_files=["next.txt"])
        (self.workspace / "next-request.json").write_text(json.dumps(request), encoding="utf-8")
        (self.workspace / "batch.json").write_text(json.dumps({
            "schema_version": 1, "plan_id": self.plan["plan_id"], "tasks": [
                {"task_id": "T1", "request_file": "request.json"},
                {"task_id": "T2", "request_file": "next-request.json"},
            ],
        }), encoding="utf-8")
        self.driver(
            "import fcntl\n"
            "with open(" + repr(str(self.lock)) + ", 'rb') as stream:\n"
            "    try:\n"
            "        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
            "    except BlockingIOError:\n"
            "        pass\n"
            "    else:\n"
            "        raise AssertionError('修复或跨任务调用期间来源租约缺失')\n"
            "records = list(pathlib.Path(" + repr(str(self.lock.parent / 'task-runs')) + ").glob('*.json'))\n"
            "assert len(records) == 1\n"
            "persistent = json.loads(records[0].read_bytes())\n"
            "assert persistent['status'] == 'EXECUTING' and persistent['cleanup_ok'] is False\n"
            "with pathlib.Path('calls.jsonl').open('a') as stream:\n"
            "    stream.write(json.dumps({'task_id': request['task_id'], 'session_id': request['session_id'],\n"
            "                             'feedback': request['recent_verification']}) + '\\n')\n"
            "if request['task_id'] == 'T1':\n"
            "    feedback = request['recent_verification']\n"
            "    if feedback is None:\n"
            "        pathlib.Path('unfinished.py').write_text('FAILED FIRST\\n')\n"
            "    else:\n"
            "        assert feedback['task_id'] == 'T1' and feedback['status'] == 'BLOCKED'\n"
            "        assert feedback['returncode'] != 0 and feedback['tests_run'] == 1\n"
            "        assert feedback['log_summary']['text'] and feedback['process_receipt']\n"
            "        saved = pathlib.Path('plan.md').read_text().split('```bmad-tasks\\n', 1)[1].split('\\n```', 1)[0]\n"
            "        assert json.loads(saved)['tasks'][0]['status'] == 'PENDING'\n"
            "        pathlib.Path('unfinished.py').write_text('DONE\\n')\n"
            "else:\n"
            "    assert request['task_id'] == 'T2' and request['recent_verification'] is None\n"
            "    saved = pathlib.Path('plan.md').read_text().split('```bmad-tasks\\n', 1)[1].split('\\n```', 1)[0]\n"
            "    assert json.loads(saved)['tasks'][0]['status'] == 'COMPLETED'\n"
            "    pathlib.Path('next.txt').write_text('DONE\\n')\n")
        process = subprocess.run(
            self.command() + ["--batch-file", "batch.json", "--maximum-calls", "3"],
            cwd=self.workspace, stdin=subprocess.DEVNULL, capture_output=True,
            text=True, env=self.child_environment(), timeout=12)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        record = json.loads(process.stdout)
        calls = [json.loads(line) for line in
                 (self.workspace / "calls.jsonl").read_text().splitlines()]
        self.assertEqual([item["task_id"] for item in calls], ["T1", "T1", "T2"])
        self.assertEqual(len({item["session_id"] for item in calls}), 3)
        self.assertEqual(record["rounds"], 3)
        self.assertEqual(record["agent_calls"], 3)
        self.assertEqual(record["completed_tasks"], ["T1", "T2"])
        self.assertTrue(record["cleanup_ok"])
        feedback = calls[1]["feedback"]
        failed_process = json.loads((self.workspace / feedback["process_receipt"]).read_bytes())
        self.assertNotEqual(failed_process["returncode"], 0)
        self.assertTrue(failed_process["cleanup_ok"])
        saved = (self.workspace / "plan.md").read_text().split("```bmad-tasks\n", 1)[1].split("\n```", 1)[0]
        tasks = json.loads(saved)["tasks"]
        self.assertEqual([task["status"] for task in tasks], ["COMPLETED", "COMPLETED"])
        for task in tasks:
            verdict = json.loads((self.workspace / task["verdict_file"]).read_bytes())
            self.assertEqual(verdict["status"], "PASS")
            self.assertEqual(verdict["result"]["tests_run"], 1)
        terminal = next(iter(self.cleanup_records().values()))
        self.assertEqual(terminal["run_id"], record["run_id"])
        self.assertEqual(terminal["status"], "COMPLETED")
        self.assertTrue(terminal["cleanup_ok"])
        self.assert_writer_available()


if __name__ == "__main__":
    unittest.main()
