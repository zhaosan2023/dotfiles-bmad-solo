"""验证实际 Shell 部署与卸载调用链；仅向项目内沙箱写入。

不传更新、标签或分支切换参数，不修改真实 Git 引用或全局配置。
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from asset_safety import deployment_lock
MODE = (
    ".vscode-server/data/User/globalStorage/"
    "rooveterinaryinc.roo-cline/settings/custom_modes.yaml"
)


class ShellEntrySafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="sandbox-shell-", dir=Path(__file__).parent
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "isolated home"
        self.target = self.root / "target with 'quote'"
        self.home.mkdir()
        self.target.mkdir()
        self.mode = self.target / MODE
        self.mode.parent.mkdir(parents=True)
        self.mode.write_bytes(
            b"theme: dark\ncustomModes: [{slug: personal, name: Personal}]\n"
        )

    def run_shell(self, *arguments):
        environment = dict(os.environ)
        environment.update({
            "HOME": str(self.home),
            "BMAD_DEPLOY_ROOT": str(self.target),
            "PYTHONDONTWRITEBYTECODE": "1",
            "GIT_TERMINAL_PROMPT": "0",
        })
        return subprocess.run(
            ["bash", str(ROOT / "bs.sh"), *arguments],
            cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=15,
        )

    def tree(self):
        result = {}
        for path in self.target.rglob("*"):
            relative = path.relative_to(self.target).as_posix()
            result[relative] = (
                "directory" if path.is_dir() else path.read_bytes(),
                path.stat().st_mode,
            )
        return result

    def test_install_idempotence_and_managed_uninstall(self):
        installed = self.run_shell()
        self.assertEqual(installed.returncode, 0, installed.stderr)
        managed = self.target / ".roo/rules/02-bmad-core.md"
        source = ROOT / "bmad-suite-v4/roo/rules/02-bmad-core.md"
        self.assertEqual(managed.read_bytes(), source.read_bytes())
        self.assertIn(b"personal", self.mode.read_bytes())
        self.assertIn(b"theme: dark", self.mode.read_bytes())
        self.assertNotIn("successfully activated!", installed.stdout)
        before = self.tree()
        repeated = self.run_shell()
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual(self.tree(), before)
        personal = managed.parent / "personal.md"
        personal.write_bytes(b"user-owned rule")
        removed = self.run_shell("--uninstall")
        self.assertEqual(removed.returncode, 0, removed.stderr)
        self.assertFalse(managed.exists())
        self.assertEqual(personal.read_bytes(), b"user-owned rule")
        self.assertIn(b"personal", self.mode.read_bytes())
        self.assertNotIn(b"bmad-engineer", self.mode.read_bytes())
        self.assertEqual(list(self.home.iterdir()), [])

    def test_dry_run_preserves_entire_target_tree(self):
        before = self.tree()
        result = self.run_shell("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.tree(), before)
        self.assertNotIn("successfully activated!", result.stdout)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_corrupt_yaml_blocks_plugin_and_rule_writes(self):
        self.mode.write_bytes(b"customModes: [")
        before = self.tree()
        result = self.run_shell()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.tree(), before)
        self.assertFalse((self.target / ".gemini").exists())
        self.assertFalse((self.target / ".roo").exists())
        self.assertFalse((self.target / ".bmad-solo-deployment").exists())
        self.assertEqual(list(self.home.iterdir()), [])

    def test_modified_managed_file_blocks_shell_uninstall(self):
        installed = self.run_shell()
        self.assertEqual(installed.returncode, 0, installed.stderr)
        managed = self.target / ".roo/rules/02-bmad-core.md"
        managed.write_bytes(b"user modification")
        before = self.tree()
        result = self.run_shell("--uninstall")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.tree(), before)
        self.assertEqual(list(self.home.iterdir()), [])


    def test_shell_install_and_uninstall_reject_another_process_lock(self):
        installed = self.run_shell()
        self.assertEqual(installed.returncode, 0, installed.stderr)
        before = self.tree()
        lock = self.target / ".bmad-solo-deployment/deployment.lock"
        # 父进程持锁，顺序启动真实 Shell 子进程，验证跨进程拒绝而非仅同进程重入。
        with deployment_lock(lock):
            for arguments in ((), ("--uninstall",)):
                with self.subTest(arguments=arguments):
                    result = self.run_shell(*arguments)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("另一部署进程持有锁", result.stderr)
                    self.assertEqual(self.tree(), before)
        repeated = self.run_shell()
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual(self.tree(), before)
        self.assertEqual(list(self.home.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
