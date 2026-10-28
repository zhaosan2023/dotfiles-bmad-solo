"""治理契约的静态和隔离回归；不证明 Cline/Roo 运行时行为。

夹具仅在项目内创建临时文件，不执行计划命令或部署真实宿主。
"""
import copy
from pathlib import Path
import re
import unittest
from unittest import mock

import test_contracts as fixtures


ROOT = fixtures.ROOT
SUITE = ROOT / "bmad-suite-v4"
contracts = fixtures.contracts


class DocumentTestGovernance(unittest.TestCase):
    setUp = fixtures.RepositoryContracts.setUp
    write_plan = fixtures.RepositoryContracts.write_plan
    run_cli = fixtures.RepositoryContracts.run_cli

    def add_adr(self, relative):
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# 隔离 ADR\n\n状态：PROPOSED\n", encoding="utf-8")
        return target

    def associated_plan(self):
        primary = "_bmad-output/adrs/primary.md"
        supplemental = "_bmad-output/adrs/supplemental.md"
        self.add_adr(primary)
        self.add_adr(supplemental)
        return {**self.plan, "requires_adr": True, "adr_file": primary,
                "supplemental_adrs": [supplemental]}

    def test_existing_plan_without_supplemental_remains_valid(self):
        before = copy.deepcopy(self.plan)
        contracts.validate_plan(self.plan, self.root)
        self.assertEqual(self.plan, before)

    def test_optional_empty_supplemental_list_remains_valid(self):
        contracts.validate_plan({**self.plan, "supplemental_adrs": []}, self.root)

    def test_primary_and_supplemental_adrs_are_checked_without_mutation(self):
        data = self.associated_plan()
        before = copy.deepcopy(data)
        contents = {relative: (self.root / relative).read_bytes()
                    for relative in (data["adr_file"], *data["supplemental_adrs"])}
        contracts.validate_plan(data, self.root)
        self.assertEqual(data, before)
        for relative, content in contents.items():
            self.assertEqual((self.root / relative).read_bytes(), content)

    def test_supplemental_type_and_entries_fail_closed(self):
        data = self.associated_plan()
        for value in (None, {}, "adr.md", ("adr.md",), [None], [42], [[]], [""], [" "]):
            with self.subTest(value=value), self.assertRaises(contracts.ContractError):
                contracts.validate_plan({**data, "supplemental_adrs": value}, self.root)

    def test_duplicate_or_primary_repeated_as_supplemental_is_rejected(self):
        data = self.associated_plan()
        relative = data["supplemental_adrs"][0]
        for value in ([relative, relative], [data["adr_file"]]):
            with self.subTest(value=value), self.assertRaises(contracts.ContractError):
                contracts.validate_plan({**data, "supplemental_adrs": value}, self.root)

    def test_supplemental_cannot_bypass_no_adr_contract(self):
        relative = "_bmad-output/adrs/existing.md"
        self.add_adr(relative)
        with self.assertRaises(contracts.ContractError):
            contracts.validate_plan({**self.plan, "supplemental_adrs": [relative]}, self.root)

    def test_missing_supplemental_is_not_accepted(self):
        data = self.associated_plan()
        with self.assertRaises(OSError):
            contracts.validate_plan({**data, "supplemental_adrs": ["missing.md"]}, self.root)

    def test_supplemental_traversal_and_absolute_paths_are_rejected(self):
        data = self.associated_plan()
        for relative in ("../outside.md", str(ROOT / "README.md")):
            with self.subTest(relative=relative), self.assertRaises(contracts.ContractError):
                contracts.validate_plan({**data, "supplemental_adrs": [relative]}, self.root)

    def test_supplemental_directory_and_escaping_symlink_are_rejected(self):
        data = self.associated_plan()
        directory = self.root / "directory.md"
        directory.mkdir()
        (self.root / "escape.md").symlink_to(ROOT / "README.md")
        for relative in ("directory.md", "escape.md"):
            with self.subTest(relative=relative), self.assertRaises(contracts.ContractError):
                contracts.validate_plan({**data, "supplemental_adrs": [relative]}, self.root)

    def test_supplemental_permission_error_is_not_swallowed(self):
        data = self.associated_plan()
        actual = contracts.project_file

        def guarded(root, relative):
            if relative == data["supplemental_adrs"][0]:
                raise PermissionError("隔离权限拒绝")
            return actual(root, relative)

        with mock.patch.object(contracts, "project_file", side_effect=guarded):
            with self.assertRaises(PermissionError):
                contracts.validate_plan(data, self.root)

    def test_explicit_root_plan_skips_corrupt_default_without_writing_it(self):
        default = self.write_plan(contracts.DEFAULT_PLAN)
        default.write_bytes(b"---\nstatus: [\n---\n")
        explicit = "PLAN-governance-fixture.md"
        selected = self.write_plan(explicit, self.associated_plan())
        before = (default.read_bytes(), selected.read_bytes())
        result = self.run_cli("--plan", explicit)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("静态契约有效", result.stdout)
        self.assertEqual((default.read_bytes(), selected.read_bytes()), before)

    def test_missing_explicit_root_plan_never_falls_back(self):
        default = self.write_plan(contracts.DEFAULT_PLAN)
        before = default.read_bytes()
        result = self.run_cli("--plan", "PLAN-missing-fixture.md")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("PASS", result.stdout)
        self.assertEqual(default.read_bytes(), before)

    def test_invalid_supplemental_cli_returns_failure_and_preserves_sources(self):
        data = self.associated_plan()
        data["supplemental_adrs"] = ["missing.md"]
        selected = self.write_plan("PLAN-invalid-fixture.md", data)
        primary = self.root / data["adr_file"]
        before = (selected.read_bytes(), primary.read_bytes())
        result = self.run_cli("--plan", "PLAN-invalid-fixture.md")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAIL", result.stderr)
        self.assertNotIn("PASS", result.stdout)
        self.assertEqual((selected.read_bytes(), primary.read_bytes()), before)

    def test_associated_plan_validation_never_executes_its_command(self):
        data = self.associated_plan()
        marker = self.root / "must-not-exist"
        data["verification_command"] = f"timeout --kill-after=2s 15s touch {marker} < /dev/null"
        self.write_plan("PLAN-no-execution-fixture.md", data)
        result = self.run_cli("--plan", "PLAN-no-execution-fixture.md")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())

    def test_engineer_root_plan_does_not_expand_analyst_edit_permissions(self):
        modes = fixtures.source_modes()
        contracts.validate_modes(modes)
        analyst = next(mode for mode in modes["customModes"]
                       if mode["slug"] == "ana-architect")
        pattern = re.compile(next(group[1]["fileRegex"] for group in analyst["groups"]
                                  if isinstance(group, list)))
        self.assertIsNone(pattern.search("PLAN-governance-fixture.md"))
        for relative in contracts.ALLOWED_PATHS:
            with self.subTest(allowed=relative):
                self.assertIsNotNone(pattern.search(relative))
        for relative in contracts.DENIED_PATHS:
            with self.subTest(denied=relative):
                self.assertIsNone(pattern.search(relative))
        self.assertNotIn("command", analyst["groups"])


class GovernanceReferences(unittest.TestCase):
    def text(self, relative):
        return (SUITE / relative).read_text(encoding="utf-8")

    def test_dm_preserves_evidence_gates_and_removes_mechanical_scores(self):
        content = self.text("skills/ana-solo/references/decision-matrix.md")
        for token in ("硬门禁", "定性比较", "不编造权重或分数", "未知保持未知",
                      "最高分不能自动裁决", "DR", "只读任务仅会话交付", "获准工程入口"):
            with self.subTest(token=token):
                self.assertIn(token, content)
        for obsolete in ("Assign explicit percentage weights", "Screen strictly to",
                         "Clear winner with highest weighted score", "Output exactly:"):
            self.assertNotIn(obsolete, content)

    def test_capability_links_resolve_to_existing_suite_procedures(self):
        relative = "skills/bmad/references/capability-map.md"
        content = self.text(relative)
        links = re.findall(r"\]\((procedures/[^)]+\.md)\)", content)
        self.assertEqual(len(links), 12)
        self.assertEqual(len(set(links)), len(links))
        for link in links:
            with self.subTest(link=link):
                target = (SUITE / relative).parent / link
                resolved = target.resolve(strict=True)
                self.assertTrue(resolved.is_file())
                self.assertTrue(resolved.is_relative_to(SUITE.resolve()))
        self.assertNotIn("所有 M/L 编码任务", content)
        self.assertIn("只读任务仅会话交付", content)
        self.assertIn("持久产物另需授权", content)

    def test_engineering_references_preserve_adaptive_failure_contract(self):
        for relative in ("skills/bmad/SKILL.md", "skills/bmad/references/capability-map.md",
                         "skills/bmad/references/mode-developer.md",
                         "skills/bmad/references/procedures/build.md"):
            with self.subTest(relative=relative):
                content = self.text(relative)
                for token in ("场景", "预算", "依赖", "重检", "授权", "证据"):
                    self.assertIn(token, content)
                self.assertNotIn("启用 Epic 单测物理背压阻断", content)
                self.assertNotIn("Implement ONLY when Architecture Preflight", content)
        router = self.text("skills/bmad/SKILL.md")
        for token in ("场景决定验证类型，实际影响范围决定深度",
                      "旧证据不能批准已变化的候选", "不是已实现的程序拦截",
                      "摘要不代替唯一原始回执", "不进入全局方法论分发"):
            self.assertIn(token, router)
        build = self.text("skills/bmad/references/procedures/build.md")
        self.assertIn("独立事项是否继续按依赖、授权及资源边界判断", build)
        self.assertIn("阶段完成不等于全计划完成", build)


if __name__ == "__main__":
    unittest.main()
