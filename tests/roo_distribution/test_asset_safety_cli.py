"""通过有界子进程验证命令入口；所有部署目标均位于项目内沙箱。"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from deployment_source import REQUIRED_FILES


class CliSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="sandbox-", dir=Path(__file__).parent
        )
        self.addCleanup(self.temp.cleanup)
        self.sandbox = Path(self.temp.name)
        self.source = self.sandbox / "source with spaces"
        self.target = self.sandbox / "target with 'quote'"
        self.source.mkdir()
        self.target.mkdir()
        for relative in REQUIRED_FILES:
            path = self.source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fixture\n")
        (self.source / "plugin.json").write_bytes(b'{"name":"bmad-suite"}\n')
        (self.source / "roo/settings/custom_modes.yaml").write_bytes(
            b"customModes: [{slug: bmad-engineer, name: Engineer}]\n"
        )
        self.mode = "ide/settings/custom_modes.yaml"

    def run_cli(self, *options):
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts/deploy-managed-cli.py"),
             "--root", str(self.target), *options],
            cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True,
            text=True, timeout=10, env=environment,
        )

    def install(self, *options):
        return self.run_cli("--source", str(self.source),
                            "--mode-target", self.mode, *options)

    def tree(self):
        return {path.relative_to(self.target).as_posix():
                (path.read_bytes(), path.stat().st_mode)
                for path in self.target.rglob("*") if path.is_file()}

    def test_install_repeat_and_uninstall_preserve_personal_assets(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        rule = self.target / ".roo/rules/02-bmad-core.md"
        self.assertEqual(rule.read_bytes(), b"fixture\n")
        before = self.tree()
        repeated = self.install()
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual(self.tree(), before)
        personal = rule.parent / "personal.md"
        personal.write_bytes(b"keep personal")
        result = self.run_cli("--uninstall")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(rule.exists())
        self.assertEqual(personal.read_bytes(), b"keep personal")
        self.assertTrue((self.target / self.mode).is_file())

    def test_first_dry_run_has_no_target_side_effects(self):
        result = self.install("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_corrupt_yaml_fails_before_any_other_target_write(self):
        mode = self.target / self.mode
        mode.parent.mkdir(parents=True)
        mode.write_bytes(b"customModes: [")
        before = self.tree()
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.tree(), before)
        self.assertFalse((self.target / ".roo").exists())
        self.assertFalse((self.target / ".bmad-solo-deployment").exists())

    def test_mode_collision_requires_target_scoped_adoption(self):
        mode = self.target / self.mode
        mode.parent.mkdir(parents=True)
        original = b"theme: dark\ncustomModes: [{slug: bmad-engineer, name: Personal}]\n"
        mode.write_bytes(original)
        rejected = self.install()
        self.assertNotEqual(rejected.returncode, 0)
        self.assertEqual(mode.read_bytes(), original)
        accepted = self.install("--adopt-mode", self.mode + "=bmad-engineer")
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertIn(b"theme: dark", mode.read_bytes())
        self.assertIn(b"Engineer", mode.read_bytes())

    def test_invalid_uninstall_combination_has_no_side_effects(self):
        result = self.install("--uninstall")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.target.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
