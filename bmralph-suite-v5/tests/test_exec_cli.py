"""类型化 CLI 实际调用回归；仅使用项目内、套件源之外的临时工作区。

不安装依赖、不联网、不启动容器或远程 Agent；不证明系统权限隔离。
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SUITE = Path(__file__).resolve().parents[1]
CLI = SUITE / "scripts/bmad-exec.py"


class ExecCliGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="sandbox-exec-cli-", dir=SUITE.parent / "tests"
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace with 'quote'"
        self.root.mkdir()
        self.tests = self.root / "tests"
        self.tests.mkdir()
        self.manifest = ".bmad-control/environment.json"
        self.fixture("        self.assertEqual(2 + 2, 4)\n")

    def fixture(self, body):
        (self.tests / "test_sample.py").write_text(
            "import unittest\n\nclass Sample(unittest.TestCase):\n"
            "    def test_sample(self):\n" + body,
            encoding="utf-8",
        )

    def raw(self, *arguments):
        return subprocess.run(
            [sys.executable, "-B", str(CLI), *arguments],
            cwd=self.root, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=8,
        )

    def invoke(self, operation, *arguments):
        result = self.raw(
            operation, "--workspace", str(self.root),
            "--environment-file", self.manifest, *arguments,
        )
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 1, result.stdout + result.stderr)
        self.assertLessEqual(len(result.stdout.encode("utf-8")), 16384)
        return result, json.loads(lines[0])

    def prepare(self):
        result, record = self.invoke(
            "register-env", "--backend", "native-python",
            "--python", sys.executable,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(record["status"], "PASS")
        return record

    def verify(self, *arguments, pattern="test_*.py"):
        return self.invoke(
            "unit-test", "--directory", "tests", "--pattern", pattern,
            "--required-test", "test_sample.Sample.test_sample", *arguments,
        )

    def query_evidence(self, verdict_file):
        result = self.raw(
            "check-evidence", "--workspace", str(self.root),
            "--verdict-file", verdict_file,
        )
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 1, result.stdout + result.stderr)
        self.assertLessEqual(len(result.stdout.encode("utf-8")), 16384)
        record = json.loads(lines[0])
        self.assertIs(record["business_reexecuted"], False)
        return result, record

    def assert_blocked(self, result, record):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(record["status"], "BLOCKED")
        self.assertTrue(record["reason"])

    def test_registration_and_repeated_check_are_separate_from_execution(self):
        record = self.prepare()
        self.assertEqual(record["operation"], "register-env")
        self.assertEqual(record["backend"], "native-python")
        self.assertEqual(record["installation_count"], 0)
        original = (self.root / self.manifest).read_bytes()
        for _ in range(2):
            result, checked = self.invoke("check-env")
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertEqual(checked["status"], "PASS")
            self.assertEqual(checked["installation_count"], 0)
        self.assertEqual((self.root / self.manifest).read_bytes(), original)
        self.assertFalse((self.root / ".bmad-runtime").exists())

    def test_actual_unit_test_has_process_and_verdict_locations(self):
        self.prepare()
        result, record = self.verify()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(record["status"], "PASS")
        self.assertEqual(record["tests_run"], 1)
        self.assertTrue((self.root / record["process_receipt"]).is_file())
        verdict = json.loads((self.root / record["verdict_path"]).read_bytes())
        self.assertEqual(verdict["status"], "PASS")
        self.assertIn("Ran 1 test", record["log_summary"]["text"])

    def test_assertion_failure_remains_failure_after_log_read(self):
        self.prepare()
        self.fixture("        self.fail('actual CLI assertion failure')\n")
        result, record = self.verify()
        self.assert_blocked(result, record)
        self.assertIn("actual CLI assertion failure", record["log_summary"]["text"])
        verdict = json.loads((self.root / record["verdict_path"]).read_bytes())
        self.assertEqual(verdict["status"], "BLOCKED")

    def test_zero_match_and_missing_required_test_do_not_pass(self):
        self.prepare()
        result, record = self.verify(pattern="test_absent_*.py")
        self.assert_blocked(result, record)
        result, record = self.verify(
            "--required-test", "test_sample.Sample.test_absent"
        )
        self.assert_blocked(result, record)

    def test_required_skip_blocks(self):
        self.prepare()
        self.fixture("        self.skipTest('required dependency missing')\n")
        result, record = self.verify()
        self.assert_blocked(result, record)
        self.assertIn("skipped=1", record["log_summary"]["text"])

    def test_zero_process_exit_without_result_is_not_completion(self):
        self.prepare()
        self.fixture("        import os\n        os._exit(0)\n")
        result, record = self.verify()
        self.assert_blocked(result, record)
        self.assertIn("缺少真实测试结果", record["reason"])

    def test_real_cancel_signals_block_cli_and_preserve_query_evidence(self):
        self.prepare()
        for signal_name in ("SIGTERM", "SIGINT"):
            with self.subTest(signal=signal_name):
                self.fixture(
                    "        import os, signal, time\n"
                    f"        print('CLI cancellation {signal_name}', flush=True)\n"
                    f"        os.kill(os.getppid(), signal.{signal_name})\n"
                    "        time.sleep(5)\n"
                )
                result, record = self.verify()
                self.assert_blocked(result, record)
                self.assertIsNone(record["tests_run"])
                self.assertIn(f"CLI cancellation {signal_name}",
                              record["log_summary"]["text"])
                process = json.loads(
                    (self.root / record["process_receipt"]).read_bytes()
                )
                verdict = json.loads(
                    (self.root / record["verdict_path"]).read_bytes()
                )
                self.assertTrue(process["cancelled"])
                self.assertFalse(process["timed_out"])
                self.assertTrue(process["cleanup_ok"])
                self.assertIsNotNone(process["returncode"])
                self.assertNotEqual(process["returncode"], 0)
                self.assertEqual(process["process_status"], "BLOCKED")
                self.assertEqual(verdict["status"], "BLOCKED")
                self.assertEqual(verdict["process_receipt"], record["process_receipt"])
                self.assertIsNone(verdict["result"])
                self.assertIsNone(verdict["evidence_after"])
                before = {
                    path.relative_to(self.root).as_posix(): path.read_bytes()
                    for path in self.root.rglob("*") if path.is_file()
                }
                queried, evidence = self.query_evidence(record["verdict_path"])
                self.assert_blocked(queried, evidence)
                after = {
                    path.relative_to(self.root).as_posix(): path.read_bytes()
                    for path in self.root.rglob("*") if path.is_file()
                }
                self.assertEqual(after, before)
        # 仅在上述回执确认清理完成后，验证入口可再次串行使用。
        self.fixture("        self.assertEqual(2 + 2, 4)\n")
        repaired, record = self.verify()
        self.assertEqual(repaired.returncode, 0, repaired.stdout + repaired.stderr)
        self.assertEqual(record["status"], "PASS")
        self.assertEqual(record["tests_run"], 1)
        self.assertEqual(len(list((self.root / ".bmad-runtime").glob("*.log"))), 3)

    def test_missing_environment_does_not_implicitly_register_or_install(self):
        for operation, arguments in (
            ("check-env", ()),
            ("unit-test", ("--directory", "tests", "--pattern", "test_*.py")),
        ):
            with self.subTest(operation=operation):
                result, record = self.invoke(operation, *arguments)
                self.assert_blocked(result, record)
        self.assertFalse((self.root / self.manifest).exists())
        self.assertFalse((self.root / ".bmad-runtime").exists())

    def test_registration_cannot_overwrite_existing_environment(self):
        self.prepare()
        original = (self.root / self.manifest).read_bytes()
        result, record = self.invoke(
            "register-env", "--backend", "native-python",
            "--python", sys.executable,
        )
        self.assert_blocked(result, record)
        self.assertEqual((self.root / self.manifest).read_bytes(), original)

    def test_missing_dependency_does_not_create_environment_record(self):
        result, record = self.invoke(
            "register-env", "--backend", "native-python",
            "--python", sys.executable,
            "--dependency", "bmad-cli-missing-dependency-fixture-914807",
        )
        self.assert_blocked(result, record)
        self.assertFalse((self.root / self.manifest).exists())

    def test_long_multibyte_log_has_explicit_bounded_summary(self):
        self.prepare()
        self.fixture("        print('中文' * 20000)\n        self.assertTrue(True)\n")
        result, record = self.verify()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(record["status"], "PASS")
        summary = record["log_summary"]
        self.assertTrue(summary["truncated"])
        self.assertIn("TRUNCATED", summary["text"])
        self.assertLessEqual(summary["summary_bytes"], 4096)
        self.assertGreater(summary["log_bytes"], 4096)

    def test_explicit_implementation_change_invalidates_cli_verdict(self):
        self.prepare()
        source = self.root / "implementation.py"
        source.write_text("VALUE = 1\n", encoding="utf-8")
        self.fixture(
            "        from pathlib import Path\n"
            "        Path('implementation.py').write_text('VALUE = 2\\n')\n"
            "        self.assertTrue(True)\n"
        )
        result, record = self.verify("--input", "implementation.py")
        self.assert_blocked(result, record)
        self.assertIn("证据失效", record["reason"])
        self.assertEqual(source.read_text(encoding="utf-8"), "VALUE = 2\n")

    def test_saved_evidence_query_passes_without_new_files_or_business_logs(self):
        self.prepare()
        verified, record = self.verify()
        self.assertEqual(verified.returncode, 0, verified.stdout)
        before = {
            path.relative_to(self.root).as_posix(): path.read_bytes()
            for path in self.root.rglob("*") if path.is_file()
        }
        result, queried = self.query_evidence(record["verdict_path"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(queried["status"], "PASS")
        self.assertEqual(queried["process_receipt"], record["process_receipt"])
        after = {
            path.relative_to(self.root).as_posix(): path.read_bytes()
            for path in self.root.rglob("*") if path.is_file()
        }
        self.assertEqual(after, before)

    def test_saved_evidence_query_blocks_after_explicit_source_change(self):
        self.prepare()
        source = self.root / "implementation.py"
        source.write_text("VALUE = 1\n", encoding="utf-8")
        verified, record = self.verify("--input", "implementation.py")
        self.assertEqual(verified.returncode, 0, verified.stdout)
        verdict_path = self.root / record["verdict_path"]
        original = verdict_path.read_bytes()
        source.write_text("VALUE = 2\n", encoding="utf-8")
        result, queried = self.query_evidence(record["verdict_path"])
        self.assert_blocked(result, queried)
        self.assertIn("证据失效", queried["reason"])
        self.assertEqual(verdict_path.read_bytes(), original)
        self.assertEqual(source.read_text(encoding="utf-8"), "VALUE = 2\n")
        self.assertEqual(len(list((self.root / ".bmad-runtime").glob("*.log"))), 1)

    def test_saved_failed_verdict_does_not_become_pass_on_query(self):
        self.prepare()
        self.fixture("        self.fail('original validation failed')\n")
        verified, record = self.verify()
        self.assert_blocked(verified, record)
        verdict_path = self.root / record["verdict_path"]
        original = verdict_path.read_bytes()
        result, queried = self.query_evidence(record["verdict_path"])
        self.assert_blocked(result, queried)
        self.assertEqual(verdict_path.read_bytes(), original)
        self.assertEqual(len(list((self.root / ".bmad-runtime").glob("*.log"))), 1)

    def test_missing_evidence_query_does_not_create_or_repair_assets(self):
        before = sorted(path.relative_to(self.root).as_posix()
                        for path in self.root.rglob("*"))
        result, record = self.query_evidence(".bmad-runtime/missing.verdict.json")
        self.assert_blocked(result, record)
        after = sorted(path.relative_to(self.root).as_posix()
                       for path in self.root.rglob("*"))
        self.assertEqual(after, before)
        self.assertFalse((self.root / ".bmad-control").exists())
        self.assertFalse((self.root / ".bmad-runtime").exists())

    def typed_plan(self, *, verdict_file=None, count=2, title="保留未完成任务"):
        tasks = []
        for index in range(count):
            tasks.append({
                "task_id": f"T{index + 1}", "title": title,
                "depends_on": ["T1"] if index == 1 else [],
                "status": "COMPLETED" if index == 0 and verdict_file else "PENDING",
                "verification": {
                    "operation": "unit-test", "environment_file": self.manifest,
                    "directory": "tests", "pattern": "test_*.py",
                    "minimum_tests": 1,
                    "required_tests": ["test_sample.Sample.test_sample"],
                    "inputs": ["implementation.py"] if verdict_file else [],
                },
                "verdict_file": verdict_file if index == 0 else None,
            })
        data = {"schema_version": 1, "plan_id": "CLI-STATE-LOCAL-01", "tasks": tasks}
        path = self.root / "plan.md"
        path.write_text(
            '---\nplan_id: "CLI-STATE-LOCAL-01"\nstatus: READY\n---\n\n'
            '# 本地状态夹具\n\n```bmad-tasks\n' +
            json.dumps(data, ensure_ascii=False) + "\n```\n", encoding="utf-8",
        )
        return path

    def project(self, *arguments):
        before = {
            path.relative_to(self.root).as_posix(): path.read_bytes()
            for path in self.root.rglob("*") if path.is_file()
        }
        result = self.raw(
            "render-state", "--workspace", str(self.root),
            "--plan-file", "plan.md", *arguments,
        )
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 1, result.stdout + result.stderr)
        self.assertLessEqual(len(result.stdout.encode("utf-8")), 16384)
        record = json.loads(lines[0])
        self.assertIs(record["business_reexecuted"], False)
        self.assertIs(record["state_saved"], False)
        after = {
            path.relative_to(self.root).as_posix(): path.read_bytes()
            for path in self.root.rglob("*") if path.is_file()
        }
        self.assertEqual(after, before)
        return result, record

    def test_pending_state_projection_preserves_all_tasks_without_creating_runtime(self):
        self.typed_plan()
        result, record = self.project()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(record["status"], "READY")
        self.assertEqual(record["ready_tasks"], ["T1"])
        self.assertEqual(record["unfinished_count"], 2)
        self.assertIn("T1 [READY]", record["view"])
        self.assertIn("T2 [PENDING]", record["view"])
        self.assertFalse((self.root / ".bmad-control").exists())
        self.assertFalse((self.root / ".bmad-runtime").exists())

    def test_state_projection_uses_real_receipt_and_blocks_after_source_change(self):
        self.prepare()
        source = self.root / "implementation.py"
        source.write_text("VALUE = 1\n", encoding="utf-8")
        verified, receipt = self.verify("--input", "implementation.py")
        self.assertEqual(verified.returncode, 0, verified.stdout)
        self.typed_plan(verdict_file=receipt["verdict_path"])
        result, record = self.project()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(record["ready_tasks"], ["T2"])
        self.assertEqual(record["unfinished_count"], 1)
        source.write_text("VALUE = 2\n", encoding="utf-8")
        result, record = self.project()
        self.assert_blocked(result, record)
        self.assertEqual(record["ready_tasks"], [])
        self.assertEqual(record["unfinished_count"], 2)
        self.assertIn("T1 [BLOCKED]", record["view"])
        self.assertEqual(len(list((self.root / ".bmad-runtime").glob("*.log"))), 1)

    def test_legacy_state_projection_does_not_migrate_manual_progress(self):
        (self.root / "plan.md").write_text(
            '---\nplan_id: "CLI-STATE-LOCAL-01"\n---\n\n- [x] old completion\n',
            encoding="utf-8",
        )
        result, record = self.project()
        self.assert_blocked(result, record)
        self.assertIn("平台记录", record["reason"])
        self.assertNotIn("view", record)

    def test_state_projection_line_and_multibyte_budgets_fail_without_truncation(self):
        self.typed_plan(count=78)
        result, record = self.project()
        self.assert_blocked(result, record)
        self.assertNotIn("view", record)
        self.typed_plan(title="中文预算" * 100)
        result, record = self.project("--maximum-bytes", "256")
        self.assert_blocked(result, record)
        self.assertNotIn("view", record)

    def test_json_escaping_budget_blocks_instead_of_discarding_task_view(self):
        self.typed_plan(count=14, title="\\" * 600)
        result, record = self.project()
        self.assert_blocked(result, record)
        self.assertIn("必要元数据超过输出预算", record["reason"])
        self.assertNotIn("view", record)
        self.assertNotIn("output_truncated", record)

    def test_state_projection_missing_plan_and_increased_budget_fail_closed(self):
        result, record = self.project()
        self.assert_blocked(result, record)
        self.assertFalse((self.root / "plan.md").exists())
        self.typed_plan()
        for arguments in (("--maximum-lines", "81"), ("--maximum-bytes", "16385")):
            with self.subTest(arguments=arguments):
                result, record = self.project(*arguments)
                self.assert_blocked(result, record)
                self.assertNotIn("view", record)

    def test_unsupported_operations_and_missing_arguments_fail_closed(self):
        for arguments in (
            (), ("render-state",), ("race-test",), ("config-syntax",),
            ("shell",), ("unit-test",),
        ):
            with self.subTest(arguments=arguments):
                result = self.raw(*arguments)
                self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / ".bmad-control").exists())
        self.assertFalse((self.root / ".bmad-runtime").exists())

    def test_unknown_and_abbreviated_options_are_not_accepted(self):
        for option in ("--shell", "--work", "--env", "--back"):
            with self.subTest(option=option):
                result = self.raw(
                    "register-env", "--workspace", str(self.root),
                    "--environment-file", self.manifest,
                    "--backend", "native-python", "--python", sys.executable,
                    option, "invalid",
                )
                self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / self.manifest).exists())

    def test_help_does_not_claim_unimplemented_operations(self):
        result = self.raw("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("register-env", result.stdout)
        self.assertIn("check-env", result.stdout)
        self.assertIn("unit-test", result.stdout)
        self.assertIn("check-evidence", result.stdout)
        self.assertIn("render-state", result.stdout)
        self.assertNotIn("race-test", result.stdout)
        self.assertNotIn("config-syntax", result.stdout)
        self.assertFalse((self.root / ".bmad-control").exists())


    def input_request(self, **changes):
        request = {
            "goal": "完成当前任务并保留全部待办",
            "authorization": "仅本地项目内实施；不提交、不启动远程 Agent",
            "task_id": "T1", "constraints": ["保护既有修改"],
            "capabilities": ["定向读取当前源码与相关测试"],
            "code_files": ["tests/test_sample.py"],
            "unfinished_files": ["tests/test_sample.py"],
            "feedback": ["调用方已核验的最近反馈"],
            "observed_host_bytes": None,
        }
        request.update(changes)
        (self.root / "request.json").write_text(
            json.dumps(request, ensure_ascii=False), encoding="utf-8",
        )
        return request

    def assemble_request(self, *arguments):
        before = {
            path.relative_to(self.root).as_posix(): path.read_bytes()
            for path in self.root.rglob("*") if path.is_file()
        }
        result = self.raw(
            "assemble-input", "--workspace", str(self.root),
            "--plan-file", "plan.md", "--request-file", "request.json",
            *arguments,
        )
        lines = result.stdout.splitlines()
        self.assertEqual(len(lines), 1, result.stdout + result.stderr)
        self.assertLessEqual(len(result.stdout.encode("utf-8")), 16384)
        record = json.loads(lines[0])
        after = {
            path.relative_to(self.root).as_posix(): path.read_bytes()
            for path in self.root.rglob("*") if path.is_file()
        }
        self.assertEqual(after, before)
        return result, record

    def test_input_assembly_cli_preserves_current_contract_sources_and_pending_tasks(self):
        self.typed_plan()
        request = self.input_request()
        result, record = self.assemble_request()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(record["operation"], "assemble-input")
        self.assertEqual(record["status"], "READY")
        self.assertEqual(record["task_id"], "T1")
        self.assertIs(record["business_reexecuted"], False)
        self.assertIs(record["state_saved"], False)
        payload = json.loads(record["payload"])
        self.assertEqual(payload["goal"], request["goal"])
        self.assertEqual(payload["authorization"], request["authorization"])
        self.assertEqual(payload["feedback"], request["feedback"])
        self.assertEqual(payload["task"]["verification"]["pattern"], "test_*.py")
        self.assertIn("T2 [PENDING]", payload["state_projection"]["view"])
        self.assertIn("class Sample", payload["code"][0])
        self.assertEqual(payload["code"], payload["unfinished_changes"])
        self.assertEqual(record["controlled_bytes"], len(record["payload"].encode("utf-8")))
        self.assertEqual(record["host_input_coverage"], "UNKNOWN")
        self.assertFalse((self.root / ".bmad-control").exists())
        self.assertFalse((self.root / ".bmad-runtime").exists())

    def test_input_assembly_cli_counts_observed_host_bytes_without_claiming_full_coverage(self):
        self.typed_plan()
        self.input_request(observed_host_bytes=1000)
        result, record = self.assemble_request()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(record["accounted_bytes"], record["controlled_bytes"] + 1000)
        self.assertEqual(record["host_input_coverage"], "PARTIAL_OBSERVATION")

    def test_input_assembly_cli_missing_request_and_legacy_plan_do_not_create_assets(self):
        self.typed_plan()
        result, record = self.assemble_request()
        self.assert_blocked(result, record)
        self.input_request()
        (self.root / "plan.md").write_text(
            '---\nplan_id: "CLI-STATE-LOCAL-01"\n---\n\n- [x] old completion\n',
            encoding="utf-8",
        )
        result, record = self.assemble_request()
        self.assert_blocked(result, record)
        self.assertNotIn("payload", record)
        self.assertFalse((self.root / ".bmad-control").exists())
        self.assertFalse((self.root / ".bmad-runtime").exists())

    def test_input_assembly_cli_does_not_substitute_unknown_or_unready_tasks(self):
        self.typed_plan()
        for task_id in ("UNKNOWN", "T2"):
            with self.subTest(task_id=task_id):
                self.input_request(task_id=task_id)
                result, record = self.assemble_request()
                self.assert_blocked(result, record)
                self.assertNotIn("payload", record)

    def test_input_assembly_cli_rejects_forged_projection_and_source_escape(self):
        self.typed_plan()
        for changes in (
            {"state_projection": {"status": "COMPLETED"}},
            {"code_files": ["../outside.py"]},
            {"code_files": ["missing.py"]},
            {"observed_host_bytes": True},
        ):
            with self.subTest(changes=changes):
                self.input_request(**changes)
                result, record = self.assemble_request()
                self.assert_blocked(result, record)
                self.assertNotIn("payload", record)

    def test_input_assembly_cli_small_and_increased_budgets_fail_closed(self):
        self.typed_plan()
        self.input_request()
        for maximum in ("256", "131073"):
            with self.subTest(maximum=maximum):
                result, record = self.assemble_request("--maximum-bytes", maximum)
                self.assert_blocked(result, record)
                self.assertNotIn("payload", record)

    def test_input_assembly_cli_outer_json_budget_blocks_without_partial_payload(self):
        self.typed_plan()
        (self.root / "escaped.py").write_text("\\" * 4500, encoding="utf-8")
        self.input_request(code_files=["escaped.py"], unfinished_files=[])
        result, record = self.assemble_request()
        self.assert_blocked(result, record)
        self.assertIn("CLI 转义元数据超过输出预算", record["reason"])
        self.assertNotIn("payload", record)
        self.assertNotIn("output_truncated", record)
        self.assertIs(record["business_reexecuted"], False)
        self.assertIs(record["state_saved"], False)

    def test_input_assembly_cli_help_and_missing_arguments_have_no_runtime_side_effects(self):
        result = self.raw("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("assemble-input", result.stdout)
        result = self.raw("assemble-input", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--request-file", result.stdout)
        self.assertIn("--maximum-bytes", result.stdout)
        result = self.raw("assemble-input", "--workspace", str(self.root))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / ".bmad-control").exists())
        self.assertFalse((self.root / ".bmad-runtime").exists())


if __name__ == "__main__":
    unittest.main()
