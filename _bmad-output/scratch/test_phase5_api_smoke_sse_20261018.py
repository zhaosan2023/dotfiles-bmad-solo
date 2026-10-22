"""流式冒烟解析离线反例；不读取凭据、不连接网关、不写任务进度。"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

SOURCE = Path(__file__).with_name("phase5-api-smoke-20261018.py")
SPEC = importlib.util.spec_from_file_location("phase5_smoke_sse", SOURCE)
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


class Response(io.BytesIO):
    def __init__(self, payload, content_type="text/event-stream; charset=utf-8"):
        super().__init__(payload)
        self.content_type = content_type

    def getheader(self, name, default=""):
        return self.content_type if name == "Content-Type" else default


def chunk(delta=None, finish=None, identifier="offline-stream-1", model=None):
    return {
        "id": identifier,
        "object": "chat.completion.chunk",
        "model": smoke.MODEL if model is None else model,
        "choices": [{"index": 0, "delta": {} if delta is None else delta,
                     "finish_reason": finish}],
    }


def wire(*events, ending=True, newline=b"\n"):
    values = []
    for event in events:
        payload = json.dumps(event).encode("utf-8")
        values.append(b"data: " + payload + newline + newline)
    if ending:
        values.append(b"data: [DONE]" + newline + newline)
    return b"".join(values)


def valid_chunks():
    return [chunk({"role": "assistant", "content": "BMAD_API_"}),
            chunk({"content": "SMOKE_OK"}), chunk(finish="stop")]


class StreamingSmokeOfflineGuards(unittest.TestCase):
    def setUp(self):
        self.guards = contextlib.ExitStack()
        self.addCleanup(self.guards.close)
        self.network = self.guards.enter_context(patch.object(
            smoke.http.client, "HTTPConnection",
            side_effect=AssertionError("offline tests must not connect")))
        self.credentials = self.guards.enter_context(patch.object(
            smoke.private_config, "_read_credential",
            side_effect=AssertionError("offline tests must not read credentials")))
        self.guards.enter_context(patch.object(
            smoke.loop, "writer_lease",
            side_effect=AssertionError("offline tests must not acquire a real writer lease")))
        self.guards.enter_context(patch.object(
            smoke, "save_receipt",
            side_effect=AssertionError("offline tests must not save runtime receipts")))

    def parse(self, payload, content_type="text/event-stream; charset=utf-8"):
        record = {}
        valid = smoke.validate_sse_response(Response(payload, content_type), record)
        return valid, record

    def test_complete_split_text_requires_stop_and_done(self):
        valid, record = self.parse(wire(*valid_chunks()))
        self.assertTrue(valid)
        self.assertTrue(record["response_validated"])
        self.assertTrue(record["stream_stop_received"])
        self.assertTrue(record["stream_done_received"])
        self.assertEqual(record["sse_events"], 4)
        self.network.assert_not_called()
        self.credentials.assert_not_called()

    def test_crlf_comments_and_event_fields_are_supported(self):
        prefix = b": heartbeat\r\n\r\nevent: message\r\n"
        self.assertTrue(self.parse(prefix + wire(*valid_chunks(), newline=b"\r\n"))[0])

    def test_usage_only_chunk_after_stop_is_supported(self):
        usage = {"id": "offline-stream-1", "object": "chat.completion.chunk",
                 "model": smoke.MODEL, "choices": [], "usage": {"total_tokens": 7}}
        self.assertTrue(self.parse(wire(*valid_chunks(), usage))[0])

    def test_http_200_without_sse_content_type_is_not_success(self):
        with self.assertRaises(smoke.SupervisorError):
            self.parse(wire(*valid_chunks()), "application/json")

    def test_missing_done_blocks_even_after_complete_text(self):
        with self.assertRaises(smoke.SupervisorError):
            self.parse(wire(*valid_chunks(), ending=False))

    def test_unterminated_done_frame_blocks(self):
        payload = wire(*valid_chunks(), ending=False) + b"data: [DONE]"
        with self.assertRaises(smoke.SupervisorError):
            self.parse(payload)

    def test_done_without_stop_is_not_pass(self):
        valid, _ = self.parse(wire(chunk({"role": "assistant", "content": "BMAD_API_SMOKE_OK"})))
        self.assertFalse(valid)

    def test_wrong_text_or_missing_assistant_role_is_not_pass(self):
        for delta in ({"role": "assistant", "content": "other"},
                      {"content": "BMAD_API_SMOKE_OK"}):
            with self.subTest(delta=delta):
                self.assertFalse(self.parse(wire(chunk(delta), chunk(finish="stop")))[0])

    def test_wrong_model_and_changed_stream_id_block(self):
        for bad in (chunk({"content": "SMOKE_OK"}, model="wrong-model"),
                    chunk({"content": "SMOKE_OK"}, identifier="other-stream")):
            with self.subTest(bad=bad):
                with self.assertRaises(smoke.SupervisorError):
                    self.parse(wire(valid_chunks()[0], bad, chunk(finish="stop")))

    def test_tool_calls_and_function_calls_block(self):
        for delta in ({"role": "assistant", "tool_calls": [{"id": "offline-tool"}]},
                      {"role": "assistant", "function_call": {"name": "blocked"}}):
            with self.subTest(delta=delta):
                with self.assertRaises(smoke.SupervisorError):
                    self.parse(wire(chunk(delta)))

    def test_invalid_finish_role_and_index_block(self):
        bad_index = chunk({"role": "assistant"})
        bad_index["choices"][0]["index"] = True
        for bad in (chunk(finish="length"), chunk({"role": "user"}), bad_index):
            with self.subTest(bad=bad):
                with self.assertRaises(smoke.SupervisorError):
                    self.parse(wire(bad))

    def test_error_event_and_post_stop_content_block(self):
        with self.assertRaises(smoke.SupervisorError):
            self.parse(wire({"error": {"message": "offline-error"}}))
        with self.assertRaises(smoke.SupervisorError):
            self.parse(wire(*valid_chunks(), chunk({"content": "late-text"})))

    def test_invalid_json_duplicate_fields_and_utf8_block(self):
        for payload in (b"data: {\n\n", b'data: {"id":"a","id":"b"}\n\n',
                        b"data: \xff\n\n"):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    self.parse(payload)

    def test_byte_and_event_budgets_are_enforced(self):
        with patch.object(smoke, "MAX_RESPONSE_BYTES", 32):
            with self.assertRaises(smoke.SupervisorError):
                self.parse(wire(*valid_chunks()))
        with patch.object(smoke, "MAX_SSE_EVENTS", 1):
            with self.assertRaises(smoke.SupervisorError):
                self.parse(wire(*valid_chunks()))

    def previous_records(self):
        expected = {"plan_id": smoke.PLAN_ID, "workspace": str(smoke.ROOT),
                    "base_url": smoke.BASE_URL, "model": smoke.MODEL}
        budget = {**expected, "smoke_receipt": smoke.PREVIOUS_RECEIPT,
                  "reserved_request_slots": 1}
        receipt = {
            **expected, "operation": "direct-http-api-smoke",
            "budget_reservation": smoke.BUDGET, "status": "BLOCKED",
            "http_status": 502, "http_request_attempts": 1,
            "automatic_retries": 0, "tools_enabled": False,
            "cleanup_ok": True, "environment_restored": True,
            "pi_runtime_executed": False, "finished_at": "offline-finished",
        }
        return budget, receipt

    def previous_snapshots(self, budget, receipt):
        values = {smoke.BUDGET: budget, smoke.PREVIOUS_RECEIPT: receipt}

        def snapshot(root, relative, maximum):
            self.assertEqual(root, smoke.ROOT)
            self.assertEqual(maximum, 16384)
            return (json.dumps(values[relative]).encode(), smoke.ROOT / relative,
                    {"offline_identity": relative})

        return snapshot

    def test_previous_window_accepts_exactly_one_failed_clean_attempt(self):
        budget, receipt = self.previous_records()
        before = json.dumps([budget, receipt], sort_keys=True)
        with patch.object(smoke.inputs, "read_snapshot",
                          side_effect=self.previous_snapshots(budget, receipt)) as reader:
            identities = smoke.previous_window()
        self.assertEqual(reader.call_count, 2)
        self.assertEqual(set(identities), {
            smoke.ROOT / smoke.BUDGET, smoke.ROOT / smoke.PREVIOUS_RECEIPT})
        self.assertEqual(json.dumps([budget, receipt], sort_keys=True), before)
        self.network.assert_not_called()
        self.credentials.assert_not_called()

    def test_previous_window_rejects_changed_target_counts_or_cleanup(self):
        variants = [
            ("budget", "reserved_request_slots", 2),
            ("budget", "reserved_request_slots", True),
            ("budget", "model", "wrong-model"),
            ("budget", "smoke_receipt", "other-receipt.json"),
            ("receipt", "http_request_attempts", 2),
            ("receipt", "http_request_attempts", True),
            ("receipt", "automatic_retries", 1),
            ("receipt", "cleanup_ok", False),
            ("receipt", "environment_restored", False),
            ("receipt", "pi_runtime_executed", True),
            ("receipt", "tools_enabled", True),
            ("receipt", "http_status", 200),
            ("receipt", "finished_at", ""),
        ]
        for target, key, value in variants:
            with self.subTest(target=target, key=key, value=value):
                budget, receipt = self.previous_records()
                (budget if target == "budget" else receipt)[key] = value
                with patch.object(smoke.inputs, "read_snapshot",
                                  side_effect=self.previous_snapshots(budget, receipt)):
                    with self.assertRaises(smoke.SupervisorError):
                        smoke.previous_window()
        self.network.assert_not_called()
        self.credentials.assert_not_called()

    def test_previous_window_rejects_nonobject_records(self):
        for target in ("budget", "receipt"):
            with self.subTest(target=target):
                budget, receipt = self.previous_records()
                if target == "budget":
                    budget = []
                else:
                    receipt = []
                with patch.object(smoke.inputs, "read_snapshot",
                                  side_effect=self.previous_snapshots(budget, receipt)):
                    with self.assertRaises(smoke.SupervisorError):
                        smoke.previous_window()

    def test_existing_budget_blocks_before_request_or_receipt_write(self):
        for second_window in (False, True):
            with self.subTest(second_window=second_window):
                existing = MagicMock()
                existing.exists.return_value = True
                with patch.object(smoke, "bind", return_value=("plan", "adr")), \
                        patch.object(smoke.loop, "status", return_value={
                            "writer_active": False, "cleanup_ok": True}), \
                        patch.object(smoke.loop, "writer_lease", return_value=contextlib.nullcontext()), \
                        patch.object(smoke, "verification_lock", return_value=contextlib.nullcontext()), \
                        patch.object(smoke, "runtime_path", return_value=smoke.ROOT), \
                        patch.object(smoke, "contained_path", return_value=existing) as resolver, \
                        patch.object(smoke.Path, "cwd", return_value=smoke.ROOT), \
                        patch.object(smoke, "previous_window") as previous, \
                        patch.object(smoke, "smoke") as caller, \
                        patch.object(smoke, "save_receipt") as saver:
                    with self.assertRaisesRegex(smoke.SupervisorError, "预算已有预留"):
                        smoke.main(authorized_stream_window_2=second_window)
                    resolver.assert_called_once_with(
                        smoke.ROOT, smoke.STREAM_BUDGET if second_window else smoke.BUDGET)
                    previous.assert_not_called()
                    caller.assert_not_called()
                    saver.assert_not_called()
        self.network.assert_not_called()
        self.credentials.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
