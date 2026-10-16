"""显式批次的本地反例；只执行合成驱动，不启动 Roo 或访问模型服务。"""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "scripts"))
import bmad_environment as environment
import bmad_state as state

CLI = SUITE / "scripts/bmad-loop.py"
CREDENTIAL = "BMAD_BATCH_ISOLATED_CREDENTIAL"


class BatchGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sandbox-batch-", dir=SUITE.parent / "tests")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        environment.register(self.root, ".bmad-control/environment.json", sys.executable)
        self.tasks = []
        self.entries = []
        for key, dependencies in (("T1", []), ("T2", ["T1"]), ("T3", [])):
            directory = "checks-" + key
            (self.root / directory).mkdir()
            (self.root / (key + ".txt")).write_text("KEEP\n", encoding="utf-8")
            (self.root / directory / "test_sample.py").write_text(
                "import pathlib, unittest\nclass Sample(unittest.TestCase):\n"
                "    def test_value(self):\n"
                "        self.assertEqual(pathlib.Path(" + repr(key + ".txt") + ").read_text(), 'DONE\\n')\n",
                encoding="utf-8")
            self.tasks.append({
                "task_id": key, "title": "隔离任务 " + key, "depends_on": dependencies,
                "status": "PENDING", "verdict_file": None,
                "verification": {"operation": "unit-test", "environment_file": ".bmad-control/environment.json",
                    "directory": directory, "pattern": "test_sample.py", "minimum_tests": 1,
                    "required_tests": ["test_sample.Sample.test_value"], "inputs": [key + ".txt"]}})
            request = {"goal": "完成隔离任务 " + key, "authorization": "仅本地夹具，不访问真实后端",
                       "task_id": key, "constraints": ["不得修改验收"], "capabilities": [],
                       "code_files": [], "unfinished_files": [key + ".txt"], "feedback": [],
                       "observed_host_bytes": None}
            self.put(key + "-request.json", request)
            if key != "T3":
                self.entries.append({"task_id": key, "request_file": key + "-request.json"})
        self.save_plan()
        self.save_batch()
        self.put("backend.json", {"schema_version": 1, "backend": "headless",
            "protocol": "bmad-headless-json-v1", "runtime_kind": "isolated-fixture",
            "source": "本测试生成的隔离驱动", "version": "batch-fixture-v1",
            "driver_file": "driver.py", "credential_environment": CREDENTIAL,
            "authorized": True, "authorization": "仅合成夹具", "new_session": True,
            "headless": True, "api_timeout_seconds": 3})
        self.driver("pathlib.Path(key + '.txt').write_text('DONE\\n')\n")

    def put(self, relative, data):
        (self.root / relative).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def save_plan(self):
        data = {"schema_version": 1, "plan_id": "BATCH-LOCAL-01", "tasks": self.tasks}
        (self.root / "plan.md").write_text(
            '---\nplan_id: "BATCH-LOCAL-01"\nstatus: READY\n---\n\n```bmad-tasks\n' +
            json.dumps(data, ensure_ascii=False) + '\n```\n\n- [ ] 范围外承诺保留\n', encoding="utf-8")

    def save_batch(self):
        self.put("batch.json", {"schema_version": 1, "plan_id": "BATCH-LOCAL-01", "tasks": self.entries})

    def driver(self, body):
        header = (
            "import argparse, json, pathlib, sys\n"
            "p = argparse.ArgumentParser(allow_abbrev=False)\n"
            "p.add_argument('--request-file', required=True)\n"
            "a = p.parse_args()\n"
            "request = json.loads(pathlib.Path(a.request_file).read_bytes())\n"
            "key = request['task_id']\n"
            "with pathlib.Path('calls.jsonl').open('a') as f:\n"
            "    f.write(json.dumps({'task_id': key, 'session_id': request['session_id'], "
            "'feedback': request['recent_verification']}) + '\\n')\n")
        tail = ("out = {k: request[k] for k in ('session_id', 'plan_id', 'task_id')}\n"
                "out.update(schema_version=1, status='OK')\n"
                "print('BMAD_AGENT_RESULT ' + json.dumps(out), flush=True)\n")
        (self.root / "driver.py").write_text(header + body + tail, encoding="utf-8")

    def invoke(self, *extra):
        env = dict(os.environ)
        env[CREDENTIAL] = "isolated-batch-secret"
        result = subprocess.run(
            [sys.executable, "-B", str(CLI), "start", "--workspace", str(self.root),
             "--plan-file", "plan.md", "--request-file", "T1-request.json",
             "--backend", "headless", "--backend-config", "backend.json", "--batch-file", "batch.json",
             "--save-progress", "--maximum-rounds", "4", "--maximum-calls", "4",
             "--timeout-seconds", "12", "--no-progress-rounds", "3", *extra],
            cwd=self.root, stdin=subprocess.DEVNULL, capture_output=True, text=True, env=env, timeout=16)
        self.assertLessEqual(len(result.stdout.encode()), 16384)
        self.assertNotIn("isolated-batch-secret", result.stdout + result.stderr)
        return result, json.loads(result.stdout)

    def calls(self):
        path = self.root / "calls.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def saved(self):
        return state.load_plan(self.root, "plan.md")[0]["tasks"]

    def assert_blocked(self, result, record):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(record["status"], "BLOCKED", record)
        self.assertTrue(record["cleanup_ok"], record)

    def test_failed_verification_retries_same_task_in_new_session(self):
        self.driver(
            "if key == 'T1' and request['recent_verification'] is None:\n"
            "    pathlib.Path('T1.txt').write_text('FAILED FIRST\\n')\n"
            "else:\n"
            "    if key == 'T1':\n"
            "        assert request['recent_verification']['status'] == 'BLOCKED'\n"
            "        assert request['recent_verification']['task_id'] == key\n"
            "        assert request['recent_verification']['returncode'] != 0\n"
            "        assert request['recent_verification']['log_summary']['text']\n"
            "        plan = pathlib.Path('plan.md').read_text().split('```bmad-tasks\\n')[1].split('```')[0]\n"
            "        assert json.loads(plan)['tasks'][0]['status'] == 'PENDING'\n"
            "    pathlib.Path(key + '.txt').write_text('DONE\\n')\n")
        result, record = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = self.calls()
        self.assertEqual([item["task_id"] for item in calls], ["T1", "T1", "T2"])
        self.assertEqual(len({item["session_id"] for item in calls}), 3)
        self.assertEqual(record["rounds"], 3)
        self.assertEqual(record["completed_tasks"], ["T1", "T2"])
        self.assertTrue(record["cleanup_ok"])

    def test_pass_automatically_selects_next_authorized_ready_task(self):
        result, record = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([item["task_id"] for item in self.calls()], ["T1", "T2"])
        self.assertEqual(record["completed_tasks"], ["T1", "T2"])
        self.assertEqual([item["status"] for item in self.saved()], ["COMPLETED", "COMPLETED", "PENDING"])
        self.assertIn("范围外承诺保留", (self.root / "plan.md").read_text())

    def test_unlisted_ready_task_is_never_selected(self):
        self.entries = self.entries[:1]
        self.save_batch()
        result, record = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([item["task_id"] for item in self.calls()], ["T1"])
        self.assertEqual((self.root / "T2.txt").read_text(), "KEEP\n")
        self.assertEqual((self.root / "T3.txt").read_text(), "KEEP\n")
        self.assertIn("T2 [READY]", record["state_card"])
        self.assertIn("T3 [READY]", record["state_card"])

    def test_feedback_does_not_leak_between_tasks(self):
        result, record = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(all(item["feedback"] is None for item in self.calls()))
        self.assertEqual(record["agent_calls"], 2)
        self.assertEqual(record["model_usage_coverage"], "UNKNOWN")

    def test_budget_exhaustion_stops_new_calls_and_preserves_changes(self):
        self.driver("pathlib.Path(key + '.txt').write_text('失败成果\\n')\n")
        result, record = self.invoke("--maximum-calls", "1")
        self.assert_blocked(result, record)
        self.assertIn("调用预算耗尽", record["reason"])
        self.assertEqual(len(self.calls()), 1)
        self.assertEqual(record["completed_tasks"], [])
        self.assertEqual((self.root / "T1.txt").read_text(), "失败成果\n")
        self.assertEqual([item["status"] for item in self.saved()], ["PENDING"] * 3)

    def test_contract_change_blocks_dependency_progress(self):
        self.driver("pathlib.Path('plan.md').write_text(pathlib.Path('plan.md').read_text() + '\\n外部修改保留\\n')\n")
        result, record = self.invoke()
        self.assert_blocked(result, record)
        self.assertIn("绑定契约", record["reason"])
        self.assertEqual(len(self.calls()), 1)
        self.assertIsNone(record["last_verdict"])
        self.assertIn("外部修改保留", (self.root / "plan.md").read_text())

    def test_mismatched_or_duplicate_batch_request_blocks_before_call(self):
        for entries in ([self.entries[0], self.entries[0]],
                        [{"task_id": "T2", "request_file": "T1-request.json"}],
                        [{"task_id": "UNKNOWN", "request_file": "T1-request.json"}]):
            with self.subTest(entries=entries):
                self.put("batch.json", {"schema_version": 1, "plan_id": "BATCH-LOCAL-01", "tasks": copy.deepcopy(entries)})
                result, record = self.invoke()
                self.assert_blocked(result, record)
                self.assertEqual(self.calls(), [])
                self.assertEqual(record["rounds"], 0)

    def test_agent_cannot_modify_acceptance_to_manufacture_pass(self):
        self.driver("pathlib.Path('checks-T1/test_sample.py').write_text('import unittest\\nclass Sample(unittest.TestCase):\\n    def test_value(self): self.assertTrue(True)\\n')\n")
        result, record = self.invoke()
        self.assert_blocked(result, record)
        self.assertIn("验收资产", record["reason"])
        self.assertEqual(len(self.calls()), 1)
        self.assertIsNone(record["last_verdict"])
        self.assertEqual(record["completed_tasks"], [])


    def test_initial_ready_task_is_selected_by_program_not_request_order(self):
        self.entries.reverse()
        self.save_batch()
        result, record = self.invoke("--request-file", "T2-request.json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([item["task_id"] for item in self.calls()], ["T1", "T2"])
        self.assertEqual(record["completed_tasks"], ["T1", "T2"])

    def test_future_task_acceptance_change_blocks_before_current_verification(self):
        self.driver("pathlib.Path('checks-T2/test_sample.py').write_text('import unittest\\nclass Sample(unittest.TestCase):\\n    def test_value(self): self.assertTrue(True)\\n')\n")
        result, record = self.invoke()
        self.assert_blocked(result, record)
        self.assertIn("验收资产", record["reason"])
        self.assertEqual(len(self.calls()), 1)
        self.assertIsNone(record["last_verdict"])
        self.assertEqual(record["completed_tasks"], [])

    def test_skipped_required_test_blocks_without_retry_or_next_task(self):
        (self.root / "checks-T1/test_sample.py").write_text(
            "import unittest\nclass Sample(unittest.TestCase):\n"
            "    @unittest.skip('必需验证不得跳过')\n"
            "    def test_value(self): self.fail('不可降低断言')\n", encoding="utf-8")
        result, record = self.invoke()
        self.assert_blocked(result, record)
        self.assertIn("跳过", record["reason"])
        self.assertEqual(len(self.calls()), 1)
        self.assertEqual(record["rounds"], 1)
        self.assertEqual(record["completed_tasks"], [])

    def test_missing_required_test_blocks_without_retry_or_next_task(self):
        self.tasks[0]["verification"]["required_tests"].append("test_sample.Sample.test_missing")
        self.save_plan()
        result, record = self.invoke()
        self.assert_blocked(result, record)
        self.assertIn("必需项缺失", record["reason"])
        self.assertEqual(len(self.calls()), 1)
        self.assertEqual(record["completed_tasks"], [])


if __name__ == "__main__":
    unittest.main()
