"""L0 登记与 L1 复核反例；只测试已实现的本机 Python 后端。

夹具位于项目内、套件分发源之外；不安装依赖、不联网、不启动容器。
本地通过不证明 GCC/musl 固定镜像、容器隔离或远程运行时可用。
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "bmad_environment_under_test", SUITE / "scripts/bmad_environment.py"
)
environment = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = environment
SPEC.loader.exec_module(environment)


class EnvironmentGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="sandbox-environment-", dir=SUITE.parent / "tests"
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "workspace with 'quote'"
        self.root.mkdir()
        self.relative = ".bmad-control/environment.json"
        self.path = self.root / self.relative

    def register(self, **kwargs):
        return environment.register(
            self.root, self.relative, sys.executable, **kwargs
        )

    def check(self):
        return environment.check(self.root, self.relative)

    def revise_record(self, mutate):
        data = json.loads(self.path.read_bytes())
        mutate(data)
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def test_actual_environment_registration_and_read_only_reuse(self):
        registered = self.register()
        self.assertEqual(registered["backend"], "native-python")
        self.assertEqual(registered["details"]["version"],
                         list(sys.version_info[:3]))
        original = self.path.read_bytes()
        before = sorted(path.relative_to(self.root).as_posix()
                        for path in self.root.rglob("*"))
        for _ in range(3):
            result = self.check()
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["installation_count"], 0)
            self.assertEqual(result["environment"], registered)
            self.assertEqual(self.path.read_bytes(), original)
        after = sorted(path.relative_to(self.root).as_posix()
                       for path in self.root.rglob("*"))
        self.assertEqual(after, before)

    def test_registration_never_overwrites_existing_record(self):
        self.register()
        original = self.path.read_bytes()
        with patch.object(environment, "probe") as probe:
            with self.assertRaises(environment.EnvironmentNotReady):
                self.register()
        probe.assert_not_called()
        self.assertEqual(self.path.read_bytes(), original)

    def test_l1_missing_registration_blocks_without_creating_assets(self):
        with patch.object(environment, "probe") as probe:
            with self.assertRaises(environment.EnvironmentNotReady):
                self.check()
        probe.assert_not_called()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_all_actual_probe_commands_are_noninteractive_and_bounded(self):
        actual_run = environment.subprocess.run
        with patch.object(environment.subprocess, "run", wraps=actual_run) as run:
            self.register()
            self.check()
            self.check()
        self.assertEqual(run.call_count, 3)
        for call in run.call_args_list:
            argv = call.args[0]
            self.assertEqual(argv[1:4], ["-I", "-B", "-c"])
            self.assertEqual(argv[4], environment.PROBE_CODE)
            self.assertEqual(call.kwargs["stdin"], subprocess.DEVNULL)
            self.assertEqual(call.kwargs["timeout"], 15)
            self.assertFalse(call.kwargs["check"])
            self.assertEqual(call.kwargs["env"]["PIP_NO_INPUT"], "1")
            for installer in ("pip", "apk", "apt-get", "docker"):
                self.assertNotIn(installer, argv)

    def test_missing_dependency_blocks_without_writing_registration(self):
        with self.assertRaises(environment.EnvironmentNotReady):
            self.register(dependencies=("bmad-nonexistent-dependency-fixture-794613",))
        self.assertFalse(self.path.exists())
        self.assertEqual(list(self.root.iterdir()), [])

    def test_missing_interpreter_blocks_before_process_launch(self):
        with patch.object(environment.shutil, "which", return_value=None), \
                patch.object(environment.subprocess, "run") as run:
            with self.assertRaises(environment.EnvironmentNotReady):
                self.register()
        run.assert_not_called()
        self.assertFalse(self.path.exists())

    def test_missing_explicit_tool_blocks_without_installation(self):
        real_which = environment.shutil.which

        def locate(name):
            if name == "bmad-missing-tool-fixture":
                return None
            return real_which(name)

        with patch.object(environment.shutil, "which", side_effect=locate):
            with self.assertRaises(environment.EnvironmentNotReady):
                self.register(executables=("bmad-missing-tool-fixture",))
        self.assertFalse(self.path.exists())

    def test_probe_timeout_blocks_without_registration(self):
        with patch.object(environment.subprocess, "run", side_effect=
                          subprocess.TimeoutExpired("python probe", 15)):
            with self.assertRaises(environment.EnvironmentNotReady):
                self.register()
        self.assertFalse(self.path.exists())

    def test_interpreter_identity_change_invalidates_registration(self):
        self.register()
        self.revise_record(lambda data: data["python"].update(sha256="0" * 64))
        original = self.path.read_bytes()
        with self.assertRaises(environment.EnvironmentNotReady):
            self.check()
        self.assertEqual(self.path.read_bytes(), original)

    def test_unsupported_backend_is_not_silently_replaced(self):
        self.register()
        self.revise_record(lambda data: data.update(backend="container-unimplemented"))
        with patch.object(environment, "probe") as probe:
            with self.assertRaises(environment.EnvironmentNotReady):
                self.check()
        probe.assert_not_called()

    def test_duplicate_json_keys_block_before_probe(self):
        self.path.parent.mkdir()
        self.path.write_text('{"schema_version":1,"schema_version":1}',
                             encoding="utf-8")
        with patch.object(environment, "probe") as probe:
            with self.assertRaises(environment.EnvironmentNotReady):
                self.check()
        probe.assert_not_called()

    def test_oversized_record_blocks_before_probe(self):
        self.path.parent.mkdir()
        self.path.write_bytes(b" " * 65537)
        with patch.object(environment, "probe") as probe:
            with self.assertRaises(environment.EnvironmentNotReady):
                self.check()
        probe.assert_not_called()

    def test_record_changed_during_check_blocks_without_overwriting_change(self):
        registered = self.register()
        external = b'{"external_edit":true}\n'

        def concurrent_probe(*args, **kwargs):
            self.path.write_bytes(external)
            return registered

        with patch.object(environment, "probe", side_effect=concurrent_probe):
            with self.assertRaises(environment.EnvironmentNotReady):
                self.check()
        self.assertEqual(self.path.read_bytes(), external)

    def test_unrelated_document_edit_does_not_change_environment_identity(self):
        registered = self.register()
        (self.root / "notes.md").write_text("unrelated task notes\n", encoding="utf-8")
        result = self.check()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["environment"], registered)

    def test_invalid_duplicate_and_excessive_names_block_before_probe(self):
        cases = (("valid", "valid"), ("bad/name",), ("--install",),
                 tuple(f"package-{index}" for index in range(65)))
        for names in cases:
            with self.subTest(names=names):
                with patch.object(environment.subprocess, "run") as run:
                    with self.assertRaises(environment.EnvironmentNotReady):
                        self.register(dependencies=names)
                run.assert_not_called()
                self.assertFalse(self.path.exists())

    def test_escape_symlink_and_distribution_paths_are_rejected(self):
        alias = self.root / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        paths = ("../outside/environment.json", "alias/environment.json",
                 "bmralph-suite-v5/logs/environment.json")
        for relative in paths:
            with self.subTest(relative=relative):
                with patch.object(environment, "probe") as probe:
                    with self.assertRaises(environment.SupervisorError):
                        environment.register(self.root, relative, sys.executable)
                probe.assert_not_called()


if __name__ == "__main__":
    unittest.main()
