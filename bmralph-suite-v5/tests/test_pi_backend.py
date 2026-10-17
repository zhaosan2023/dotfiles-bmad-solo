"""Pi 薄驱动协议反例；不启动已安装 Pi、不联网、不使用真实凭据。

协议记录、安装元数据和调用回执均为显式单元测试输入，不是 Pi 运行证据。
进程组反例另用隔离 Python 子进程验证既有监督器，不伪装成 Pi。
"""
import copy
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
import uuid
from unittest.mock import patch

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "scripts"))
import bmad_agent_backend as agent
import bmad_loop as loop
import bmad_supervisor as supervisor

CREDENTIAL = "BMAD_PI_TEST_API_KEY"
TEST_VALUE = "unit-test-only-not-a-real-api-key"


class PiBackendGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sandbox-pi-unit-", dir=SUITE.parent / "tests")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = {
            "schema_version": 1, "backend": "pi-agent", "protocol": agent.PROTOCOL,
            "runtime_kind": "pi-agent", "source": agent.PI_SOURCE, "version": agent.PI_VERSION,
            "driver_file": "backend.py", "credential_environment": CREDENTIAL,
            "authorized": True, "authorization": "仅单元测试；禁止真实 Pi 启动",
            "new_session": True, "headless": True, "api_timeout_seconds": 1,
            "pi": {"executable": "/usr/local/bin/pi", "provider": "anthropic",
                   "model": "claude-test-model", "tools": ["read", "edit", "write"],
                   "no_progress_rounds": 3},
        }
        # 仅模拟绑定路径；本文件不会作为适配器或 Pi 可执行程序运行。
        (self.root / "backend.py").write_text("# unit-test binding marker; never executed\n")
        self.startup = {
            "state_projection": {"plan_id": "PI-UNIT-01", "view": "T1 [READY]\nT2 [PENDING]"},
            "task": {"task_id": "T1", "verification": {"environment_file": "environment.json"}},
            "observed_host_bytes": None,
        }
        self.expected = {"session_id": "outer-session", "plan_id": "PI-UNIT-01", "task_id": "T1"}
        # 单元测试一律拦截进程启动，即使实现错误也不能调用真实 Pi。
        self.addCleanup(patch.stopall)
        patch.object(supervisor.subprocess, "Popen", side_effect=AssertionError("unit test must not spawn Pi")).start()
        patch.object(agent.os, "execve", side_effect=AssertionError("unit test must not exec Pi")).start()

    def active(self, *, threshold=3, status="EXECUTING"):
        self.lease = loop.writer_lease(self.root)
        self.lease.__enter__()
        self.addCleanup(self.lease.__exit__, None, None, None)
        (self.root / ".bmad-control/loop-current.json").write_text(json.dumps({
            "status": status, "no_progress_rounds": threshold,
        }))

    def stream(self, *, identifier=None, text="<promise>DONE</promise>"):
        return [
            {"type": "session", "version": 3, "id": identifier or str(uuid.uuid4()),
             "cwd": str(self.root)},
            {"type": "agent_start"},
            {"type": "message_end", "message": {"role": "assistant", "stopReason": "stop",
                                                 "content": [{"type": "text", "text": text}]}},
            {"type": "agent_end", "messages": [], "willRetry": False},
            {"type": "agent_settled", "aborted": False},
        ]

    def parse(self, records):
        path = self.root / "protocol-unit-input.jsonl"
        path.write_bytes(b"".join(json.dumps(record, ensure_ascii=False).encode() + b"\n" for record in records))
        return agent.pi_result_from_log(path, self.expected, self.root)

    def invoke(self, *, returncode=0, timed_out=False, cancelled=False, cleanup_ok=True,
               records=None, reason="", feedback=None, maximum_bytes=16384):
        captured = []

        def unit_process_receipt(spec):
            captured.append(spec)
            request = self.root / spec.argv[spec.argv.index("--request-file") + 1]
            self.last_envelope = json.loads(request.read_bytes())
            log = self.root / ".bmad-runtime/unit-process-records.jsonl"
            values = self.stream() if records is None else records
            log.write_bytes(b"".join(json.dumps(value).encode() + b"\n" for value in values))
            return {
                "reason": reason, "log_path": log.relative_to(self.root).as_posix(),
                "receipt_path": ".bmad-runtime/unit-process-receipt.json", "returncode": returncode,
                "timed_out": timed_out, "cancelled": cancelled, "cleanup_ok": cleanup_ok,
                "process_status": "PASS" if returncode == 0 and not reason and not timed_out
                                  and not cancelled and cleanup_ok else "BLOCKED",
            }

        with patch.object(agent, "__file__", str(self.root / "backend.py")), \
                patch.dict(os.environ, {CREDENTIAL: TEST_VALUE}, clear=True), \
                patch.object(agent.environment, "check", return_value={
                    "environment": {"python": {"path": sys.executable}}}), \
                patch.object(agent, "run", side_effect=unit_process_receipt) as runner:
            record = agent.invoke(
                workspace=self.root, config=self.config,
                assembled={"payload": json.dumps(self.startup)}, runtime_directory=".bmad-runtime",
                deadline=time.monotonic() + 5, cancel_requested=lambda: False,
                feedback=feedback, maximum_bytes=maximum_bytes)
        self.assertEqual(runner.call_count, 1)
        self.assertNotIn(TEST_VALUE, json.dumps(record) + json.dumps(self.last_envelope) + repr(captured))
        return record, captured[0]

    def test_argument_allowlist_uses_one_shot_ephemeral_json_and_closed_option_parsing(self):
        request = self.root / "request with spaces.json"
        argv = agent.pi_arguments(self.config, request)
        self.assertEqual(argv[:6], ("/usr/local/bin/pi", "--print", "--mode", "json", "--no-session", "--no-extensions"))
        self.assertEqual(argv[-2:], ("--", "@" + str(request)))
        for flag in ("--no-mcp", "--no-skills", "--no-prompt-templates", "--no-themes",
                     "--no-context-files", "--no-approve", "--offline"):
            self.assertIn(flag, argv)
        self.assertEqual(argv[argv.index("--provider") + 1], "anthropic")
        self.assertEqual(argv[argv.index("--model") + 1], "claude-test-model")
        self.assertEqual(argv[argv.index("--tools") + 1], "read,edit,write")
        for flag in ("--continue", "--resume", "--session", "--session-id", "--fork", "--api-key"):
            self.assertNotIn(flag, argv)
        self.assertNotIn(TEST_VALUE, repr(argv))

    def test_argument_injection_extensions_and_relative_request_fail_closed(self):
        variants = [
            ("provider", "--resume"), ("model", "@history.json"), ("model", "model with spaces"),
            ("model", "model\x00"), ("tools", ["read", "mcp__remote"]),
            ("tools", ["+bash"]), ("tools", ["read", "read"]), ("tools", []),
        ]
        for key, value in variants:
            with self.subTest(key=key, value=value):
                config = copy.deepcopy(self.config)
                config["pi"][key] = value
                with self.assertRaises(supervisor.SupervisorError):
                    agent.pi_arguments(config, self.root / "request.json")
        with self.assertRaises(supervisor.SupervisorError):
            agent.pi_arguments(self.config, "relative.json")
        config = copy.deepcopy(self.config)
        config["pi"]["extra_args"] = ["--extension", "third-party.js"]
        with self.assertRaises(supervisor.SupervisorError):
            agent.validate_pi_config(config)

    def test_source_version_authorization_and_runtime_cannot_be_relaxed(self):
        for key, value in (("source", "https://example.invalid/fork"), ("version", "latest"),
                           ("authorized", False), ("authorization", ""), ("new_session", False),
                           ("headless", False), ("runtime_kind", "isolated-fixture"),
                           ("backend", "roo-cli")):
            with self.subTest(key=key):
                config = copy.deepcopy(self.config)
                config[key] = value
                with self.assertRaises(supervisor.SupervisorError):
                    agent.validate_pi_config(config)

    def test_three_round_binding_rejects_other_thresholds_and_booleans(self):
        for value in (1, 2, 4, True, "3"):
            with self.subTest(value=value):
                config = copy.deepcopy(self.config)
                config["pi"]["no_progress_rounds"] = value
                with self.assertRaisesRegex(supervisor.SupervisorError, "3 轮"):
                    agent.validate_pi_config(config)

    def test_unapproved_runtime_blocks_invoke_before_request_or_launch(self):
        self.config["authorized"] = False
        with patch.object(agent, "run") as runner:
            with self.assertRaisesRegex(supervisor.SupervisorError, "授权"):
                agent.invoke(workspace=self.root, config=self.config,
                             assembled={"payload": json.dumps(self.startup)},
                             runtime_directory=".bmad-runtime", deadline=time.monotonic() + 2,
                             cancel_requested=lambda: False)
        runner.assert_not_called()
        self.assertFalse((self.root / ".bmad-runtime").exists())

    def test_missing_credentials_blocks_load_before_driver_read_or_launch(self):
        (self.root / "config.json").write_text(json.dumps(self.config))
        with patch.dict(os.environ, {}, clear=True), \
                patch.object(agent, "__file__", str(self.root / "backend.py")):
            with self.assertRaisesRegex(supervisor.SupervisorError, "凭据缺失"):
                agent.load(self.root, "config.json", "pi-agent")
        self.assertFalse((self.root / ".bmad-runtime").exists())

    def test_real_pi_category_cannot_be_loaded_as_isolated_fixture(self):
        config = copy.deepcopy(self.config)
        config.pop("pi")
        config["runtime_kind"] = "isolated-fixture"
        (self.root / "config.json").write_text(json.dumps(config))
        with self.assertRaisesRegex(supervisor.SupervisorError, "不得声明为隔离夹具"):
            agent.load(self.root, "config.json", "pi-agent")

    def test_load_accepts_only_self_driver_and_preserves_pi_runtime_kind(self):
        (self.root / "config.json").write_text(json.dumps(self.config))
        with patch.dict(os.environ, {CREDENTIAL: TEST_VALUE}, clear=True), \
                patch.object(agent, "__file__", str(self.root / "backend.py")):
            loaded, bindings = agent.load(self.root, "config.json", "pi-agent")
        self.assertEqual(loaded["runtime_kind"], "pi-agent")
        self.assertEqual(set(bindings), {self.root / "config.json", self.root / "backend.py"})
        with patch.dict(os.environ, {CREDENTIAL: TEST_VALUE}, clear=True):
            with self.assertRaisesRegex(supervisor.SupervisorError, "必须绑定本模块"):
                agent.load(self.root, "config.json", "pi-agent")

    def test_existing_writer_lease_is_required_and_owner_is_verified(self):
        self.active()
        agent.require_pi_writer(self.root, os.getpid())
        with self.assertRaisesRegex(supervisor.SupervisorError, "未持有"):
            agent.require_pi_writer(self.root, os.getpid() + 100000)
        self.lease.__exit__(None, None, None)
        self._cleanups.pop()
        with self.assertRaisesRegex(supervisor.SupervisorError, "未持有"):
            agent.require_pi_writer(self.root, os.getpid())

    def test_outer_threshold_and_execution_state_must_match(self):
        self.active()
        path = self.root / ".bmad-control/loop-current.json"
        for state in ({"status": "EXECUTING", "no_progress_rounds": 2},
                      {"status": "SUSPENDED", "no_progress_rounds": 3},
                      {"status": "EXECUTING", "no_progress_rounds": True}):
            with self.subTest(state=state):
                path.write_text(json.dumps(state))
                with self.assertRaisesRegex(supervisor.SupervisorError, "3 轮"):
                    agent.require_pi_writer(self.root, os.getpid())

    def test_missing_credentials_blocks_invoke_before_request_or_process(self):
        self.active()
        with patch.dict(os.environ, {}, clear=True), patch.object(agent, "run") as runner:
            with self.assertRaisesRegex(supervisor.SupervisorError, "凭据缺失"):
                agent.invoke(workspace=self.root, config=self.config,
                             assembled={"payload": json.dumps(self.startup)},
                             runtime_directory=".bmad-runtime", deadline=time.monotonic() + 2,
                             cancel_requested=lambda: False)
        runner.assert_not_called()
        self.assertFalse((self.root / ".bmad-runtime").exists())

    def test_complete_protocol_is_only_call_evidence_not_business_completion(self):
        data = self.parse(self.stream(text="Nothing was changed"))
        self.assertEqual(data["status"], "OK")
        self.assertEqual(data["task_id"], "T1")
        self.assertNotIn("verdict_file", data)
        self.assertNotIn("COMPLETED", json.dumps(data))

    def test_completion_promise_and_exit_without_protocol_are_rejected(self):
        path = self.root / "promise.txt"
        for payload in (b"<promise>DONE</promise>\n", b"", b"BMAD_AGENT_RESULT {}\n"):
            with self.subTest(payload=payload):
                path.write_bytes(payload)
                with self.assertRaises(supervisor.SupervisorError):
                    agent.pi_result_from_log(path, self.expected, self.root)

    def test_wrong_workspace_session_id_or_duplicate_session_blocks(self):
        for key, value in (("cwd", str(self.root.parent)), ("id", "old-session"), ("version", True)):
            with self.subTest(key=key):
                records = self.stream()
                records[0][key] = value
                with self.assertRaises(supervisor.SupervisorError):
                    self.parse(records)
        records = self.stream()
        records.insert(2, copy.deepcopy(records[0]))
        with self.assertRaisesRegex(supervisor.SupervisorError, "切换或恢复"):
            self.parse(records)

    def test_model_error_abort_missing_settled_or_late_activity_blocks(self):
        variants = []
        records = self.stream()
        records[2]["message"]["stopReason"] = "error"
        variants.append(records)
        records = self.stream()
        records[-1]["aborted"] = True
        variants.append(records)
        variants.append(self.stream()[:-1])
        variants.append(self.stream() + [{"type": "agent_start"}])
        variants.append([self.stream()[0], {"type": "agent_settled", "aborted": False}])
        for records in variants:
            with self.subTest(records=records):
                with self.assertRaises(supervisor.SupervisorError):
                    self.parse(records)

    def test_retry_failure_and_provider_error_cannot_be_overridden(self):
        for failure in ({"type": "auto_retry_end", "success": False},
                        {"type": "extension_error"},
                        {"type": "message_update", "assistantMessageEvent": {"type": "error"}}):
            with self.subTest(failure=failure):
                records = self.stream()
                records.insert(2, failure)
                with self.assertRaisesRegex(supervisor.SupervisorError, "运行失败"):
                    self.parse(records)

    def test_jsonl_duplicate_keys_truncation_and_record_budget_fail_closed(self):
        path = self.root / "invalid.jsonl"
        values = (b'{"type":"session","type":"agent_settled"}\n', b'{"type":"session"}',
                  b"{" + b"x" * agent.PI_RECORD_BYTES + b"}\n")
        for value in values:
            with self.subTest(size=len(value)):
                path.write_bytes(value)
                with self.assertRaises(supervisor.SupervisorError):
                    agent.pi_result_from_log(path, self.expected, self.root)

    def test_unicode_separators_inside_text_do_not_break_jsonl(self):
        data = self.parse(self.stream(text="one\u2028two\u2029three"))
        self.assertEqual(data["status"], "OK")

    def test_nonzero_exit_cannot_be_masked_by_valid_protocol_or_promise(self):
        self.active()
        record, spec = self.invoke(returncode=7)
        self.assertEqual(record["status"], "BLOCKED")
        self.assertEqual(record["returncode"], 7)
        self.assertEqual(spec.operation, "agent-call")
        self.assertEqual(spec.tier, "verify")
        self.assertIn("--pi-exec", spec.argv)
        self.assertNotIn("--api-key", spec.argv)

    def test_timeout_cancellation_and_unknown_cleanup_override_protocol_ok(self):
        self.active()
        for options, category in (({"timed_out": True}, "TIMEOUT"),
                                  ({"cancelled": True}, "CANCELLED"),
                                  ({"cleanup_ok": False}, "CLEANUP_UNKNOWN")):
            with self.subTest(category=category):
                record, _ = self.invoke(**options)
                self.assertEqual(record["status"], "BLOCKED")
                self.assertEqual(record["category"], category)

    def test_each_invocation_has_distinct_input_and_only_current_feedback(self):
        self.active()
        first, first_spec = self.invoke(feedback={"status": "BLOCKED", "process_receipt": "previous.json"})
        second, second_spec = self.invoke(feedback=None)
        self.assertEqual(first["status"], "PASS")
        self.assertEqual(second["status"], "PASS")
        self.assertNotEqual(first["session_id"], second["session_id"])
        self.assertNotEqual(first_spec.argv, second_spec.argv)
        requests = sorted((self.root / ".bmad-runtime").glob("agent-input-*.json"))
        self.assertEqual(len(requests), 2)
        envelopes = [json.loads(path.read_bytes()) for path in requests]
        self.assertEqual(sum(item["recent_verification"] is None for item in envelopes), 1)
        self.assertTrue(all(set(item) == {"schema_version", "protocol", "session_id", "plan_id",
                                         "task_id", "startup", "recent_verification"} for item in envelopes))
        self.assertNotIn("history", json.dumps(envelopes))
        self.assertNotIn("verdict_file", second)

    def test_state_card_and_input_budget_block_before_launch(self):
        self.active()
        for long_view, budget in ((True, 16384), (False, 256)):
            with self.subTest(long_view=long_view):
                self.startup["state_projection"]["view"] = "\n".join(["task"] * 81) if long_view else "T1 [READY]"
                with patch.dict(os.environ, {CREDENTIAL: TEST_VALUE}, clear=True), \
                        patch.object(agent, "__file__", str(self.root / "backend.py")), \
                        patch.object(agent, "run") as runner:
                    with self.assertRaises(supervisor.SupervisorError):
                        agent.invoke(workspace=self.root, config=self.config,
                                     assembled={"payload": json.dumps(self.startup)},
                                     runtime_directory=".bmad-runtime", deadline=time.monotonic() + 2,
                                     cancel_requested=lambda: False, maximum_bytes=budget)
                runner.assert_not_called()
        self.assertFalse((self.root / ".bmad-runtime").exists())

    def test_legacy_timeout_is_not_claimed_as_model_request_timeout(self):
        self.active()
        record, _ = self.invoke()
        dimensions = record["timeout_dimensions"]
        self.assertIsNone(dimensions["model_request_timeout_seconds"])
        self.assertEqual(dimensions["model_request_timeout_coverage"], "UNKNOWN")
        self.assertLessEqual(dimensions["agent_session_timeout_seconds"], 30)

    def test_request_tool_session_and_batch_caps_are_not_conflated(self):
        with patch.object(agent.time, "monotonic", return_value=100.0):
            dimensions = agent.timeout_dimensions(self.config, 100.5)
        self.assertIsNone(dimensions["model_request_timeout_seconds"])
        self.assertEqual(dimensions["model_request_timeout_coverage"], "UNKNOWN")
        self.assertEqual(dimensions["agent_session_timeout_seconds"], 1)
        self.assertEqual(dimensions["agent_session_deadline"], 100.5)
        self.assertEqual(dimensions["batch_deadline"], 100.5)
        self.assertEqual(dimensions["tool_timeout_caps_seconds"],
                         {"probe": 15, "verify": 30, "build": 600})
        for limit in (True, 0, 30.01, float("nan"), float("inf")):
            with self.subTest(limit=limit):
                with self.assertRaises(supervisor.SupervisorError):
                    agent.timeout_dimensions(dict(self.config, api_timeout_seconds=limit), 101)

    def test_exec_interception_preserves_process_group_and_excludes_inherited_config(self):
        self.active()
        runtime = self.root / ".bmad-runtime"
        runtime.mkdir()
        request = runtime / "request.json"
        request.write_text(json.dumps({"protocol": agent.PROTOCOL}))
        package = self.root / "metadata-only-unit-input"
        package.mkdir()
        (package / "package.json").write_text(json.dumps({
            "name": agent.PI_PACKAGE, "version": agent.PI_VERSION,
            "repository": {"url": "git+" + agent.PI_SOURCE + ".git"},
        }))
        executable = package / "dist/bundle/cli.js"
        original_resolve = Path.resolve

        def unit_resolve(path, *args, **kwargs):
            return executable if str(path) == "/usr/local/bin/pi" else original_resolve(path, *args, **kwargs)

        with patch.object(Path, "cwd", return_value=self.root), \
                patch.object(Path, "resolve", unit_resolve), \
                patch.object(agent.os, "getppid", return_value=os.getpid()), \
                patch.dict(os.environ, {CREDENTIAL: TEST_VALUE, "PI_CODING_AGENT_DIR": "/untrusted",
                                       "NODE_OPTIONS": "--require malicious.js", "OTHER_API_KEY": TEST_VALUE}, clear=True), \
                patch.object(agent.os, "dup2") as redirect, \
                patch.object(agent.os, "execve", side_effect=RuntimeError("intercepted; no Pi launched")) as execute:
            with self.assertRaisesRegex(RuntimeError, "intercepted"):
                agent._pi_exec(self.config, request.relative_to(self.root).as_posix(), os.getpid())
        execute.assert_called_once()
        path, argv, env = execute.call_args.args
        self.assertEqual(path, "/usr/local/bin/pi")
        self.assertEqual(argv[-1], "@" + str(request))
        self.assertEqual(env[CREDENTIAL], TEST_VALUE)
        self.assertNotIn("NODE_OPTIONS", env)
        self.assertNotIn("OTHER_API_KEY", env)
        self.assertNotEqual(env["PI_CODING_AGENT_DIR"], "/untrusted")
        self.assertTrue(Path(env["PI_CODING_AGENT_DIR"]).is_relative_to(runtime))
        self.assertEqual(env["PI_TELEMETRY"], "0")
        redirect.assert_called_once()
        self.assertNotIn(TEST_VALUE, repr(argv) + request.read_text())

    def test_frozen_loop_still_rejects_real_pi_without_activation(self):
        spec = loop.LoopSpec(workspace=self.root, plan_file="plan.md", request_file="request.json",
                             backend="pi-agent", maximum_rounds=3, timeout_seconds=3,
                             no_progress_rounds=3, backend_config="config.json")
        with self.assertRaisesRegex(supervisor.SupervisorError, "后端未覆盖"):
            spec.validate()
        # 此断言保存真实边界：本轮没有解冻或绕过外层真实运行门禁。


def isolated_python_group_fixture(root, scenario):
    """只启动 Python，不模拟 Pi；收养及回收孤儿仅属于测试设施。"""
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "isolated subreaper unavailable")
    child_code = (
        "import os,pathlib,signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); "
        "pathlib.Path('child.pid').write_text(str(os.getpid())); time.sleep(10)"
    )
    leader_code = (
        "import os,pathlib,signal,subprocess,sys,time\n"
        f"subprocess.Popen([sys.executable,'-B','-c',{child_code!r}])\n"
        "end=time.monotonic()+2\n"
        "while not pathlib.Path('child.pid').exists():\n"
        "    if time.monotonic()>end: raise SystemExit(8)\n"
        "    time.sleep(0.01)\n"
        "pathlib.Path('kept.txt').write_text('unfinished change')\n"
    )
    if scenario == "cancel":
        leader_code += "os.kill(os.getppid(),signal.SIGTERM)\n"
    leader_code += "time.sleep(10)\n"
    original_stop = supervisor.stop_group
    reaped = []
    reaper_errors = []
    reaper = None
    group = None

    def reap(pid):
        end = time.monotonic() + 3
        while time.monotonic() < end:
            try:
                reaped.append(os.waitpid(pid, 0))
                return
            except ChildProcessError:
                time.sleep(0.01)
        reaper_errors.append("orphan was not reaped")

    def stop(process):
        nonlocal reaper, group
        group = process.pid
        pid = int((root / "child.pid").read_text())
        reaper = threading.Thread(target=reap, args=(pid,))
        reaper.start()
        return original_stop(process, grace_seconds=0.3)

    try:
        with patch.object(supervisor, "stop_group", side_effect=stop):
            receipt = supervisor.run(supervisor.RunSpec(
                operation="agent-call", argv=(sys.executable, "-B", "-c", leader_code),
                workspace=root, runtime_directory=".bmad-runtime", tier="verify",
                target="isolated Python group cleanup; not Pi", deadline=time.monotonic() + 0.7))
        if reaper is not None:
            reaper.join(timeout=3)
        if reaper_errors or len(reaped) != 1 or reaper is None or reaper.is_alive():
            raise RuntimeError("missing actual isolated child reaping evidence")
        print(json.dumps({
            "receipt": receipt, "wait_pid": reaped[0][0],
            "child_pid": int((root / "child.pid").read_text()),
            "child_exit": os.waitstatus_to_exitcode(reaped[0][1]),
            "group_gone": group is not None and not supervisor.group_exists(group),
            "kept": (root / "kept.txt").read_text(),
        }), flush=True)
    finally:
        if group is not None and supervisor.group_exists(group):
            os.killpg(group, signal.SIGKILL)
        pid_file = root / "child.pid"
        if pid_file.exists() and not reaped:
            pid = int(pid_file.read_text())
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            if reaper is not None:
                reaper.join(timeout=3)
            if not reaped:
                os.waitpid(pid, 0)


class PiSupervisorDelegationGuards(unittest.TestCase):
    def test_frozen_supervisor_fuses_after_exactly_three_unchanged_failures(self):
        # 复用既有本地验证夹具；不启动 Pi、不修改冻结原语或既有测试。
        from test_loop_guards import LoopGuards

        guards = LoopGuards("test_no_progress_auto_stops_nonzero_and_preserves_every_pending_item")
        self.addCleanup(guards.doCleanups)
        guards.setUp()
        plan_before = (guards.root / "plan.md").read_bytes()
        changes_before = (guards.root / "unfinished.py").read_bytes()
        record = loop.start(guards.spec(no_progress_rounds=3, maximum_rounds=5))
        self.assertEqual(record["status"], "BLOCKED")
        self.assertIn("持续无进展", record["reason"])
        self.assertEqual(record["rounds"], 3)
        self.assertEqual(record["no_progress_count"], 3)
        self.assertEqual(record["agent_calls"], 0)
        self.assertTrue(record["cleanup_ok"])
        self.assertFalse(record["task_progress_saved"])
        self.assertEqual((guards.root / "plan.md").read_bytes(), plan_before)
        self.assertEqual((guards.root / "unfinished.py").read_bytes(), changes_before)
        self.assertEqual(len(list((guards.root / ".bmad-runtime").glob("run-*.verdict.json"))), 3)
        saved = json.loads((guards.root / record["final_receipt"]).read_bytes())
        self.assertEqual(saved, record)
        self.assertFalse(loop.writer_active(guards.root))

    def batch_guards(self):
        # 只复用明确的 Python 隔离驱动；不绕过冻结的真实 Pi 门禁。
        from test_batch_guards import BatchGuards

        guards = BatchGuards("test_budget_exhaustion_stops_new_calls_and_preserves_changes")
        self.addCleanup(guards.doCleanups)
        guards.setUp()
        return guards

    def batch_spec(self, guards, **changes):
        options = dict(workspace=guards.root, plan_file="plan.md", request_file="T1-request.json",
                       backend="headless", backend_config="backend.json", batch_file="batch.json",
                       maximum_rounds=5, maximum_calls=5, timeout_seconds=12,
                       no_progress_rounds=3, save_progress=True)
        options.update(changes)
        return loop.LoopSpec(**options)

    def test_three_unchanged_failures_prohibit_fourth_call_and_dependency_progress(self):
        from test_batch_guards import CREDENTIAL as fixture_credential

        guards = self.batch_guards()
        guards.driver("pass\n")
        before = (guards.root / "plan.md").read_bytes()
        with patch.dict(os.environ, {fixture_credential: "isolated-fixture-only"}):
            record = loop.start(self.batch_spec(guards))
        self.assertEqual(record["status"], "BLOCKED")
        self.assertIn("持续无进展", record["reason"])
        self.assertEqual(record["rounds"], 3)
        self.assertEqual(record["agent_calls"], 3)
        self.assertEqual(record["no_progress_count"], 3)
        self.assertEqual([call["task_id"] for call in guards.calls()], ["T1"] * 3)
        self.assertEqual(len({call["session_id"] for call in guards.calls()}), 3)
        self.assertTrue(all(call["feedback"]["returncode"] != 0
                            for call in guards.calls()[1:]))
        self.assertEqual(record["completed_tasks"], [])
        self.assertTrue(record["cleanup_ok"])
        self.assertEqual((guards.root / "plan.md").read_bytes(), before)
        self.assertEqual((guards.root / "T2.txt").read_text(), "KEEP\n")
        self.assertFalse(loop.writer_active(guards.root))

    def test_unknown_cleanup_prohibits_next_call_verification_and_restart(self):
        from test_batch_guards import CREDENTIAL as fixture_credential

        guards = self.batch_guards()
        before = (guards.root / "plan.md").read_bytes()
        failure = {"operation": "agent-call", "status": "BLOCKED",
                   "reason": "显式清理未知故障注入，不是 Pi 实测",
                   "cleanup_ok": False, "cancelled": False, "timed_out": False,
                   "returncode": 0, "category": "CLEANUP_UNKNOWN"}
        with patch.dict(os.environ, {fixture_credential: "isolated-fixture-only"}), \
                patch.object(agent, "invoke", return_value=failure) as invoke, \
                patch.object(loop.execution, "unit_test") as verify:
            record = loop.start(self.batch_spec(guards))
            self.assertEqual(record["status"], "BLOCKED")
            self.assertFalse(record["cleanup_ok"])
            self.assertEqual(record["agent_calls"], 1)
            self.assertEqual(record["completed_tasks"], [])
            self.assertIsNone(record["last_verdict"])
            invoke.assert_called_once()
            verify.assert_not_called()
            with self.assertRaisesRegex(supervisor.SupervisorError, "清理"):
                loop.start(self.batch_spec(guards))
            invoke.assert_called_once()
            verify.assert_not_called()
        self.assertEqual((guards.root / "plan.md").read_bytes(), before)
        self.assertFalse(loop.writer_active(guards.root))
        self.assertEqual(guards.calls(), [])

    def fixture(self, scenario):
        with tempfile.TemporaryDirectory(prefix="sandbox-pi-group-", dir=SUITE.parent / "tests") as temporary:
            root = Path(temporary)
            result = subprocess.run(
                [sys.executable, "-B", str(Path(__file__).resolve()), "--isolated-python-group", str(root), scenario],
                cwd=root, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=8)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data["child_pid"], data["wait_pid"])
            self.assertEqual(data["child_exit"], -signal.SIGKILL)
            self.assertTrue(data["group_gone"])
            self.assertTrue(data["receipt"]["cleanup_ok"])
            self.assertEqual(data["receipt"]["process_status"], "BLOCKED")
            self.assertEqual(data["kept"], "unfinished change")
            saved = json.loads((root / data["receipt"]["receipt_path"]).read_bytes())
            self.assertEqual(saved, data["receipt"])
            return data["receipt"]

    def test_agent_call_timeout_cleans_same_group_and_preserves_changes(self):
        receipt = self.fixture("timeout")
        self.assertTrue(receipt["timed_out"])
        self.assertFalse(receipt["cancelled"])

    def test_agent_call_interrupt_cleans_same_group_and_preserves_changes(self):
        receipt = self.fixture("cancel")
        self.assertTrue(receipt["cancelled"])
        self.assertFalse(receipt["timed_out"])


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--isolated-python-group":
        isolated_python_group_fixture(Path(sys.argv[2]), sys.argv[3])
    else:
        unittest.main()
