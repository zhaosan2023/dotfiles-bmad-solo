"""安装依赖的失败关闭回归；不联网、不安装包、不部署真实宿主。

在项目内夹具中控制命令发现与 Python 导入，核对副作用前置边界。
"""
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class InstallDependencies(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="sandbox-install-deps-", dir=Path(__file__).parent,
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.home = self.root / "home"
        self.home.mkdir()
        self.target = self.root / "deployment"
        self.target.mkdir()
        self.repo = self.root / "repository"
        self.repo.mkdir()
        for name in ("bs.sh", "install.sh"):
            shutil.copy2(ROOT / name, self.repo / name)
        self.bash = shutil.which("bash")
        self.assertIsNotNone(self.bash)
        for name in ("bash", "dirname", "mkdir", "git", "timeout", "env", "python3"):
            actual = shutil.which(name)
            self.assertIsNotNone(actual, name)
            (self.bin / name).symlink_to(actual)
        self.log = self.root / "git-invocations"
        self.wrapper("git", f"printf '%s\\n' invoked >> '{self.log}'\nexit 81\n")
        self.env = dict(os.environ)
        for name in list(self.env):
            if name.startswith(("GIT_", "BMAD_", "PYTHON")):
                del self.env[name]
        self.env.update({
            "PATH": str(self.bin),
            "HOME": str(self.home),
            "BMAD_SOLO_DIR": str(self.root / "new checkout"),
            "BMAD_DEPLOY_ROOT": str(self.target),
            "PYTHONDONTWRITEBYTECODE": "1",
            "GIT_TERMINAL_PROMPT": "0",
        })

    def wrapper(self, name, body):
        path = self.bin / name
        if path.is_symlink() or path.exists():
            path.unlink()
        path.write_text(f"#!{self.bash}\n" + body, encoding="utf-8")
        path.chmod(0o700)

    def tree(self, root):
        return {
            path.relative_to(root).as_posix():
                ("directory" if path.is_dir() else path.read_bytes(),
                 path.stat().st_mode)
            for path in root.rglob("*")
        }

    def run_entry(self, entry, *arguments):
        return subprocess.run(
            [self.bash, str(self.repo / entry), *arguments], cwd=self.repo,
            env=self.env, stdin=subprocess.DEVNULL, capture_output=True,
            text=True, timeout=10,
        )

    def assert_blocked_without_side_effects(self, entry, diagnostic, *arguments):
        before = tuple(self.tree(path) for path in (self.repo, self.home, self.target))
        result = self.run_entry(entry, *arguments)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(diagnostic, result.stderr)
        self.assertFalse(self.log.exists(), "依赖失败不得调用 Git")
        self.assertFalse(Path(self.env["BMAD_SOLO_DIR"]).exists())
        self.assertEqual(tuple(self.tree(path) for path in
                               (self.repo, self.home, self.target)), before)
        return result

    def test_missing_programs_block_before_git_or_target_writes(self):
        for name in ("git", "timeout", "python3", "env"):
            executable = self.bin / name
            if executable.is_symlink():
                saved = ("link", str(executable.readlink()))
            else:
                saved = ("file", executable.read_bytes())
            executable.unlink()
            try:
                for entry in ("install.sh", "bs.sh"):
                    with self.subTest(dependency=name, entry=entry):
                        self.assert_blocked_without_side_effects(entry, name)
            finally:
                if saved[0] == "link":
                    executable.symlink_to(saved[1])
                else:
                    executable.write_bytes(saved[1])
                    executable.chmod(0o700)

    def test_non_gnu_timeout_is_rejected(self):
        self.wrapper("timeout", "printf '%s\\n' 'Unsupported timeout implementation'\n")
        for entry in ("install.sh", "bs.sh"):
            with self.subTest(entry=entry):
                self.assert_blocked_without_side_effects(entry, "GNU timeout")

    def test_missing_yaml_import_blocks_before_clone_or_deployment(self):
        modules = self.root / "missing-yaml"
        modules.mkdir()
        (modules / "yaml.py").write_text("raise ImportError('injected missing YAML')\n")
        self.env["PYTHONPATH"] = str(modules)
        for entry in ("install.sh", "bs.sh"):
            with self.subTest(entry=entry):
                self.assert_blocked_without_side_effects(entry, "PyYAML")
        self.assertFalse((modules / "__pycache__").exists())

    def test_missing_fcntl_blocks_before_clone_or_deployment(self):
        actual = str((self.bin / "python3").resolve())
        # 启动阶段可能已缓存 fcntl；在隔离子进程拦截实际导入请求，
        # 不依赖 PYTHONPATH 遮蔽，也不修改安装入口的真实预检正文。
        probe = (
            "import builtins, sys\n"
            "original = builtins.__import__\n"
            "def guarded(name, *arguments, **keywords):\n"
            "    if name == 'fcntl':\n"
            "        raise ImportError('injected missing fcntl')\n"
            "    return original(name, *arguments, **keywords)\n"
            "builtins.__import__ = guarded\n"
            "exec(sys.argv[1])\n"
        )
        self.wrapper("python3", "exec " + shlex.quote(actual)
                     + " -B -c " + shlex.quote(probe)
                     + " \"${@: -1}\" < /dev/null\n")
        for entry in ("install.sh", "bs.sh"):
            with self.subTest(entry=entry):
                self.assert_blocked_without_side_effects(entry, "fcntl")

    def test_python_below_minimum_blocks_before_clone_or_deployment(self):
        actual = str((self.bin / "python3").resolve())
        # 仅在隔离解释器中替换探测版本；仍执行入口传入的真实预检正文。
        self.wrapper("python3", "exec " + shlex.quote(actual)
                     + " -B -c 'import sys; sys.version_info = (3, 9, 18); "
                     + "exec(sys.argv[1])' \"${@: -1}\" < /dev/null\n")
        for entry in ("install.sh", "bs.sh"):
            with self.subTest(entry=entry):
                self.assert_blocked_without_side_effects(entry, "Python 3.10")

    def test_broken_yaml_parser_is_rejected(self):
        modules = self.root / "broken-yaml"
        modules.mkdir()
        (modules / "yaml.py").write_text(
            "class SafeLoader: pass\ndef safe_load(content): return {}\n",
        )
        self.env["PYTHONPATH"] = str(modules)
        for entry in ("install.sh", "bs.sh"):
            with self.subTest(entry=entry):
                self.assert_blocked_without_side_effects(entry, "解析能力异常")

    def test_python_probe_failure_and_timeout_are_not_success(self):
        for exit_code in (78, 124):
            self.wrapper("python3", f"printf '%s\\n' 'injected probe failure' >&2\nexit {exit_code}\n")
            for entry in ("install.sh", "bs.sh"):
                with self.subTest(exit_code=exit_code, entry=entry):
                    result = self.assert_blocked_without_side_effects(
                        entry, "injected probe failure",
                    )
                    self.assertEqual(result.returncode, exit_code)

    def test_help_and_invalid_parameters_do_not_require_dependencies(self):
        for name in ("git", "python3", "timeout"):
            (self.bin / name).unlink()
        for entry in ("install.sh", "bs.sh"):
            with self.subTest(entry=entry):
                help_result = self.run_entry(entry, "--help")
                self.assertEqual(help_result.returncode, 0, help_result.stderr)
                self.assertIn("V4", help_result.stdout)
                self.assert_blocked_without_side_effects(entry, "", "--unknown")
        self.assertFalse(self.log.exists())

    def test_status_dependency_failure_is_read_only(self):
        (self.bin / "python3").unlink()
        self.assert_blocked_without_side_effects("bs.sh", "python3", "--status")

    def test_dependency_success_reaches_git_but_does_not_claim_install_success(self):
        before = self.tree(self.target)
        result = self.run_entry("install.sh")
        self.assertEqual(result.returncode, 81, result.stdout + result.stderr)
        self.assertTrue(self.log.exists())
        self.assertFalse(Path(self.env["BMAD_SOLO_DIR"]).exists())
        self.assertEqual(self.tree(self.target), before)
        self.assertNotIn("受管资产处理完成", result.stdout)


if __name__ == "__main__":
    unittest.main()
