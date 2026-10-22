"""唯一 V4 静态契约、缺源和退役拒绝；不代表宿主行为。"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class SuiteContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sandbox-suite-", dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "bmad-suite-v4", self.root / "bmad-suite-v4")

    def run_cli(self, *arguments):
        return subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts/validate-roo-contracts.py"),
             "--root", str(self.root), *arguments],
            cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=10,
        )

    def test_v4_and_default_pass(self):
        for arguments in ((), ("--suite", "v4")):
            with self.subTest(arguments=arguments):
                result = self.run_cli(*arguments)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("PASS：v4", result.stdout)

    def test_retired_or_unknown_suite_rejected_without_fallback(self):
        for version in ("v3", "v5", "latest", ""):
            with self.subTest(version=version):
                result = self.run_cli("--suite", version)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("PASS", result.stdout)

    def test_missing_v4_does_not_use_generic_source(self):
        (self.root / "bmad-suite-v4").rename(self.root / "bmad-suite")
        result = self.run_cli("--suite", "v4")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("PASS", result.stdout)

    def test_corrupt_v4_modes_rejected(self):
        (self.root / "bmad-suite-v4/roo/settings/custom_modes.yaml").write_text("customModes: [", encoding="utf-8")
        result = self.run_cli("--suite", "v4")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("PASS", result.stdout)

    def test_missing_rule_and_skill_rejected(self):
        for relative in ("roo/rules/02-bmad-core.md", "skills/bmad/SKILL.md"):
            path = self.root / "bmad-suite-v4" / relative
            original = path.read_bytes()
            try:
                path.unlink()
                result = self.run_cli()
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("PASS", result.stdout)
            finally:
                path.write_bytes(original)

    def test_explicit_missing_plan_never_uses_default(self):
        result = self.run_cli("--plan", "missing-plan.md")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("PASS", result.stdout)


if __name__ == "__main__":
    unittest.main()
