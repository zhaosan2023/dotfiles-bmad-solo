"""Pi 回执裁决的八项必需反例；全部记录为合成输入，不启动 Pi 或联网。

测试通过只证明快照校验逻辑，不证明快照来源、真实执行或客户端断开。
生产回执必须另由真实进程、日志及独立验证采集，不从本夹具导出。
"""
import copy
from pathlib import Path
import sys
import unittest

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "scripts"))
from bmad_pi_evidence import evaluate_trial

WORKSPACE = "/synthetic-only/pi-workspace"
PLAN_ID = "PI-EVIDENCE-UNIT-01"
DISCONNECT = "2026-10-18T12:00:05+00:00"


class PiHeadlessEvidenceGuards(unittest.TestCase):
    def sample(self):
        def verification(status, code, receipt):
            return {"operation": "unit-test", "status": status, "returncode": code,
                    "tests_run": 8, "minimum_tests": 8, "missing_required_tests": [],
                    "skipped": 0, "cleanup_ok": True, "timed_out": False,
                    "receipt": receipt, "independent": True}

        def round_record(number, task, status, code, feedback=None):
            return {"round": number, "task_id": task, "session_id": "outer-" + str(number),
                    "pi_session_id": "pi-" + str(number), "new_session": True,
                    "agent_status": "PASS", "agent_returncode": 0, "cleanup_ok": True,
                    "settled": True, "aborted": False,
                    "feedback": feedback,
                    "verification": verification(status, code, "verification-" + str(number)),
                    "model_events": [{"request_number": number,
                                      "at": "2026-10-18T12:00:0" + str(2 + number * 2) + "+00:00",
                                      "kind": "model_complete", "outcome": "COMPLETE"}]}

        first = round_record(1, "T1", "BLOCKED", 1)
        second = round_record(2, "T1", "PASS", 0, {
            "task_id": "T1", "status": "BLOCKED", "returncode": 1,
            "receipt": "verification-1", "tests_run": 8,
            "log_summary": "Synthetic assertion failure, not a real execution log"})
        third = round_record(3, "T2", "PASS", 0)
        return {"schema_version": 1,
                "runtime": {"kind": "pi-agent", "source": "https://github.com/earendil-works/pi",
                            "version": "1.3.0", "workspace": WORKSPACE, "plan_id": PLAN_ID,
                            "headless": True, "independent_auth": True,
                            "rules_loaded": True, "tools_observed": ["read", "edit"],
                            "gateway": "http://127.0.0.1:8080/v1"},
                "authorized_tasks": ["T1", "T2"], "dependencies": {"T1": [], "T2": ["T1"]},
                "rounds": [first, second, third],
                "budget": {"maximum_requests": 30, "request_attempts": 3,
                           "maximum_data_bytes": 15000000, "data_bytes": 1400,
                           "measurement": "PI_TO_GATEWAY_HTTP_BODY_ONLY",
                           "maximum_seconds": 600, "elapsed_seconds": 10,
                           "maximum_session_seconds": 360, "longest_session_seconds": 4,
                           "no_progress_rounds": 6, "usage_coverage": "PI_TO_GATEWAY_HTTP_BODY_ONLY",
                           "upstream_gateway_retry_coverage": "UNKNOWN"},
                "stop": {"reason": "authorized_tasks_verified", "at": "2026-10-18T12:00:10+00:00",
                         "cleanup_ok": True, "writer_active": False, "inflight_requests": 0,
                         "request_attempts_at_stop": 3, "request_attempts_after_stop": 3}}

    def check(self, sample):
        return evaluate_trial(sample, expected_workspace=WORKSPACE, expected_plan_id=PLAN_ID,
                              authorized_tasks=("T1", "T2"), disconnect_at=DISCONNECT)

    def assert_blocked(self, sample):
        result = self.check(sample)
        self.assertEqual(result["status"], "BLOCKED", result)
        self.assertTrue(result["reason"])
        self.assertIs(result["adr_accepted"], False)
        self.assertIs(result["plan_archived"], False)

    def test_fixture_or_exit_zero_is_not_real_runtime_evidence(self):
        self.assertEqual(self.check(self.sample())["status"], "PASS")
        for kind in ("isolated-fixture", "local-verification", "roo-cli", "unknown"):
            sample = self.sample()
            sample["runtime"]["kind"] = kind
            self.assert_blocked(sample)
        sample = self.sample()
        sample["rounds"] = []
        self.assert_blocked(sample)
        sample = self.sample()
        sample["rounds"][1]["settled"] = False
        self.assert_blocked(sample)

    def test_runtime_version_workspace_and_task_binding_are_required(self):
        for key, value in (("source", "https://example.invalid/pi"), ("version", "1.3.1"),
                           ("workspace", "/another-workspace"), ("plan_id", "ANOTHER-PLAN"),
                           ("headless", False), ("independent_auth", False),
                           ("rules_loaded", False), ("tools_observed", [])):
            sample = self.sample()
            sample["runtime"][key] = value
            self.assert_blocked(sample)
        sample = self.sample()
        sample["rounds"][1]["task_id"] = "UNAUTHORIZED"
        self.assert_blocked(sample)

    def test_failure_requires_actual_verification_and_new_session_feedback(self):
        for mutate in (lambda s: s["rounds"][0]["verification"].update(independent=False),
                       lambda s: s["rounds"][0]["verification"].update(returncode=0),
                       lambda s: s["rounds"][0]["verification"].update(tests_run=0),
                       lambda s: s["rounds"][0]["verification"].update(skipped=1),
                       lambda s: s["rounds"][1].update(session_id="outer-1"),
                       lambda s: s["rounds"][1].update(pi_session_id="pi-1"),
                       lambda s: s["rounds"][1].update(feedback=None),
                       lambda s: s["rounds"][1]["feedback"].update(receipt="unrelated"),
                       lambda s: s["rounds"][1]["feedback"].update(returncode=0)):
            sample = self.sample()
            mutate(sample)
            self.assert_blocked(sample)

    def test_client_disconnect_requires_new_model_or_tool_steps(self):
        sample = self.sample()
        for item in sample["rounds"]:
            item["model_events"][0]["at"] = "2026-10-18T12:00:04+00:00"
        self.assert_blocked(sample)
        sample = self.sample()
        for item in sample["rounds"]:
            item["model_events"][0]["kind"] = "process_alive"
        self.assert_blocked(sample)
        sample = self.sample()
        sample["rounds"] = sample["rounds"][:2]
        sample["rounds"][1]["model_events"] = []
        self.assert_blocked(sample)

    def test_next_task_requires_independent_pass_and_explicit_batch_membership(self):
        for mutate in (lambda s: s["rounds"][1]["verification"].update(status="BLOCKED", returncode=1),
                       lambda s: s["rounds"][1]["verification"].update(independent=False),
                       lambda s: s["rounds"][2].update(task_id="T3"),
                       lambda s: s.update(authorized_tasks=["T1"]),
                       lambda s: s["dependencies"].update(T2=["UNKNOWN"]),
                       lambda s: s["rounds"][1]["verification"].update(missing_required_tests=["required"]),
                       lambda s: s["rounds"][1]["verification"].update(timed_out=True)):
            sample = self.sample()
            mutate(sample)
            self.assert_blocked(sample)

    def test_budget_stop_requires_no_new_calls_and_confirmed_cleanup(self):
        sample = self.sample()
        sample["stop"]["reason"] = "data_budget"
        self.assertEqual(self.check(sample)["status"], "PASS")
        for mutate in (lambda s: s["stop"].update(cleanup_ok=False),
                       lambda s: s["stop"].update(writer_active=True),
                       lambda s: s["stop"].update(inflight_requests=1),
                       lambda s: s["stop"].update(request_attempts_after_stop=4),
                       lambda s: s["budget"].update(request_attempts=31),
                       lambda s: s["budget"].update(data_bytes=15000001),
                       lambda s: s["budget"].update(elapsed_seconds=601),
                       lambda s: s["budget"].update(longest_session_seconds=361),
                       lambda s: s["budget"].update(no_progress_rounds=3)):
            sample = self.sample()
            mutate(sample)
            self.assert_blocked(sample)

    def test_unknown_cleanup_or_usage_never_manufactures_pass(self):
        for mutate in (lambda s: s["rounds"][1].update(cleanup_ok=None),
                       lambda s: s["rounds"][1].update(agent_returncode=1),
                       lambda s: s["rounds"][1].update(aborted=True),
                       lambda s: s["budget"].update(usage_coverage="UNKNOWN"),
                       lambda s: s["budget"].update(measurement="driver_start_count"),
                       lambda s: s["budget"].update(request_attempts=True),
                       lambda s: s["budget"].update(data_bytes=-1)):
            sample = self.sample()
            mutate(sample)
            self.assert_blocked(sample)
        for invalid in (None, {}, {"schema_version": 2}):
            self.assert_blocked(invalid)

    def test_receipt_checker_unit_pass_does_not_accept_adr_or_archive_plan(self):
        sample = self.sample()
        before = copy.deepcopy(sample)
        result = self.check(sample)
        self.assertEqual(result["status"], "PASS", result)
        self.assertIs(result["adr_accepted"], False)
        self.assertIs(result["plan_archived"], False)
        self.assertTrue(result["evidence_boundary"])
        self.assertEqual(sample, before)
        self.assertNotIn("api_key", repr(result).lower())


if __name__ == "__main__":
    unittest.main()
