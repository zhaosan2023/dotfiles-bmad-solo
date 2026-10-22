"""V4 返修的静态回归；不执行探针、计划命令或真实宿主部署。

检查入口文字、权限配置、模板契约和报告导航，不证明模型行为、
执行级隔离、宿主加载或效率提升。文件读取只用于测试断言。
"""
import copy
import importlib.util
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / "bmad-suite-v4"
SPEC = importlib.util.spec_from_file_location(
    "v4_repair_contracts", ROOT / "scripts/validate-roo-contracts.py"
)
contracts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contracts)

ANALYSIS_PATHS = (
    "skills/ana-solo/SKILL.md",
    "roo/rules-ana-architect/01-ana-solo-core.md",
    "skills/ana-solo/references/convergence-locks.md",
    "skills/ana-solo/references/paper-reading-guide.md",
    "skills/bmad/references/mode-analyst.md",
    "skills/bmad/references/procedures/three-pass-analysis.md",
)
TEMPLATE = "skills/bmad/references/templates/implementation-plan.template.md"
REPORT = ROOT / "_bmad-output/analysis/ANALYSIS-20261021-v4-backpressure-repair.md"
ORIGINAL = ROOT / "docs/Ralph-Wiggum-Loop/dr_dm_v4_backpressure_optimization.md"


def text(relative):
    return (SUITE / relative).read_text(encoding="utf-8")


class V4AnalysisRepair(unittest.TestCase):
    def test_analysis_configuration_does_not_grant_terminal_or_scratch_edit(self):
        data = contracts.load_yaml(text("roo/settings/custom_modes.yaml"))
        contracts.validate_modes(data)
        analyst = next(mode for mode in data["customModes"]
                       if mode["slug"] == "ana-architect")
        groups = analyst["groups"]
        names = [group if isinstance(group, str) else group[0]
                 for group in groups]
        self.assertEqual(set(names), {"read", "edit", "browser"})
        pattern = re.compile(next(group[1]["fileRegex"] for group in groups
                                  if isinstance(group, list)))
        for path in (
            "_bmad-output/scratch/probe.py",
            "_bmad-output/scratch/probe.md",
            "docs/Ralph-Wiggum-Loop/decision.md",
            "src/production.md",
            "_bmad-output/project-context.md",
        ):
            with self.subTest(path=path):
                self.assertIsNone(pattern.search(path))
        instructions = analyst["customInstructions"]
        for token in ("不运行终端", "不创建或执行探针", "只读任务仅会话交付",
                      "获准工程入口", "不自动切换"):
            self.assertIn(token, instructions)

    def test_analysis_references_preserve_read_only_and_experiment_handoff(self):
        for relative in ANALYSIS_PATHS:
            with self.subTest(path=relative):
                content = text(relative)
                self.assertIn("不使用终端", content)
                self.assertIn("不创建或执行探针", content)
                self.assertIn("只读任务", content)
                self.assertIn("会话交付", content)
                self.assertIn("获准工程入口", content)
                self.assertIn("不自动", content)
                for obsolete in (
                    "MUST explicitly state at least 3 Non-Goals",
                    "Mandate at least 3 out-of-scope",
                    "Must explicitly state at least **3 items",
                    "Top-3 Hidden Assumptions",
                    "Top-3 Failure Scenarios",
                    "Proceed immediately to `/bmad-solo`",
                    "Action: Stop analysis. Begin implementation",
                    "只读状态自主探查权（免提示放行）",
                    "草稿区探针验证权 (Scratchpad Probe",
                ):
                    self.assertNotIn(obsolete, content)

    def test_dual_entries_keep_evidence_and_nonmechanical_convergence(self):
        for relative in ANALYSIS_PATHS[:2]:
            with self.subTest(path=relative):
                content = text(relative)
                for token in ("三遍阅读", "第一遍", "第二遍", "第三遍",
                              "不固定", "反证", "未知", "不编造", "不等于"):
                    self.assertIn(token, content)
                self.assertIn("不按", content)
                self.assertNotIn("verification_type: footprint_property", content)
                self.assertNotIn("uv run pytest tests/test_footprint.py", content)

    def test_skill_uses_existing_suite_local_template(self):
        skill = text("skills/ana-solo/SKILL.md")
        target = "../bmad/references/templates/implementation-plan.template.md"
        self.assertIn("](" + target + ")", skill)
        linked = (SUITE / "skills/ana-solo" / target).resolve(strict=True)
        self.assertTrue(linked.is_relative_to(SUITE.resolve()))
        self.assertEqual(linked, (SUITE / TEMPLATE).resolve())
        data = contracts.frontmatter(text(TEMPLATE))
        contracts.validate_plan(data, ROOT, template=True)
        with self.assertRaises(contracts.ContractError):
            contracts.validate_plan(data, ROOT)
        instantiated = {
            **data,
            "plan_id": "V4-REPAIR-STATIC-FIXTURE",
            "requires_adr": False,
            "adr_file": None,
            "verification_command": "timeout 30s python3 -B check.py < /dev/null",
            "verification_command_status": "PLANNED_NOT_YET_CREATED",
            "authorization": "仅内存中的静态契约测试，不执行命令",
        }
        contracts.validate_plan(instantiated, ROOT)
        self.assertIsNone(instantiated["session_id"])
        invalid = copy.deepcopy(instantiated)
        invalid["verification_type"] = "footprint_property"
        with self.assertRaises(contracts.ContractError):
            contracts.validate_plan(invalid, ROOT)

    def test_engineering_mode_preserves_progress_and_closure_authorization(self):
        data = contracts.load_yaml(text("roo/settings/custom_modes.yaml"))
        engineer = next(mode for mode in data["customModes"]
                        if mode["slug"] == "bmad-engineer")
        instructions = engineer["customInstructions"]
        for token in (
            "任务清单", "只读视图", "未实现或未覆盖", "平台任务记录",
            "字节预算", "全部未完成事项", "取得转正授权",
            "取得相应写入授权", "全计划完成且获准归档",
            "源已变化则保留源",
        ):
            self.assertIn(token, instructions)

    def test_progress_is_single_source_and_closure_requires_authorization(self):
        for relative in (
            "rules/bmad-core.md",
            "skills/bmad/SKILL.md",
            "roo/rules/02-bmad-core.md",
            "roo/rules-bmad-engineer/01-bmad-engineer-core.md",
            TEMPLATE,
        ):
            with self.subTest(path=relative):
                content = text(relative)
                for token in (
                    "任务清单", "只读视图", "未实现或未覆盖",
                    "平台任务记录", "字节", "全计划完成", "获准归档",
                ):
                    self.assertIn(token, content)
                self.assertRegex(content, r"转正[^\n]*授权|授权[^\n]*转正")

    def test_algorithm_procedure_preserves_routing_and_experiment_authorization(self):
        content = text("skills/bmad/references/procedures/algorithm-fit.md")
        for token in (
            "仅 `algo` 场景", "`structural`", "`bugfix`", "`ops`",
            "只读任务", "会话交付", "不写契约", "不运行验证",
            "不使用终端", "不创建或执行探针", "复用绑定计划",
            "已获文档写入授权", "问题、范围、环境前提与验收",
            "获准工程入口", "不自动切换模式或启动实验",
            "仅阻塞依赖该依据的任务",
        ):
            with self.subTest(token=token):
                self.assertIn(token, content)
        self.assertNotIn("you MUST switch to experiment/spike mode", content)
        self.assertNotIn("Create the contract at", content)
        target = "../contracts/algorithm-contract.template.md"
        self.assertIn("](" + target + ")", content)
        procedure = SUITE / "skills/bmad/references/procedures/algorithm-fit.md"
        self.assertEqual(
            (procedure.parent / target).resolve(strict=True),
            (SUITE / "skills/bmad/references/contracts/algorithm-contract.template.md").resolve(),
        )

    def test_readme_closure_has_independent_authorization_gates(self):
        content = (ROOT / "README.md").read_text(encoding="utf-8")
        closure = next(line for line in content.splitlines()
                       if line.startswith("  * **完工对账**"))
        for token in (
            "阶段通过不等于全计划完成", "绑定契约要求关联 ADR",
            "全部必需门禁通过且取得转正授权",
            "仅取得相应写入授权", "阶段交付不自动更新事实基线",
            "仅全计划完成且获准归档", "目标包含时间和计划标识",
            "禁止覆盖", "复核源标识与内容版本",
            "失败或源已变化则保留源", "不清理无关任务",
            "必需运行时证据缺失", "不以静态测试或自治裁决替代验收",
        ):
            with self.subTest(token=token):
                self.assertIn(token, closure)
        self.assertIn("不附加算法检查或无关业务测试", content)
        self.assertIn("属性测试与缺陷回归互补，不按比例删测", content)
        self.assertNotIn("强制 Epic 物理单测阻断", content)

    def test_ci_explicitly_collects_v4_distribution_regression(self):
        config = contracts.load_yaml(
            (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        )
        steps = config["jobs"]["test-physical-mirror-install"]["steps"]
        matches = [step for step in steps
                   if step.get("name") == "Test V4 Analysis Repair Distribution"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(
            matches[0]["run"],
            "timeout 30s python3 -B -m unittest discover "
            "-s tests/roo_distribution -p 'test_v4_analysis_distribution.py' < /dev/null",
        )
        self.assertTrue(
            (ROOT / "tests/roo_distribution/test_v4_analysis_distribution.py").is_file()
        )

    def test_conditional_reconciliation_cannot_waive_required_acceptance(self):
        content = text("skills/bmad/references/procedures/state-reconcile.md")
        conditional = next(line for line in content.splitlines()
                           if line.startswith("- CONDITIONALLY_CONSISTENT："))
        self.assertIn("不得豁免必需验收或作为完成绿灯", conditional)
        self.assertNotIn("Only `CONSISTENT` or `CONDITIONALLY_CONSISTENT`", content)
        self.assertIn("全计划完成", content)

    def test_retired_report_links_to_corrected_analysis_without_erasing_body(self):
        original = ORIGINAL.read_text(encoding="utf-8")
        header = original.split("---", 1)[0]
        self.assertIn("已退役，不作为规范", header)
        self.assertIn("不作为有效规范、授权、性能基线或验收证据", header)
        target = "../../_bmad-output/analysis/ANALYSIS-20261021-v4-backpressure-repair.md"
        self.assertIn("](" + target + ")", header)
        self.assertEqual((ORIGINAL.parent / target).resolve(strict=True), REPORT.resolve())
        self.assertIn("## 五、 DM (Decision Matrix)", original)
        self.assertIn("## 六、 结论与落地清单", original)
        corrected = REPORT.read_text(encoding="utf-8")
        for token in ("71.0", "55.0", "定性比较", "不登记测试通过",
                      "不证明运行绑定或在途进程已经结束"):
            self.assertIn(token, corrected)


if __name__ == "__main__":
    unittest.main()
