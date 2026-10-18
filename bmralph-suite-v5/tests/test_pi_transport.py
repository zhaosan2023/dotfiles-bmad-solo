"""任务期转发反例：只连接测试回环端口，上游 HTTP 完全拦截。

不连接真实 8080 网关，不启动 Pi，不加载真实凭据。
真实本机 HTTP 用于核验请求读取、流式输出及线程清理。
"""
import http.client
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "scripts"))
import bmad_pi_transport as transport
from bmad_pi_budget import PiNetworkBudget

LOCAL_CONNECTION = http.client.HTTPConnection
TEST_CREDENTIAL = "synthetic-transport-test-not-a-real-secret"
MODEL = "unit-test-model"
STREAM = b'data: {"choices":[{"delta":{"content":"test"}}]}\n\ndata: [DONE]\n\n'


class ResponseInput:
    def __init__(self, body=STREAM, status=200, content_type="text/event-stream"):
        self.body = body
        self.status = status
        self.content_type = content_type
        self.read_sizes = []

    def getheader(self, name, default=""):
        return self.content_type if name == "Content-Type" else default

    def read1(self, size):
        self.read_sizes.append(size)
        chunk, self.body = self.body[:size], self.body[size:]
        return chunk


class InterceptedUpstream:
    def __init__(self, response):
        self.response = response
        self.calls = []
        self.sock = None
        self.closed = False

    def request(self, method, path, *, body, headers):
        self.calls.append({"method": method, "path": path,
                           "body": body, "headers": headers})

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


class PiTransportGuards(unittest.TestCase):
    def setUp(self):
        self.deadline = time.monotonic() + 10
        self.budget = PiNetworkBudget(
            maximum_requests=30, maximum_bytes=15_000_000,
            deadline=self.deadline)
        self.response = ResponseInput()
        self.upstream = InterceptedUpstream(self.response)
        self.factory = patch.object(
            transport.http.client, "HTTPConnection",
            return_value=self.upstream).start()
        self.addCleanup(patch.stopall)

    def gateway(self):
        return transport.PiTransport(
            budget=self.budget, credential=TEST_CREDENTIAL,
            model=MODEL, session_deadline=self.deadline)

    def body(self, **changes):
        value = {"model": MODEL, "stream": True,
                 "messages": [{"role": "user", "content": "test"}]}
        value.update(changes)
        return json.dumps(value).encode()

    def post(self, gateway, *, body=None, path=transport.REQUEST_PATH,
             authorization=None, extra_headers=None):
        client = LOCAL_CONNECTION("127.0.0.1", gateway._server.server_port, timeout=3)
        try:
            headers = {"Authorization": authorization if authorization is not None
                       else "Bearer " + gateway.token,
                       "Content-Type": "application/json"}
            if extra_headers:
                headers.update(extra_headers)
            client.request("POST", path,
                           body=self.body() if body is None else body,
                           headers=headers)
            response = client.getresponse()
            return response.status, response.read()
        finally:
            client.close()

    def test_streaming_body_is_forwarded_and_actual_request_reserved_before_send(self):
        raw = self.body()
        original_request = self.upstream.request

        def observed_request(*args, **kwargs):
            self.assertEqual(self.budget.requests, 1)
            self.assertEqual(self.budget.request_bytes, len(raw))
            original_request(*args, **kwargs)

        self.upstream.request = observed_request
        gateway = self.gateway()
        with gateway:
            status, body = self.post(gateway, body=raw)
            self.assertEqual(status, 200)
            self.assertEqual(body, STREAM)
        self.assertTrue(gateway.cleanup_ok)
        self.assertFalse(gateway.snapshot()["thread_active"])
        self.factory.assert_called_once()
        self.assertEqual(self.factory.call_args.args,
                         ("127.0.0.1", 8080))
        view = self.budget.snapshot()
        self.assertEqual(view["model_request_attempts"], 1)
        self.assertEqual(view["data_bytes"], len(raw) + len(STREAM))
        self.assertEqual(view["events"][0]["outcome"], "COMPLETE")
        self.assertTrue(self.upstream.closed)

    def test_real_credential_is_used_only_upstream_and_never_in_snapshot_or_downstream(self):
        gateway = self.gateway()
        with gateway:
            token = gateway.token
            status, body = self.post(gateway)
        self.assertEqual(status, 200)
        self.assertEqual(self.upstream.calls[0]["headers"]["Authorization"],
                         "Bearer " + TEST_CREDENTIAL)
        public = json.dumps(gateway.snapshot()) + body.decode()
        self.assertNotIn(TEST_CREDENTIAL, public)
        self.assertNotIn(token, public)
        self.assertEqual(gateway._credential, "")
        self.assertEqual(gateway.token, "")

    def test_wrong_internal_token_blocks_before_upstream_request(self):
        gateway = self.gateway()
        with gateway:
            status, _ = self.post(gateway, authorization="Bearer wrong")
        self.assertEqual(status, 502)
        self.factory.assert_not_called()
        self.assertEqual(self.budget.requests, 0)
        self.assertEqual(gateway.snapshot()["status"], "BLOCKED")

    def test_wrong_path_blocks_before_upstream_request(self):
        gateway = self.gateway()
        with gateway:
            status, _ = self.post(gateway, path="/v1/other")
        self.assertEqual(status, 502)
        self.factory.assert_not_called()
        self.assertEqual(self.budget.requests, 0)

    def test_nonstreaming_request_blocks_before_upstream_request(self):
        gateway = self.gateway()
        with gateway:
            status, _ = self.post(gateway, body=self.body(stream=False))
        self.assertEqual(status, 502)
        self.factory.assert_not_called()

    def test_wrong_model_blocks_before_upstream_request(self):
        gateway = self.gateway()
        with gateway:
            status, _ = self.post(gateway, body=self.body(model="other"))
        self.assertEqual(status, 502)
        self.factory.assert_not_called()

    def test_transfer_encoding_is_rejected_before_upstream_request(self):
        gateway = self.gateway()
        with gateway:
            status, _ = self.post(gateway,
                                  extra_headers={"Transfer-Encoding": "chunked"})
        self.assertEqual(status, 502)
        self.factory.assert_not_called()

    def test_upstream_http_error_counts_attempt_and_blocks_further_requests(self):
        self.response.status = 502
        gateway = self.gateway()
        with gateway:
            self.assertEqual(self.post(gateway)[0], 502)
            self.assertEqual(self.post(gateway)[0], 502)
        self.assertEqual(len(self.upstream.calls), 1)
        view = self.budget.snapshot()
        self.assertEqual(view["model_request_attempts"], 1)
        self.assertEqual(view["events"][0]["http_status"], 502)
        self.assertEqual(view["events"][0]["outcome"], "HTTP_ERROR")
        self.assertEqual(gateway.snapshot()["status"], "BLOCKED")

    def test_missing_done_is_failure_not_successful_stream_completion(self):
        self.response.body = b'data: {"choices":[]}\n\n'
        gateway = self.gateway()
        with gateway:
            self.post(gateway)
        self.assertEqual(gateway.snapshot()["status"], "BLOCKED")
        self.assertEqual(self.budget.snapshot()["events"][0]["outcome"],
                         "NETWORK_ERROR")
        self.assertTrue(gateway.cleanup_ok)

    def test_non_sse_upstream_is_failure_even_with_http_200(self):
        self.response.content_type = "application/json"
        gateway = self.gateway()
        with gateway:
            self.assertEqual(self.post(gateway)[0], 502)
        self.assertEqual(gateway.snapshot()["status"], "BLOCKED")
        self.assertEqual(self.budget.snapshot()["events"][0]["http_status"], 200)

    def test_response_reads_never_exceed_remaining_decimal_byte_budget(self):
        self.budget = PiNetworkBudget(maximum_requests=30, maximum_bytes=256,
                                      deadline=self.deadline)
        self.response.body = b"x" * 1000
        raw = self.body()
        remaining = 256 - len(raw)
        self.assertGreater(remaining, 0)
        gateway = self.gateway()
        with gateway:
            self.post(gateway, body=raw)
        self.assertEqual(self.response.read_sizes, [remaining])
        self.assertEqual(self.budget.snapshot()["data_bytes"], 256)
        self.assertEqual(gateway.snapshot()["status"], "BLOCKED")
        self.assertTrue(gateway.cleanup_ok)

    def test_new_transport_session_reuses_request_budget_instead_of_resetting_it(self):
        self.budget = PiNetworkBudget(maximum_requests=1, maximum_bytes=15_000_000,
                                      deadline=self.deadline)
        first = self.gateway()
        with first:
            self.assertEqual(self.post(first)[0], 200)
        second = self.gateway()
        with second:
            self.assertEqual(self.post(second)[0], 502)
        self.assertEqual(len(self.upstream.calls), 1)
        self.assertEqual(self.budget.requests, 1)
        self.assertEqual(self.budget.snapshot()["status"], "BLOCKED")
        self.assertTrue(first.cleanup_ok)
        self.assertTrue(second.cleanup_ok)


if __name__ == "__main__":
    unittest.main()
