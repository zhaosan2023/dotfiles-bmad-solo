"""共享 HTTP 预算反例；不联网、不启动 Pi、不读取真实凭据。"""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "scripts"))
import bmad_pi_budget as budget
from bmad_supervisor import SupervisorError


class PiNetworkBudgetGuards(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        clock = patch.object(budget.time, "monotonic", side_effect=lambda: self.now)
        clock.start()
        self.addCleanup(clock.stop)
        self.meter = budget.PiNetworkBudget(
            maximum_requests=30, maximum_bytes=15_000_000, deadline=700.0)

    def finish(self, number, outcome="COMPLETE"):
        self.meter.finish_request(number, http_status=200, outcome=outcome)

    def test_exactly_thirty_actual_request_reservations_prohibit_thirty_first(self):
        for number in range(1, 31):
            self.assertEqual(self.meter.reserve_request(10), number)
            self.finish(number)
        with self.assertRaisesRegex(SupervisorError, "次数预算"):
            self.meter.reserve_request(1)
        self.assertEqual(self.meter.snapshot()["model_request_attempts"], 30)
        self.assertEqual(len(self.meter.snapshot()["events"]), 30)

    def test_failed_http_attempt_does_not_refund_or_reset_request_budget(self):
        number = self.meter.reserve_request(100)
        self.meter.finish_request(number, http_status=502, outcome="HTTP_ERROR")
        self.assertEqual(self.meter.reserve_request(100), 2)
        view = self.meter.snapshot()
        self.assertEqual(view["request_bytes"], 200)
        self.assertEqual(view["events"][0]["outcome"], "HTTP_ERROR")

    def test_request_body_over_budget_is_rejected_before_reservation(self):
        with self.assertRaisesRegex(SupervisorError, "数据预算"):
            self.meter.reserve_request(15_000_001)
        self.assertEqual(self.meter.requests, 0)
        self.assertEqual(self.meter.request_bytes, 0)
        with self.assertRaises(SupervisorError):
            self.meter.reserve_request(1)

    def test_request_and_response_share_decimal_fifteen_megabyte_cap(self):
        number = self.meter.reserve_request(100)
        self.assertEqual(self.meter.response_allowance(), 14_999_900)
        self.meter.accept_response(number, 14_999_900)
        self.assertEqual(self.meter.response_allowance(), 0)
        with self.assertRaisesRegex(SupervisorError, "数据预算"):
            self.meter.accept_response(number, 1)
        self.assertEqual(self.meter.snapshot()["data_bytes"], 15_000_000)

    def test_concurrent_inflight_request_blocks_without_second_reservation(self):
        self.meter.reserve_request(100)
        with self.assertRaisesRegex(SupervisorError, "在途"):
            self.meter.reserve_request(100)
        self.assertEqual(self.meter.requests, 1)

    def test_deadline_blocks_new_request_and_further_response_reads(self):
        number = self.meter.reserve_request(100)
        self.now = 700.0
        with self.assertRaisesRegex(SupervisorError, "截止时间"):
            self.meter.response_allowance()
        with self.assertRaises(SupervisorError):
            self.meter.accept_response(number, 1)
        self.meter.finish_request(number, http_status=None, outcome="BUDGET_STOP")
        self.assertIsNotNone(self.meter.snapshot()["events"][0]["finished_at"])
        self.assertEqual(self.meter.snapshot()["status"], "BLOCKED")

    def test_cancellation_blocks_before_any_request_is_reserved(self):
        cancelled = budget.PiNetworkBudget(
            maximum_requests=30, maximum_bytes=15_000_000, deadline=700,
            cancel_requested=lambda: True)
        with self.assertRaisesRegex(SupervisorError, "停止请求"):
            cancelled.reserve_request(1)
        self.assertEqual(cancelled.requests, 0)

    def test_response_without_reservation_or_after_finish_fails_closed(self):
        with self.assertRaises(SupervisorError):
            self.meter.accept_response(1, 1)
        fresh = budget.PiNetworkBudget(
            maximum_requests=30, maximum_bytes=15_000_000, deadline=700)
        number = fresh.reserve_request(1)
        fresh.finish_request(number, http_status=200, outcome="COMPLETE")
        with self.assertRaisesRegex(SupervisorError, "结束后"):
            fresh.accept_response(number, 1)

    def test_invalid_caps_and_boolean_byte_counts_are_not_accepted(self):
        for requests in (True, 0, 31, "30"):
            with self.assertRaises(SupervisorError):
                budget.PiNetworkBudget(
                    maximum_requests=requests, maximum_bytes=15_000_000, deadline=700)
        for size in (True, 255, 15_000_001, "15000000"):
            with self.assertRaises(SupervisorError):
                budget.PiNetworkBudget(
                    maximum_requests=30, maximum_bytes=size, deadline=700)
        for size in (True, -1, 1.5):
            with self.assertRaises(SupervisorError):
                self.meter.reserve_request(size)

    def test_snapshot_is_read_only_metadata_and_never_claims_upstream_coverage(self):
        number = self.meter.reserve_request(10)
        self.meter.accept_response(number, 20)
        self.finish(number)
        view = self.meter.snapshot()
        view["events"][0]["outcome"] = "CHANGED"
        self.assertEqual(self.meter.snapshot()["events"][0]["outcome"], "COMPLETE")
        self.assertEqual(view["upstream_gateway_retry_coverage"], "UNKNOWN")
        self.assertEqual(view["data_bytes"], 30)
        self.assertNotIn("payload", view)
        self.assertNotIn("credential", view)
        self.assertNotEqual(view["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
