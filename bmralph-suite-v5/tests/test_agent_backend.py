"""隔离无头驱动反例；不安装或启动真实 Roo，不改变宿主网络。"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "scripts"))
import bmad_environment as environment
import bmad_loop as loop

CREDENTIAL = "BMAD_ISOLATED_TEST_CREDENTIAL"
CLI = SUITE / "scripts/bmad-loop.py"


class AgentBackendGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sandbox-agent-", dir=SUITE.parent / "tests")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "tests").mkdir()
        (self.root / "unfinished.py").write_text("KEEP\n", encoding="utf-8")
        (self.root / "tests/test_sample.py").write_text(
            "import pathlib, unittest\nclass Sample(unittest.TestCase):\n"
            "    def test_sample(self):\n"
            "        self.assertEqual(pathlib.Path('unfinished.py').read_text(), 'DONE\\n')\n",
            encoding="utf-8")
        environment.register(self.root, ".bmad-control/environment.json", sys.executable)
        verification = {
            "operation": "unit-test", "environment_file": ".bmad-control/environment.json",
            "directory": "tests", "pattern": "test_sample.py", "minimum_tests": 1,
            "required_tests": ["test_sample.Sample.test_sample"], "inputs": ["unfinished.py"],
        }
        self.plan = {"schema_version": 1, "plan_id": "AGENT-LOCAL-01", "tasks": [
            {"task_id": "T1", "title": "隔离驱动当前任务", "depends_on": [], "status": "PENDING",
             "verification": verification, "verdict_file": None},
            {"task_id": "T2", "title": "保留后续事项", "depends_on": ["T1"], "status": "PENDING",
             "verification": verification, "verdict_file": None},
        ]}
        (self.root / "plan.md").write_text(
            '---\nplan_id: "AGENT-LOCAL-01"\nstatus: READY\n---\n\n```bmad-tasks\n' +
            json.dumps(self.plan, ensure_ascii=False) + "\n```\n", encoding="utf-8")
        request = {
            "goal": "仅本地模拟驱动", "authorization": "隔离夹具；无真实 Agent、公网或提交操作",
            "task_id": "T1", "constraints": ["保持对照源码只读"], "capabilities": [],
            "code_files": [], "unfinished_files": ["unfinished.py"], "feedback": [],
            "observed_host_bytes": None,
        }
        (self.root / "request.json").write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
        self.config = {
            "schema_version": 1, "backend": "headless", "protocol": "bmad-headless-json-v1",
            "runtime_kind": "isolated-fixture", "source": "本测试生成的项目内驱动",
            "version": "fixture-v1", "driver_file": "driver.py", "credential_environment": CREDENTIAL,
            "authorized": True, "authorization": "仅本地隔离夹具", "new_session": True,
            "headless": True, "api_timeout_seconds": 5,
        }
        self.save_config()
        self.driver("pathlib.Path('unfinished.py').write_text('DONE\\n')\n")

    def save_config(self):
        (self.root / "backend.json").write_text(json.dumps(self.config, ensure_ascii=False), encoding="utf-8")

    def driver(self, body, *, result=True):
        header = (
            "import argparse, json, pathlib, sys, time\n"
            "p = argparse.ArgumentParser(allow_abbrev=False)\n"
            "p.add_argument('--request-file', required=True)\n"
            "a = p.parse_args()\n"
            "request = json.loads(pathlib.Path(a.request_file).read_bytes())\n"
            "out = {key: request[key] for key in ('session_id', 'plan_id', 'task_id')}\n"
            "out.update(schema_version=1, status='OK')\n"
        )
        tail = "print('BMAD_AGENT_RESULT ' + json.dumps(out), flush=True)\n" if result else ""
        (self.root / "driver.py").write_text(header + body + tail, encoding="utf-8")

    def invoke(self, *extra, credential=True):
        env = dict(os.environ)
        env.pop(CREDENTIAL, None)
        if credential:
            env[CREDENTIAL] = "isolated-secret-not-for-production"
        result = subprocess.run(
            [sys.executable, "-B", str(CLI), "start", "--workspace", str(self.root),
             "--plan-file", "plan.md", "--request-file", "request.json", "--backend", self.config["backend"],
             "--backend-config", "backend.json", "--maximum-rounds", "3", "--timeout-seconds", "8",
             "--no-progress-rounds", "2", "--save-progress", *extra],
            cwd=self.root, stdin=subprocess.DEVNULL, capture_output=True, text=True, env=env, timeout=12)
        self.assertLessEqual(len(result.stdout.encode("utf-8")), 16384)
        self.assertNotIn("isolated-secret-not-for-production", result.stdout + result.stderr)
        return result, json.loads(result.stdout)

    def assert_blocked(self, result, record):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(record["status"], "BLOCKED", record)
        self.assertFalse(record["task_progress_saved"])

    def test_driver_success_requires_independent_verification_then_saves_one_task(self):
        result, record = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(record["last_agent"]["status"], "PASS")
        self.assertEqual(record["status"], "COMPLETED")
        self.assertTrue(record["task_progress_saved"])
        self.assertTrue(record["cleanup_ok"])
        self.assertIn("T2 [READY]", record["state_card"])
        verdict = json.loads((self.root / record["last_verdict"]).read_bytes())
        self.assertEqual(verdict["result"]["tests_run"], 1)
        self.assertEqual(verdict["status"], "PASS")

    def test_missing_credentials_blocks_before_agent_or_business_execution(self):
        before = (self.root / "plan.md").read_bytes()
        result, record = self.invoke(credential=False)
        self.assert_blocked(result, record)
        self.assertIn("凭据缺失", record["reason"])
        self.assertEqual(record["rounds"], 0)
        self.assertIsNone(record["last_verdict"])
        self.assertEqual((self.root / "plan.md").read_bytes(), before)
        self.assertEqual(list((self.root / ".bmad-runtime").glob("agent-input-*.json")), [])

    def test_unauthorized_driver_is_never_started(self):
        self.config["authorized"] = False
        self.save_config()
        result, record = self.invoke()
        self.assert_blocked(result, record)
        self.assertIn("未授权", record["reason"])
        self.assertEqual(record["rounds"], 0)
        self.assertEqual((self.root / "unfinished.py").read_text(), "KEEP\n")

    def test_authentication_and_permission_failures_stop_without_retry(self):
        for status in ("AUTH_FAILED", "PERMISSION_DENIED"):
            with self.subTest(status=status):
                self.driver("out['status'] = " + repr(status) + "\n")
                result, record = self.invoke()
                self.assert_blocked(result, record)
                self.assertEqual(record["last_agent"]["category"], status)
                self.assertEqual(record["rounds"], 1)
                self.assertIsNone(record["last_verdict"])
                self.assertTrue(record["cleanup_ok"])

    def test_nonzero_exit_cannot_be_overridden_by_valid_ok_result(self):
        self.driver("print('BMAD_AGENT_RESULT ' + json.dumps(out), flush=True)\nsys.exit(7)\n", result=False)
        result, record = self.invoke()
        self.assert_blocked(result, record)
        self.assertEqual(record["last_agent"]["returncode"], 7)
        self.assertIsNone(record["last_verdict"])

    def test_missing_duplicate_and_wrong_session_results_block(self):
        variants = (
            ("print('TASK COMPLETE', flush=True)\n", False),
            ("print('BMAD_AGENT_RESULT ' + json.dumps(out), flush=True)\n", True),
            ("out['session_id'] = 'old-session'\n", True),
        )
        for body, structured in variants:
            with self.subTest(body=body):
                self.driver(body, result=structured)
                result, record = self.invoke()
                self.assert_blocked(result, record)
                self.assertIsNone(record["last_verdict"])

    def test_api_timeout_cleans_group_and_preserves_local_artifacts(self):
        self.config["api_timeout_seconds"] = 0.15
        self.save_config()
        self.driver("pathlib.Path('kept.txt').write_text('保留现场')\ntime.sleep(5)\n")
        result, record = self.invoke()
        self.assert_blocked(result, record)
        self.assertEqual(record["last_agent"]["category"], "TIMEOUT")
        self.assertTrue(record["last_agent"]["timed_out"])
        self.assertTrue(record["cleanup_ok"])
        self.assertEqual((self.root / "kept.txt").read_text(), "保留现场")
        self.assertTrue((self.root / record["final_receipt"]).exists())

    def test_agent_ok_and_file_change_do_not_mask_business_failure(self):
        self.driver("pathlib.Path('unfinished.py').write_text('NOT DONE\\n')\n")
        result, record = self.invoke()
        self.assert_blocked(result, record)
        self.assertEqual(record["last_agent"]["status"], "PASS")
        verdict = json.loads((self.root / record["last_verdict"]).read_bytes())
        self.assertEqual(verdict["status"], "BLOCKED")
        self.assertIn("持续无进展", record["reason"])
        self.assertEqual((self.root / "unfinished.py").read_text(), "NOT DONE\n")

    def test_new_round_receives_actual_failure_feedback_in_new_session(self):
        self.driver(
            "marker = pathlib.Path('previous-session.txt')\n"
            "if marker.exists():\n"
            "    assert marker.read_text() != request['session_id']\n"
            "    assert request['recent_verification']['status'] == 'BLOCKED'\n"
            "    assert request['recent_verification']['process_receipt']\n"
            "    pathlib.Path('unfinished.py').write_text('DONE\\n')\n"
            "else:\n"
            "    marker.write_text(request['session_id'])\n")
        result, record = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(record["rounds"], 2)
        self.assertTrue(record["task_progress_saved"])

    def test_simulated_disconnection_allows_local_step_and_durable_receipts(self):
        self.driver(
            "import socket\nfrom unittest.mock import patch\n"
            "with patch.object(socket.socket, 'connect', side_effect=OSError('模拟连接已关闭')):\n"
            "    try:\n"
            "        with socket.socket() as connection:\n"
            "            connection.connect(('127.0.0.1', 1))\n"
            "    except OSError:\n"
            "        pathlib.Path('connection-state.txt').write_text('DISCONNECTED')\n"
            "    else:\n"
            "        raise AssertionError('模拟连接未关闭')\n"
            "pathlib.Path('unfinished.py').write_text('DONE\\n')\n")
        result, record = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.root / "connection-state.txt").read_text(), "DISCONNECTED")
        saved = json.loads((self.root / record["final_receipt"]).read_bytes())
        self.assertEqual(saved, record)
        self.assertTrue((self.root / record["last_agent"]["process_receipt"]).exists())
        self.assertEqual(loop.status(self.root)["status"], "COMPLETED")
        self.assertFalse(loop.status(self.root)["writer_active"])

    def test_network_error_blocks_and_keeps_unfinished_changes(self):
        self.driver("pathlib.Path('kept.txt').write_text('失败成果')\nout['status'] = 'NETWORK_ERROR'\n")
        result, record = self.invoke()
        self.assert_blocked(result, record)
        self.assertEqual(record["last_agent"]["category"], "NETWORK_ERROR")
        self.assertIsNone(record["last_verdict"])
        self.assertEqual((self.root / "kept.txt").read_text(), "失败成果")

    def test_real_roo_without_required_runtime_evidence_fails_closed(self):
        self.config.update(backend="roo-cli", runtime_kind="roo-cli")
        self.save_config()
        result, record = self.invoke()
        self.assert_blocked(result, record)
        self.assertIn("实证", record["reason"])
        self.assertEqual(record["rounds"], 0)

    def test_complete_driver_envelope_budget_blocks_before_launch(self):
        result, record = self.invoke("--startup-bytes", "256")
        self.assert_blocked(result, record)
        self.assertIn("预算", record["reason"])
        self.assertEqual((self.root / "unfinished.py").read_text(), "KEEP\n")


if __name__ == "__main__":
    unittest.main()
