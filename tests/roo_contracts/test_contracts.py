"""静态契约回归测试；不代表 Roo 运行时权限或模型行为验收。"""
import copy
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "roo_contracts", ROOT / "scripts/validate-roo-contracts.py"
)
contracts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contracts)


def source_modes():
    return contracts.load_yaml((ROOT / contracts.MODE_PATH).read_text(encoding="utf-8"))


class ModeContracts(unittest.TestCase):
    def test_actual_modes(self):
        contracts.validate_modes(source_modes())

    def test_duplicate_yaml_keys(self):
        for text in ("customModes: []\ncustomModes: []", "a: {slug: x, slug: y}"):
            with self.subTest(text=text), self.assertRaises(contracts.ContractError):
                contracts.load_yaml(text)

    def test_invalid_yaml_structure(self):
        for text in ("", "[]", "null", "42"):
            with self.subTest(text=text), self.assertRaises(contracts.ContractError):
                contracts.load_yaml(text)

    def test_duplicate_mode(self):
        data = source_modes()
        data["customModes"].append(copy.deepcopy(data["customModes"][0]))
        with self.assertRaises(contracts.ContractError):
            contracts.validate_modes(data)

    def test_analyst_privilege_escalations(self):
        for group in ("command", "mcp", "edit"):
            data = source_modes()
            data["customModes"][0]["groups"][1] = group
            with self.subTest(group=group), self.assertRaises(contracts.ContractError):
                contracts.validate_modes(data)

    def test_overbroad_and_end_anchor_regex_rejected(self):
        for regex in (".*", r"^_bmad-output/.*\.md$",
                      r"^_bmad-output/(?:(?:adrs|analysis|archive/plans)/[A-Za-z0-9_-]+\.md|pending_implementation_plan\.md)$"):
            data = source_modes()
            data["customModes"][0]["groups"][1][1]["fileRegex"] = regex
            with self.subTest(regex=regex), self.assertRaises(contracts.ContractError):
                contracts.validate_modes(data)

    def test_engineer_requires_command_permission(self):
        data = source_modes()
        data["customModes"][1]["groups"].remove("command")
        with self.assertRaises(contracts.ContractError):
            contracts.validate_modes(data)

    def test_frontmatter_errors(self):
        for text in ("title", "---\nstatus: READY", "---\nstatus: READY\nstatus: IDLE\n---"):
            with self.subTest(text=text), self.assertRaises(contracts.ContractError):
                contracts.frontmatter(text)


class RepositoryContracts(unittest.TestCase):
    def setUp(self):
        # 所有夹具留在项目内；不触碰真实全局配置或实际活动计划。
        self.temp = tempfile.TemporaryDirectory(prefix="sandbox-", dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for relative in (contracts.MODE_PATH, contracts.TEMPLATE_PATH,
                         *contracts.RULE_PATHS, *contracts.SKILL_PATHS):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        self.plan = {
            "plan_id": "test-plan", "status": "READY_FOR_IMPLEMENTATION",
            "scenario": "structural", "impact_tier": "M", "requires_adr": False,
            "adr_file": None, "verification_type": "config_syntax",
            "verification_command": "timeout 30s python3 scripts/validate-roo-contracts.py < /dev/null",
            "verification_command_status": "AVAILABLE",
            "authorization": "仅隔离夹具静态校验", "session_id": None,
        }

    def write_plan(self, relative, data=None):
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("---\n" + yaml.safe_dump(self.plan if data is None else data)
                          + "---\n# 隔离测试计划\n", encoding="utf-8")
        return target

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate-roo-contracts.py"),
             "--root", str(self.root), *args],
            cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True,
            text=True, timeout=10,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

    def test_missing_default_is_normal(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("正常生命周期状态", result.stdout)

    def test_explicit_plan_skips_corrupt_default(self):
        default = self.write_plan(contracts.DEFAULT_PLAN)
        default.write_text("损坏的暂存计划", encoding="utf-8")
        explicit = "_bmad-output/archive/plans/selected.md"
        self.write_plan(explicit)
        result = self.run_cli("--plan", explicit)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(default.read_text(encoding="utf-8"), "损坏的暂存计划")

    def test_missing_explicit_does_not_fall_back(self):
        self.write_plan(contracts.DEFAULT_PLAN)
        result = self.run_cli("--plan", "missing.md")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("PASS", result.stdout)

    def test_corrupt_default_fails_closed(self):
        target = self.write_plan(contracts.DEFAULT_PLAN)
        target.write_bytes(b"---\nstatus: [\n---\n")
        before = target.read_bytes()
        self.assertNotEqual(self.run_cli().returncode, 0)
        self.assertEqual(target.read_bytes(), before)

    def test_every_required_field(self):
        for field in contracts.FIELDS:
            data = dict(self.plan)
            del data[field]
            with self.subTest(field=field), self.assertRaises(contracts.ContractError):
                contracts.validate_plan(data, self.root)

    def test_invalid_metadata(self):
        variants = {
            "scenario": "unknown", "impact_tier": "XL", "status": "PASSED",
            "requires_adr": "false", "session_id": [], "authorization": "",
            "verification_command_status": "PASSED", "verification_type": "anything",
            "plan_id": "../other", "verification_command": "python3 check.py",
        }
        for field, value in variants.items():
            data = {**self.plan, field: value}
            with self.subTest(field=field), self.assertRaises(contracts.ContractError):
                contracts.validate_plan(data, self.root)

    def test_adr_reference_required(self):
        data = {**self.plan, "requires_adr": True, "adr_file": "_bmad-output/adrs/missing.md"}
        with self.assertRaises(OSError):
            contracts.validate_plan(data, self.root)
        target = self.root / data["adr_file"]
        target.parent.mkdir(parents=True)
        target.write_text("# ADR\nStatus: PROPOSED\n", encoding="utf-8")
        contracts.validate_plan(data, self.root)

    def test_reference_traversal_rejected(self):
        for path in ("../outside.md", str(ROOT / "bs.sh")):
            with self.subTest(path=path), self.assertRaises(contracts.ContractError):
                contracts.project_file(self.root, path)

    def test_reference_symlink_escape_rejected(self):
        (self.root / "escape.md").symlink_to(ROOT / "bs.sh")
        with self.assertRaises(contracts.ContractError):
            contracts.project_file(self.root, "escape.md")

    def test_template_is_not_executable_plan(self):
        data = contracts.frontmatter((self.root / contracts.TEMPLATE_PATH).read_text(encoding="utf-8"))
        contracts.validate_plan(data, self.root, template=True)
        with self.assertRaises(contracts.ContractError):
            contracts.validate_plan(data, self.root)

    def test_validation_does_not_execute_command(self):
        marker = self.root / "must-not-exist"
        data = {**self.plan, "verification_command": f"timeout 15s touch {marker} < /dev/null"}
        self.write_plan(contracts.DEFAULT_PLAN, data)
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
