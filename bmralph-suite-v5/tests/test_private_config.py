"""私有配置加载反例：仅合成凭据，不启动 Pi、不联网或读取真实认证。"""
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "scripts"))
import bmad_private_config as private
from bmad_supervisor import SupervisorError

SPEC = importlib.util.spec_from_file_location("private_config_cli_unit", SUITE / "scripts/bmad-loop.py")
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)
SYNTHETIC_VALUE = "unit-only-not-a-real-key"


class PrivateConfigGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sandbox-private-", dir=SUITE.parent / "tests")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / ".bmad-private"
        self.directory.mkdir(mode=0o700)
        self.path = self.directory / "credentials.env"
        self.relative = ".bmad-private/credentials.env"
        self.write(private.CREDENTIAL_NAME + "=" + SYNTHETIC_VALUE + "\n")

    def write(self, body):
        self.path.write_text(body, encoding="utf-8")
        self.path.chmod(0o600)

    def blocked(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SupervisorError) as error:
                with private.credential_environment(self.root, self.relative):
                    self.fail("非法私有配置不得进入任务作用域")
            self.assertNotIn(SYNTHETIC_VALUE, str(error.exception))
            self.assertNotIn(private.CREDENTIAL_NAME, os.environ)

    def test_explicit_load_is_scoped_and_never_prints_secret(self):
        with patch.dict(os.environ, {}, clear=True), patch("sys.stdout", new_callable=io.StringIO) as output:
            with private.credential_environment(self.root, self.relative) as result:
                self.assertIsNone(result)
                self.assertEqual(os.environ[private.CREDENTIAL_NAME], SYNTHETIC_VALUE)
            self.assertNotIn(private.CREDENTIAL_NAME, os.environ)
            self.assertEqual(output.getvalue(), "")

    def test_preexisting_environment_is_restored_after_normal_exit(self):
        with patch.dict(os.environ, {private.CREDENTIAL_NAME: "original-unit-value"}, clear=True):
            with private.credential_environment(self.root, self.relative):
                self.assertEqual(os.environ[private.CREDENTIAL_NAME], SYNTHETIC_VALUE)
            self.assertEqual(os.environ[private.CREDENTIAL_NAME], "original-unit-value")

    def test_environment_is_restored_after_exception(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "unit failure"):
                with private.credential_environment(self.root, self.relative):
                    raise RuntimeError("unit failure")
            self.assertNotIn(private.CREDENTIAL_NAME, os.environ)

    def test_unspecified_path_does_not_read_any_private_file(self):
        with patch.object(private, "_read_credential", side_effect=AssertionError("unexpected read")):
            with private.credential_environment(self.root):
                pass

    def test_quotes_comments_and_blank_lines_are_literal_only(self):
        for quote in ("", "'", '"'):
            with self.subTest(quote=quote):
                self.write("# unit comment\n\n" + private.CREDENTIAL_NAME + "=" + quote + SYNTHETIC_VALUE + quote + "\n")
                with patch.dict(os.environ, {}, clear=True):
                    with private.credential_environment(self.root, self.relative):
                        self.assertEqual(os.environ[private.CREDENTIAL_NAME], SYNTHETIC_VALUE)

    def test_unknown_duplicate_or_exported_variables_block(self):
        for body in ("OTHER_API_KEY=" + SYNTHETIC_VALUE,
                     (private.CREDENTIAL_NAME + "=" + SYNTHETIC_VALUE + "\n") * 2,
                     "export " + private.CREDENTIAL_NAME + "=" + SYNTHETIC_VALUE):
            with self.subTest(body_kind=body.split("=")[0]):
                self.write(body)
                self.blocked()

    def test_shell_expansion_and_commands_are_never_executed(self):
        for value in ("$(touch marker)", "`touch marker`", "$OTHER", "abc;command",
                      "abc|command", "abc&&command", "abc\\ndef", '"unterminated',
                      "'abc def'", "abc # inline comment"):
            with self.subTest(value_kind=value[:1]):
                self.write(private.CREDENTIAL_NAME + "=" + value + "\n")
                self.blocked()
        self.assertFalse((self.root / "marker").exists())

    def test_missing_empty_non_ascii_and_oversized_files_block(self):
        for body in ("", "# no credential\n", private.CREDENTIAL_NAME + "=\n",
                     private.CREDENTIAL_NAME + "=非字面量\n", "x" * (private.MAX_CREDENTIAL_BYTES + 1)):
            self.write(body)
            self.blocked()
        self.path.unlink()
        self.blocked()

    def test_absolute_parent_and_other_directory_paths_block(self):
        for relative in (str(self.path), "../credentials.env", ".bmad-private/../credentials.env",
                         "credentials.env", ".bmad-private/nested/credentials.env",
                         ".bmad-private/", ".bmad-private\\credentials.env"):
            with self.subTest(relative=relative):
                with self.assertRaises(SupervisorError):
                    with private.credential_environment(self.root, relative):
                        self.fail("路径越界不得加载")

    def test_directory_and_file_permissions_must_be_private(self):
        for mode in (0o644, 0o640, 0o400, 0o700):
            self.path.chmod(mode)
            self.blocked()
        self.path.chmod(0o600)
        for mode in (0o755, 0o750, 0o777):
            self.directory.chmod(mode)
            self.blocked()
        self.directory.chmod(0o700)

    def test_file_symlink_and_hardlink_block(self):
        target = self.directory / "target.env"
        self.path.rename(target)
        self.path.symlink_to(target.name)
        self.blocked()
        self.path.unlink()
        os.link(target, self.path)
        self.blocked()

    def test_directory_symlink_blocks(self):
        target = self.root / "other-private"
        self.directory.rename(target)
        self.directory.symlink_to(target.name, target_is_directory=True)
        self.blocked()

    def test_nonregular_file_blocks_without_waiting_for_input(self):
        self.path.unlink()
        os.mkfifo(self.path, mode=0o600)
        self.blocked()

    def test_wrong_owner_blocks_before_reading_value(self):
        with patch.object(private.os, "geteuid", return_value=os.geteuid() + 1), \
                patch.object(private.os, "read", side_effect=AssertionError("unexpected credential read")):
            self.blocked()

    def test_file_change_during_read_blocks(self):
        original = os.read
        changed = False

        def mutate(descriptor, count):
            nonlocal changed
            result = original(descriptor, count)
            if not changed:
                changed = True
                self.write(private.CREDENTIAL_NAME + "=different-unit-key\n")
            return result

        with patch.object(private.os, "read", side_effect=mutate):
            self.blocked()

    def arguments(self, backend="headless"):
        return ["start", "--workspace", str(self.root), "--plan-file", "plan.md",
                "--request-file", "request.json", "--backend", backend,
                "--maximum-rounds", "1", "--timeout-seconds", "1",
                "--no-progress-rounds", "3", "--backend-config", "backend.json",
                "--credential-file", self.relative]

    def test_cli_start_loads_only_inside_call_and_restores_environment(self):
        def unit_start(spec):
            self.assertEqual(os.environ[private.CREDENTIAL_NAME], SYNTHETIC_VALUE)
            self.assertFalse(hasattr(spec, "credential_file"))
            return {"status": "COMPLETED", "cleanup_ok": True}

        with patch.dict(os.environ, {}, clear=True), \
                patch.object(cli.loop, "start", side_effect=unit_start) as start, \
                patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(cli.main(self.arguments()), 0)
            start.assert_called_once()
            self.assertNotIn(private.CREDENTIAL_NAME, os.environ)
            self.assertNotIn(SYNTHETIC_VALUE, output.getvalue())

    def test_cli_local_verification_rejects_credentials_before_read(self):
        with patch.object(private, "_read_credential", side_effect=AssertionError("unexpected read")), \
                patch.object(cli.loop, "start") as start, patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(cli.main(self.arguments("local-verification")), 1)
            start.assert_not_called()

    def test_cli_status_stop_and_help_never_load_credentials(self):
        with patch.object(private, "_read_credential", side_effect=AssertionError("unexpected read")), \
                patch.object(cli.loop, "status", return_value={"status": "IDLE"}), \
                patch.object(cli.loop, "stop", return_value={"status": "SUSPENDED"}), \
                patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(cli.main(["status", "--workspace", str(self.root)]), 0)
            self.assertEqual(cli.main(["stop", "--workspace", str(self.root)]), 0)
            with self.assertRaises(SystemExit) as exit_result:
                cli.main(["--help"])
            self.assertEqual(exit_result.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
