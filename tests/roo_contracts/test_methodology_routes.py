"""目标项目产物路由与旧消费者兼容的静态回归，不证明宿主加载。

只读取当前套件和检查模板形状；不执行任务、迁移资产或登记事实。
"""
from pathlib import Path
import re
import unittest

import test_contracts as fixtures


ROOT = fixtures.ROOT
SUITE = ROOT / "bmad-suite-v4"
contracts = fixtures.contracts


def text(relative):
    return (SUITE / relative).read_text(encoding="utf-8")


class MethodologyRoutes(unittest.TestCase):
    def test_analysis_entries_use_target_project_routes(self):
        for relative in (
            "skills/ana-solo/SKILL.md",
            "roo/rules-ana-architect/01-ana-solo-core.md",
        ):
            with self.subTest(relative=relative):
                content = text(relative)
                for route in (
                    "docs/analysis/ANALYSIS-YYYYMMDD-[topic].md",
                    "docs/adrs/ADR-YYYYMMDD-[topic].md",
                    "specs/tasks/TU-<task_id>.md",
                ):
                    self.assertIn(route, content)
                self.assertNotIn("默认候选为 `_bmad-output/pending_implementation_plan.md`", content)
                self.assertIn("不混合", content)
                self.assertIn("不自动写活动指针", content)
                self.assertIn("不使用终端", content)
                self.assertIn("只读任务", content)

    def test_analysis_skill_links_both_templates_inside_suite(self):
        relative = "skills/ana-solo/SKILL.md"
        content = text(relative)
        links = re.findall(r"\]\(([^)]+template\.md)\)", content)
        expected = {
            "../bmad/references/templates/task-unit.template.md",
            "../bmad/references/templates/implementation-plan.template.md",
        }
        self.assertEqual(set(links), expected)
        for link in links:
            with self.subTest(link=link):
                path = (SUITE / relative).parent / link
                resolved = path.resolve(strict=True)
                self.assertTrue(resolved.is_file())
                self.assertTrue(resolved.is_relative_to(SUITE.resolve()))
        task = contracts.frontmatter(text("skills/bmad/references/templates/task-unit.template.md"))
        contracts.validate_task(task, template=True)
        with self.assertRaises(contracts.ContractError):
            contracts.validate_task(task)

    def test_core_output_routes_do_not_create_parallel_legacy_plan(self):
        content = text("rules/bmad-core.md")
        output = content.split("## 第 4.5 章", 1)[1]
        for route in (
            "specs/tasks/TU-<task_id>.md", "specs/tasks/_active.md",
            "docs/analysis/ANALYSIS-YYYYMMDD-[topic].md",
            "docs/adrs/ADR-YYYYMMDD-[topic].md", "docs/project-context.md",
        ):
            self.assertIn(route, output)
        self.assertIn("不默认创建旧暂存计划", output)
        self.assertIn("第二份计划", output)
        self.assertIn("保留消费者兼容", output)
        self.assertIn("不能只改文档路径便宣称迁移完成", output)
        self.assertNotIn("新 ADR 默认位于 `_bmad-output/adrs/`", output)
        self.assertNotIn("默认候选为 `_bmad-output/pending_implementation_plan.md`", output)
        self.assertIn("平台任务记录及真实回执", output)

    def test_constitutions_agree_on_fact_read_fallback(self):
        for relative in (
            "rules/bmad-constitution.md",
            "roo/rules/01-bmad-constitution.md",
        ):
            with self.subTest(relative=relative):
                content = text(relative)
                self.assertIn("docs/project-context.md", content)
                self.assertIn("仅新基线不存在时兼容旧", content)
                self.assertIn("损坏或来源冲突不静默换源", content)

    def test_architecture_decision_is_authorized_proposal_not_automatic_promotion(self):
        content = text("skills/bmad/references/procedures/architecture-decision.md")
        self.assertIn("docs/adrs/ADR-YYYYMMDD-[topic].md", content)
        self.assertIn("只读讨论仅取证与会话交付", content)
        self.assertIn("不运行验证", content)
        self.assertIn("既有记录保留原路径", content)
        self.assertIn("保留消费者兼容", content)
        self.assertIn("取得转正授权", content)
        self.assertIn("缺必需运行时证据保持 PROPOSED", content)
        self.assertNotIn("Save the result to `_bmad-output/architecture/decisions/", content)
        self.assertNotIn("you must update `_bmad-output/", content)
        self.assertIn("## Status\nPROPOSED", content)

    def test_new_analysis_outputs_match_declared_edit_contract(self):
        modes = fixtures.source_modes()
        contracts.validate_modes(modes)
        analyst = next(mode for mode in modes["customModes"]
                       if mode["slug"] == "ana-architect")
        pattern = re.compile(next(group[1]["fileRegex"] for group in analyst["groups"]
                                  if isinstance(group, list)))
        for relative in (
            "docs/analysis/ANALYSIS-20261103-routes.md",
            "docs/adrs/ADR-20261103-routes.md",
            "specs/tasks/TU-ROUTES-001.md",
        ):
            with self.subTest(relative=relative):
                self.assertIsNotNone(pattern.search(relative))
        for relative in (
            "specs/tasks/_active.md", "docs/project-context.md",
            "specs/governance/02-task-unit-schema.md",
        ):
            with self.subTest(relative=relative):
                self.assertIsNone(pattern.search(relative))


if __name__ == "__main__":
    unittest.main()
