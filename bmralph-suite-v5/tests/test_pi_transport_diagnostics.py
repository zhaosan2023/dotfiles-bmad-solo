"""转发分类离线反例；仅临时回环客户端，上游完全拦截。

不读取真实回执正文或凭据，不连接8080、不启动Pi。合成失败不能
追认历史运行根因；这里只证明新增分类在指定调用点准确且不泄密。
"""
import http.client
import json
import time
import unittest
from unittest.mock import patch

import test_pi_transport as fixtures
from bmad_pi_budget import PiNetworkBudget

transport = fixtures.transport
SENSITIVE = "synthetic-body-header-exception-marker-not-a-secret"
FIELDS = {
    "schema_version", "stage", "code", "exception_category", "request_number",
    "http_status", "content_type_is_sse", "headers_sent", "eof_seen",
    "done_seen", "response_bytes_read", "response_bytes_forwarded",
}


class PiTransportDiagnosticGuards(unittest.TestCase):
    def setUp(self):
        self.guards = fixtures.PiTransportGuards(
            "test_missing_done_is_failure_not_successful_stream_completion")
        self.guards.setUp()
        self.addCleanup(self.guards.doCleanups)

    def failed(self, gateway, *, stage, code, category="GUARD_REJECTION"):
        view = gateway.snapshot()
        self.assertEqual(view["status"], "BLOCKED")
        self.assertTrue(view["cleanup_ok"])
        self.assertFalse(view["thread_active"])
        failure = view["failure"]
        self.assertEqual(set(failure), FIELDS)
        self.assertEqual(failure["stage"], stage)
        self.assertEqual(failure["code"], code)
        self.assertEqual(failure["exception_category"], category)
        public = json.dumps(view)
        self.assertNotIn(SENSITIVE, public)
        self.assertNotIn(fixtures.TEST_CREDENTIAL, public)
        return failure

    def test_eof_after_data_is_classified_without_recording_body_or_assuming_root_cause(self):
        body = b'data: {"synthetic":"' + SENSITIVE.encode() + b'"}\n\n'
        self.guards.response.body = body
        gateway = self.guards.gateway()
        with gateway:
            token = gateway.token
            self.assertEqual(self.guards.post(gateway)[0], 200)
        failure = self.failed(gateway, stage="UPSTREAM_READ", code="EOF_BEFORE_DONE")
        self.assertTrue(failure["eof_seen"])
        self.assertFalse(failure["done_seen"])
        self.assertTrue(failure["content_type_is_sse"])
        self.assertTrue(failure["headers_sent"])
        self.assertEqual(failure["response_bytes_read"], len(body))
        self.assertEqual(failure["response_bytes_forwarded"], len(body))
        self.assertNotIn(token, json.dumps(gateway.snapshot()))
        self.assertEqual(self.guards.budget.snapshot()["events"][0]["outcome"], "NETWORK_ERROR")

    def test_non_sse_is_distinguished_from_eof_and_header_values_are_not_saved(self):
        self.guards.response.content_type = "application/" + SENSITIVE
        gateway = self.guards.gateway()
        with gateway:
            self.assertEqual(self.guards.post(gateway)[0], 502)
        failure = self.failed(gateway, stage="UPSTREAM_HEADERS", code="UPSTREAM_NOT_SSE")
        self.assertEqual(failure["http_status"], 200)
        self.assertFalse(failure["content_type_is_sse"])
        self.assertFalse(failure["eof_seen"])
        self.assertFalse(failure["headers_sent"])
        self.assertEqual(failure["response_bytes_read"], 0)

    def test_upstream_http_error_retains_first_failure_without_retry_or_body_capture(self):
        self.guards.response.status = 503
        self.guards.response.body = SENSITIVE.encode()
        gateway = self.guards.gateway()
        with gateway:
            self.assertEqual(self.guards.post(gateway)[0], 503)
            first = gateway.snapshot()["failure"]
            self.assertEqual(self.guards.post(gateway)[0], 502)
        failure = self.failed(gateway, stage="UPSTREAM_HEADERS", code="UPSTREAM_HTTP_STATUS",
                              category=None)
        self.assertEqual(first, failure)
        self.assertEqual(failure["http_status"], 503)
        self.assertEqual(len(self.guards.upstream.calls), 1)
        self.assertEqual(self.guards.response.read_sizes, [])

    def test_upstream_timeout_does_not_save_exception_message(self):
        self.guards.response.read1 = lambda size: (_ for _ in ()).throw(TimeoutError(SENSITIVE))
        gateway = self.guards.gateway()
        with gateway:
            self.assertEqual(self.guards.post(gateway)[0], 200)
        failure = self.failed(gateway, stage="UPSTREAM_READ", code="UPSTREAM_READ_ERROR",
                              category="TIMEOUT")
        self.assertFalse(failure["eof_seen"])
        self.assertEqual(failure["response_bytes_read"], 0)

    def test_incomplete_read_does_not_leak_partial_body_or_count_it_as_forwarded(self):
        error = http.client.IncompleteRead(SENSITIVE.encode(), 100)
        self.guards.response.read1 = lambda size: (_ for _ in ()).throw(error)
        gateway = self.guards.gateway()
        with gateway:
            self.guards.post(gateway)
        failure = self.failed(gateway, stage="UPSTREAM_READ", code="UPSTREAM_READ_ERROR",
                              category="HTTP_INCOMPLETE_READ")
        self.assertEqual(failure["response_bytes_read"], 0)
        self.assertEqual(failure["response_bytes_forwarded"], 0)
        self.assertFalse(failure["eof_seen"])

    def test_upstream_send_and_headers_failures_have_distinct_stages(self):
        for method, stage, code, error, category in (
            ("request", "UPSTREAM_SEND", "UPSTREAM_SEND_ERROR",
             ConnectionResetError(SENSITIVE), "CONNECTION_CLOSED"),
            ("getresponse", "UPSTREAM_HEADERS", "UPSTREAM_HEADERS_ERROR",
             http.client.BadStatusLine(SENSITIVE), "HTTP_PROTOCOL_ERROR"),
        ):
            with self.subTest(method=method):
                # 每项独立预算及传输实例；不会因前项失败重置真实任务预算。
                self.guards.budget = PiNetworkBudget(
                    maximum_requests=30, maximum_bytes=15_000_000,
                    deadline=self.guards.deadline)
                gateway = self.guards.gateway()
                with patch.object(self.guards.upstream, method, side_effect=error):
                    with gateway:
                        self.assertEqual(self.guards.post(gateway)[0], 502)
                self.failed(gateway, stage=stage, code=code, category=category)
                self.assertEqual(self.guards.budget.requests, 1)

    def test_downstream_write_failure_is_not_reported_as_upstream_eof(self):
        original = transport.BaseHTTPRequestHandler.end_headers

        class FailingWriter:
            def __init__(self, stream):
                self.stream = stream

            def write(self, body):
                raise BrokenPipeError(SENSITIVE)

            def __getattr__(self, name):
                return getattr(self.stream, name)

        def end_headers(handler):
            original(handler)
            handler.wfile = FailingWriter(handler.wfile)

        gateway = self.guards.gateway()
        with patch.object(transport.BaseHTTPRequestHandler, "end_headers", end_headers):
            with gateway:
                self.assertEqual(self.guards.post(gateway), (200, b""))
        failure = self.failed(gateway, stage="DOWNSTREAM_WRITE", code="DOWNSTREAM_WRITE_ERROR",
                              category="CONNECTION_CLOSED")
        self.assertEqual(failure["response_bytes_read"], len(fixtures.STREAM))
        self.assertEqual(failure["response_bytes_forwarded"], 0)
        self.assertFalse(failure["eof_seen"])
        self.assertFalse(failure["done_seen"])
        self.assertEqual(self.guards.budget.response_bytes, len(fixtures.STREAM))

    def test_data_budget_failure_remains_fail_closed_without_changing_byte_limit(self):
        self.guards.budget = PiNetworkBudget(maximum_requests=30, maximum_bytes=256,
                                            deadline=self.guards.deadline)
        self.guards.response.body = b"x" * 1000
        gateway = self.guards.gateway()
        with gateway:
            self.guards.post(gateway)
        failure = self.failed(gateway, stage="STREAM_CONTROL", code="RESPONSE_DATA_BUDGET_STOP")
        self.assertFalse(failure["eof_seen"])
        self.assertEqual(self.guards.budget.snapshot()["data_bytes"], 256)
        self.assertEqual(self.guards.budget.snapshot()["events"][0]["outcome"], "BUDGET_STOP")

    def test_internal_auth_failure_has_no_request_or_sensitive_header_in_snapshot(self):
        gateway = self.guards.gateway()
        with gateway:
            self.assertEqual(self.guards.post(gateway, authorization="Bearer " + SENSITIVE)[0], 502)
        failure = self.failed(gateway, stage="CLIENT_REQUEST", code="INTERNAL_AUTH_REJECTED")
        self.assertIsNone(failure["request_number"])
        self.assertIsNone(failure["http_status"])
        self.guards.factory.assert_not_called()
        self.assertEqual(self.guards.budget.requests, 0)

    def test_malformed_request_json_is_not_saved_in_exception_or_failure_snapshot(self):
        gateway = self.guards.gateway()
        with gateway:
            self.assertEqual(self.guards.post(gateway, body=SENSITIVE.encode())[0], 502)
        self.failed(gateway, stage="REQUEST_VALIDATION", code="REQUEST_JSON_INVALID",
                    category="DECODE_OR_TYPE_ERROR")
        self.guards.factory.assert_not_called()

    def test_success_with_fragmented_crlf_done_has_no_failure_and_preserves_snapshot_isolation(self):
        chunks = [b'data: {"choices":[]}\r\n\r\n', b'data: [DO', b'NE]\r', b'\n\r\n']

        def read1(size):
            chunk = chunks.pop(0) if chunks else b""
            self.assertLessEqual(len(chunk), size)
            return chunk

        self.guards.response.read1 = read1
        gateway = self.guards.gateway()
        with gateway:
            self.assertEqual(self.guards.post(gateway)[0], 200)
        self.assertEqual(gateway.snapshot()["status"], "READY")
        self.assertIsNone(gateway.snapshot()["failure"])
        self.assertTrue(gateway.cleanup_ok)
        self.assertEqual(self.guards.budget.snapshot()["events"][0]["outcome"], "COMPLETE")

    def test_mutating_returned_failure_cannot_change_saved_diagnostic(self):
        self.guards.response.body = b""
        gateway = self.guards.gateway()
        with gateway:
            self.guards.post(gateway)
        view = gateway.snapshot()
        view["failure"]["code"] = SENSITIVE
        self.assertEqual(gateway.snapshot()["failure"]["code"], "EOF_BEFORE_DONE")
        self.assertNotIn(SENSITIVE, json.dumps(gateway.snapshot()))


if __name__ == "__main__":
    unittest.main()
