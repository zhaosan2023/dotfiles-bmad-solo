"""Pi 获准入口与共享预算集成反例；不启动 Pi、不连接真实网关。

进程、转发及安装元数据均显式拦截。循环反例只运行本地合成单测，
不把合成 HTTP 计数、配置文件或测试通过宣称为真实独立执行证据。
"""
import copy
import json
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "scripts"))
import bmad_agent_backend as agent
import bmad_loop as loop
import bmad_pi_transport as transport
import bmad_supervisor as supervisor
from bmad_pi_budget import PiNetworkBudget
import test_pi_backend as pi_fixtures
import test_batch_guards as batch_fixtures


class PiActivationGuards(unittest.TestCase):
    def pi_guards(self):
        guards = pi_fixtures.PiBackendGuards(
            "test_missing_credentials_blocks_invoke_before_request_or_process")
        self.addCleanup(guards.doCleanups)
        guards.setUp()
        guards.config["pi"].update(no_progress_rounds=6, gateway={
            "base_url": "http://127.0.0.1:8080/v1", "api": "openai-completions"})
        guards.active(threshold=6)
        return guards

    def spec(self, root, **changes):
        options = dict(workspace=root, plan_file="plan.md", request_file="request.json",
                       backend="pi-agent", backend_config="backend.json",
                       maximum_rounds=8, maximum_calls=8, timeout_seconds=12,
                       no_progress_rounds=6, maximum_model_requests=30,
                       maximum_data_bytes=15_000_000)
        options.update(changes)
        return loop.LoopSpec(**options)

    def test_explicit_pi_budget_accepts_only_authorized_caps_and_threshold(self):
        guards = self.pi_guards()
        self.spec(guards.root).validate()
        for changes in ({"maximum_model_requests": None},
                        {"maximum_model_requests": True},
                        {"maximum_model_requests": 31},
                        {"maximum_data_bytes": None},
                        {"maximum_data_bytes": 15_000_001},
                        {"no_progress_rounds": 3},
                        {"backend": "headless"}):
            with self.subTest(changes=changes):
                with self.assertRaises(supervisor.SupervisorError):
                    self.spec(guards.root, **changes).validate()

    def test_gateway_invoke_requires_shared_budget_before_process_launch(self):
        guards = self.pi_guards()
        with patch.object(agent, "__file__", str(guards.root / "backend.py")), \
                patch.dict(os.environ, {pi_fixtures.CREDENTIAL: pi_fixtures.TEST_VALUE}, clear=True), \
                patch.object(agent, "run") as runner:
            with self.assertRaisesRegex(supervisor.SupervisorError, "共享"):
                agent.invoke(workspace=guards.root, config=guards.config,
                             assembled={"payload": json.dumps(guards.startup)},
                             runtime_directory=".bmad-runtime",
                             deadline=time.monotonic() + 5,
                             cancel_requested=lambda: False)
        runner.assert_not_called()
        self.assertFalse((guards.root / ".bmad-runtime").exists())

    def test_gateway_address_and_protocol_cannot_be_changed(self):
        guards = self.pi_guards()
        for value in ({"base_url": "http://example.invalid/v1", "api": "openai-completions"},
                      {"base_url": "http://127.0.0.1:8080/v1", "api": "anthropic-messages"},
                      {"base_url": "http://127.0.0.1:8080/v1", "api": "openai-completions",
                       "api_key": "synthetic-forbidden-key"}):
            config = copy.deepcopy(guards.config)
            config["pi"]["gateway"] = value
            with self.assertRaises(supervisor.SupervisorError):
                agent.validate_pi_config(config)

    def intercepted_invoke(self, guards, budget, *, complete=True, transport_status="READY",
                           process_cancelled=False):
        owner = self
        token = "a" * 64

        class InterceptedTransport:
            def __init__(self, **options):
                owner.transport_options = options
                self.cleanup_ok = False
                self.base_url = "http://127.0.0.1:19090/v1"
                self.token = token

            def __enter__(self):
                if complete:
                    number = budget.reserve_request(3)
                    budget.accept_response(number, 4)
                    budget.finish_request(number, http_status=200, outcome="COMPLETE")
                return self

            def __exit__(self, *unused):
                self.cleanup_ok = True
                self.token = ""
                return False

            def snapshot(self):
                return {"status": transport_status, "reason": "", "cleanup_ok": self.cleanup_ok,
                        "network_budget": budget.snapshot(), "thread_active": False}

        def process_receipt(spec):
            self.captured_spec = spec
            relative = spec.argv[spec.argv.index("--pi-transport-file") + 1]
            self.binding_path = guards.root / relative
            self.binding_mode = self.binding_path.stat().st_mode & 0o777
            self.binding_data = json.loads(self.binding_path.read_bytes())
            log = guards.root / ".bmad-runtime/intercepted-pi.jsonl"
            log.write_bytes(b"".join(json.dumps(item).encode() + b"\n"
                                     for item in guards.stream()))
            return {"reason": "", "log_path": log.relative_to(guards.root).as_posix(),
                    "receipt_path": ".bmad-runtime/intercepted-process.json",
                    "returncode": 0, "timed_out": False, "cancelled": process_cancelled,
                    "cleanup_ok": True, "process_status": "PASS"}

        with patch.object(agent, "__file__", str(guards.root / "backend.py")), \
                patch.dict(os.environ, {pi_fixtures.CREDENTIAL: pi_fixtures.TEST_VALUE}, clear=True), \
                patch.object(agent.environment, "check", return_value={
                    "environment": {"python": {"path": sys.executable}}}), \
                patch.object(transport, "PiTransport", InterceptedTransport), \
                patch.object(agent, "run", side_effect=process_receipt):
            return agent.invoke(workspace=guards.root, config=guards.config,
                                assembled={"payload": json.dumps(guards.startup)},
                                runtime_directory=".bmad-runtime", deadline=time.monotonic() + 5,
                                cancel_requested=lambda: False, network_budget=budget)

    def test_shared_transport_binding_is_private_removed_and_not_in_public_receipt(self):
        guards = self.pi_guards()
        budget = PiNetworkBudget(maximum_requests=30, maximum_bytes=15_000_000,
                                 deadline=time.monotonic() + 15)
        result = self.intercepted_invoke(guards, budget)
        self.assertEqual(result["status"], "PASS")
        self.assertIs(self.transport_options["budget"], budget)
        self.assertEqual(self.transport_options["credential"], pi_fixtures.TEST_VALUE)
        self.assertEqual(self.binding_mode, 0o600)
        self.assertFalse(self.binding_path.exists())
        self.assertEqual(self.binding_data["model"], guards.config["pi"]["model"])
        self.assertTrue(result["transport"]["cleanup_ok"])
        public = json.dumps(result) + repr(self.captured_spec)
        self.assertNotIn(pi_fixtures.TEST_VALUE, public)
        self.assertNotIn(self.binding_data["token"], public)

    def test_previous_session_complete_event_cannot_prove_current_session_request(self):
        guards = self.pi_guards()
        budget = PiNetworkBudget(maximum_requests=30, maximum_bytes=15_000_000,
                                 deadline=time.monotonic() + 15)
        self.assertEqual(self.intercepted_invoke(guards, budget)["status"], "PASS")
        result = self.intercepted_invoke(guards, budget, complete=False)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["category"], "NETWORK_ERROR")
        self.assertEqual(budget.requests, 1)

    def test_transport_failure_cannot_be_masked_by_complete_pi_protocol(self):
        guards = self.pi_guards()
        budget = PiNetworkBudget(maximum_requests=30, maximum_bytes=15_000_000,
                                 deadline=time.monotonic() + 15)
        result = self.intercepted_invoke(guards, budget, transport_status="BLOCKED",
                                        process_cancelled=True)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["category"], "NETWORK_ERROR")
        self.assertTrue(result["cleanup_ok"])

    def test_exec_uses_internal_token_and_isolated_streaming_provider_configuration(self):
        guards = self.pi_guards()
        runtime = guards.root / ".bmad-runtime"
        runtime.mkdir()
        request = runtime / "request.json"
        request.write_text(json.dumps({"protocol": agent.PROTOCOL}))
        binding = runtime / "transport.json"
        binding.write_text(json.dumps({"schema_version": 1,
            "base_url": "http://127.0.0.1:19090/v1", "token": "b" * 64,
            "model": guards.config["pi"]["model"], "provider": guards.config["pi"]["provider"]}))
        binding.chmod(0o600)
        package = guards.root / "intercepted-install-metadata"
        package.mkdir()
        (package / "package.json").write_text(json.dumps({
            "name": agent.PI_PACKAGE, "version": agent.PI_VERSION,
            "repository": {"url": "git+" + agent.PI_SOURCE + ".git"}}))
        executable = package / "dist/bundle/cli.js"
        original_resolve = Path.resolve

        def resolve(path, *args, **kwargs):
            return executable if str(path) == "/usr/local/bin/pi" else original_resolve(path, *args, **kwargs)

        with patch.object(Path, "cwd", return_value=guards.root), \
                patch.object(Path, "resolve", resolve), \
                patch.object(agent.os, "getppid", return_value=os.getpid()), \
                patch.dict(os.environ, {pi_fixtures.CREDENTIAL: pi_fixtures.TEST_VALUE}, clear=True), \
                patch.object(agent.os, "dup2"), \
                patch.object(agent.os, "execve", side_effect=RuntimeError("intercepted exec")) as execute:
            with self.assertRaisesRegex(RuntimeError, "intercepted exec"):
                agent._pi_exec(guards.config, request.relative_to(guards.root).as_posix(),
                               os.getpid(), binding.relative_to(guards.root).as_posix())
        _, argv, environment = execute.call_args.args
        self.assertEqual(environment[pi_fixtures.CREDENTIAL], "b" * 64)
        private = Path(environment["PI_CODING_AGENT_DIR"])
        self.assertTrue(private.is_relative_to(runtime))
        models = json.loads((private / "models.json").read_bytes())
        provider = models["providers"][guards.config["pi"]["provider"]]
        self.assertEqual(provider["api"], "openai-completions")
        self.assertEqual(provider["baseUrl"], "http://127.0.0.1:19090/v1")
        self.assertEqual(provider["apiKey"], "${" + pi_fixtures.CREDENTIAL + "}")
        settings = json.loads((private / "settings.json").read_bytes())
        self.assertFalse(settings["retry"]["enabled"])
        self.assertEqual(settings["retry"]["provider"]["maxRetries"], 0)
        self.assertEqual(settings["cacheWarming"], "off")
        self.assertNotIn(pi_fixtures.TEST_VALUE, json.dumps(models) + repr(argv) + repr(environment))

    def batch_guards(self):
        guards = batch_fixtures.BatchGuards(
            "test_budget_exhaustion_stops_new_calls_and_preserves_changes")
        self.addCleanup(guards.doCleanups)
        guards.setUp()
        config = {"runtime_kind": "pi-agent", "pi": {"no_progress_rounds": 6,
                  "gateway": {"base_url": "http://127.0.0.1:8080/v1",
                              "api": "openai-completions"}}}
        return guards, config

    def test_six_unchanged_failures_share_one_budget_and_prohibit_seventh_call(self):
        guards, config = self.batch_guards()
        seen = []
        before = (guards.root / "plan.md").read_bytes()

        def intercepted_call(**options):
            budget = options["network_budget"]
            seen.append(budget)
            number = budget.reserve_request(3)
            budget.accept_response(number, 4)
            budget.finish_request(number, http_status=200, outcome="COMPLETE")
            return {"operation": "agent-call", "status": "PASS", "reason": "",
                    "cleanup_ok": True, "cancelled": False, "timed_out": False,
                    "returncode": 0, "category": "OK"}

        with patch.object(agent, "load", return_value=(config, {})), \
                patch.object(agent, "invoke", side_effect=intercepted_call) as invoke:
            result = loop.start(self.spec(guards.root, request_file="T1-request.json"))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("持续无进展", result["reason"])
        self.assertEqual(invoke.call_count, 6)
        self.assertEqual(result["rounds"], 6)
        self.assertEqual(result["no_progress_count"], 6)
        self.assertTrue(all(item is seen[0] for item in seen))
        self.assertEqual(result["network_budget"]["model_request_attempts"], 6)
        self.assertEqual(result["network_budget"]["data_bytes"], 42)
        self.assertEqual(result["completed_tasks"], [])
        self.assertTrue(result["cleanup_ok"])
        self.assertFalse(loop.writer_active(guards.root))
        self.assertEqual((guards.root / "plan.md").read_bytes(), before)

    def test_transport_triggered_cancellation_remains_blocked_not_user_suspended(self):
        guards, config = self.batch_guards()
        failure = {"operation": "agent-call", "status": "BLOCKED",
                   "reason": "synthetic transport gate failure", "category": "NETWORK_ERROR",
                   "returncode": 0, "cleanup_ok": True, "cancelled": True, "timed_out": False}
        with patch.object(agent, "load", return_value=(config, {})), \
                patch.object(agent, "invoke", return_value=failure) as invoke, \
                patch.object(loop.execution, "unit_test") as verify:
            result = loop.start(self.spec(guards.root, request_file="T1-request.json"))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], failure["reason"])
        invoke.assert_called_once()
        verify.assert_not_called()
        self.assertTrue(result["cleanup_ok"])
        self.assertFalse(loop.writer_active(guards.root))

    def test_real_pi_without_metered_gateway_blocks_before_agent_or_verification(self):
        guards, config = self.batch_guards()
        config["pi"].pop("gateway")
        with patch.object(agent, "load", return_value=(config, {})), \
                patch.object(agent, "invoke") as invoke, \
                patch.object(loop.execution, "unit_test") as verify:
            result = loop.start(self.spec(guards.root, request_file="T1-request.json"))
        self.assertEqual(result["status"], "BLOCKED")
        invoke.assert_not_called()
        verify.assert_not_called()
        self.assertTrue(result["cleanup_ok"])


if __name__ == "__main__":
    unittest.main()
