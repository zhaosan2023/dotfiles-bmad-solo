"""显式版本静态契约与 V4 兼容；不代表 Roo 运行时行为。"""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "suite_contracts_validator", ROOT / "scripts/validate-roo-contracts.py"
)
contracts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contracts)


class SuiteContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="sandbox-suite-", dir=Path(__file__).parent
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for directory in ("bmad-suite-v4", "bmralph-suite-v5"):
            shutil.copytree(ROOT / directory, self.root / directory,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    def run_cli(self, *arguments):
        return subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts/validate-roo-contracts.py"),
             "--root", str(self.root), *arguments],
            cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True,
            text=True, timeout=10,
        )

    def test_each_suite_passes_separately(self):
        for suite in ("v4", "v5"):
            with self.subTest(suite=suite):
                result = self.run_cli("--suite", suite)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"PASS：{suite}", result.stdout)

    def test_missing_selected_v5_does_not_fall_back(self):
        shutil.rmtree(self.root / "bmralph-suite-v5")
        result = self.run_cli("--suite", "v5")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("PASS", result.stdout)
        self.assertEqual(self.run_cli("--suite", "v4").returncode, 0)

    def test_v5_checks_do_not_apply_to_v4(self):
        path = self.root / "bmad-suite-v4/roo/rules/02-bmad-core.md"
        path.write_text("# V4 隔离静态夹具\n", encoding="utf-8")
        result = self.run_cli("--suite", "v4")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_corrupt_v4_does_not_affect_explicit_v5(self):
        path = self.root / "bmad-suite-v4/roo/settings/custom_modes.yaml"
        path.write_text("customModes: [", encoding="utf-8")
        result = self.run_cli("--suite", "v5")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotEqual(self.run_cli("--suite", "v4").returncode, 0)

    def test_v5_cross_version_link_is_rejected(self):
        path = self.root / "bmralph-suite-v5/skills/bmad/SKILL.md"
        path.write_text(path.read_text(encoding="utf-8") +
                        "\n[错误依赖](../../../../bmad-suite-v4/plugin.json)\n",
                        encoding="utf-8")
        result = self.run_cli("--suite", "v5")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("不得引用旧套件路径", result.stderr)

    def test_missing_v5_navigation_target_is_rejected(self):
        path = self.root / "bmralph-suite-v5/skills/bmad/SKILL.md"
        path.write_text(path.read_text(encoding="utf-8") +
                        "\n[不存在](references/missing.md)\n", encoding="utf-8")
        result = self.run_cli("--suite", "v5")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("导航目标不存在", result.stderr)

    def test_dual_platform_drift_is_rejected(self):
        path = self.root / "bmralph-suite-v5/rules/bmad-core.md"
        path.write_text(path.read_text(encoding="utf-8") + "\n额外职责\n", encoding="utf-8")
        result = self.run_cli("--suite", "v5")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("正文不一致", result.stderr)

    def test_v5_required_capabilities_cannot_be_removed(self):
        source = self.root / "bmralph-suite-v5"
        required = (
            "skills/bmad/references/capability-map.md",
            "skills/bmad/references/procedures/build.md",
            "skills/bmad/references/procedures/code-review.md",
            "skills/bmad/references/procedures/three-pass-analysis.md",
        )
        for relative in required:
            with self.subTest(relative=relative):
                path = source / relative
                original = path.read_bytes()
                try:
                    path.unlink()
                    result = self.run_cli("--suite", "v5")
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn("PASS", result.stdout)
                    self.assertEqual(self.run_cli("--suite", "v4").returncode, 0)
                finally:
                    path.write_bytes(original)

    def test_v5_dual_entries_navigate_to_local_capabilities(self):
        source = self.root / "bmralph-suite-v5"
        engineer = (source / "skills/bmad/SKILL.md").read_text(encoding="utf-8")
        analyst = (source / "skills/ana-solo/SKILL.md").read_text(encoding="utf-8")
        for target in (
            "references/capability-map.md",
            "references/procedures/build.md",
            "references/procedures/code-review.md",
        ):
            self.assertIn(f"]({target})", engineer)
        for target in (
            "../bmad/references/capability-map.md",
            "../bmad/references/procedures/three-pass-analysis.md",
        ):
            self.assertIn(f"]({target})", analyst)
        for path in (source / "skills/bmad/references/procedures").glob("*.md"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("brain/task.md", text)
            self.assertNotIn("brain/implementation_plan.md", text)
        result = self.run_cli("--suite", "v5")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_v5_identity_cannot_claim_v4(self):
        path = self.root / "bmralph-suite-v5/suite.json"
        path.write_text(path.read_text(encoding="utf-8").replace('"v5"', '"v4"'),
                        encoding="utf-8")
        result = self.run_cli("--suite", "v5")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("身份字段", result.stderr)


if __name__ == "__main__":
    unittest.main()
