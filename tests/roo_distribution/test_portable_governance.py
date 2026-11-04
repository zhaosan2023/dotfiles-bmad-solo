"""可分发治理依据的引用闭包与隔离部署；不扫描真实棕地项目。

仅验证套件资产及候选契约，不证明宿主加载、引擎执行或独立批准。
"""
import json
from pathlib import Path
import re
import unittest

import test_asset_safety_cli as fixtures
from deployment_source import collect_source, verify_source


ROOT = fixtures.ROOT
SUITE = ROOT / "bmad-suite-v4"
PROCEDURE = "skills/bmad/references/procedures/brownfield-distill-governance.md"
CONTRACT = "skills/bmad/references/governance-contract.md"
TEMPLATE = "skills/bmad/references/templates/task-unit.template.md"
PLUGIN = ".gemini/config/plugins/bmad-suite/"
LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def reference_closure(root, entry):
    """从指定入口检查真实文件与行定位；不把目标槽位当作套件文件。"""
    root = root.resolve(strict=True)
    pending = [entry]
    visited = set()
    while pending:
        relative = pending.pop()
        if relative in visited:
            continue
        current = root / relative
        resolved = current.resolve(strict=True)
        if not resolved.is_relative_to(root) or not resolved.is_file():
            raise AssertionError(f"引用超出套件或不是文件：{relative}")
        content = current.read_text(encoding="utf-8")
        visited.add(relative)
        for destination in LINK_PATTERN.findall(content):
            if destination.startswith(("http:", "https:")):
                raise AssertionError(f"公共治理闭包不能依赖远端正文：{destination}")
            path = destination.split("#", 1)[0]
            located = re.fullmatch(r"(.+):(\d+)", path)
            if located:
                path, line = located.groups()
            else:
                line = None
            if not path:
                continue
            if Path(path).is_absolute():
                raise AssertionError(f"套件引用不能是绝对路径：{destination}")
            target = (current.parent / path).resolve(strict=True)
            if not target.is_relative_to(root) or not target.is_file():
                raise AssertionError(f"引用超出套件或不是文件：{destination}")
            if line is not None:
                count = len(target.read_text(encoding="utf-8").splitlines())
                if not 1 <= int(line) <= count:
                    raise AssertionError(f"行定位无效：{destination}")
            pending.append(target.relative_to(root).as_posix())
    return visited


class PortableGovernanceContracts(unittest.TestCase):
    def test_procedure_has_complete_suite_local_reference_closure(self):
        self.assertEqual(reference_closure(SUITE, PROCEDURE),
                         {PROCEDURE, CONTRACT, TEMPLATE})

    def test_target_slots_are_explicit_not_source_repository_navigation(self):
        procedure = (SUITE / PROCEDURE).read_text(encoding="utf-8")
        contract = (SUITE / CONTRACT).read_text(encoding="utf-8")
        for slot in ("AGENTS.md", "specs/governance/", "specs/tasks/",
                     "docs/adrs/", "docs/analysis/", "docs/project-context.md"):
            with self.subTest(slot=slot):
                self.assertIn(slot, contract)
        self.assertIn("目标产物按获准目标根解析", procedure)
        self.assertIn("槽位名称不是这些文件已经存在的证据", contract)
        self.assertNotIn("../../../../../", procedure)
        self.assertNotIn("_bmad-solo-source", procedure + contract)
        self.assertNotIn("legacy-skills", procedure + contract)

    def test_portable_contract_preserves_required_safety_boundaries(self):
        content = (SUITE / CONTRACT).read_text(encoding="utf-8")
        required = (
            "不重复完整分析", "只读任务", "不运行验证",
            "不另建进度账本", "全部未完成义务", "支持闭包",
            "三者覆盖率均为 100%", "不得缩减分母", "separate_actor",
            "context_only", "不构成独立批准", "纯软超限",
            "未协商能力", "消费者独立核对", "原始回执",
            "失败不推进依赖", "必需项跳过", "清理未知",
            "只重验相应证据", "不触发业务重测", "分别取得",
        )
        # 最后一项使用明确发布边界检查，避免把文字同义表达当运行判定。
        for token in required[:-1]:
            with self.subTest(token=token):
                self.assertIn(token, content)
        self.assertIn("候选输出与正式发布分开授权", content)
        self.assertIn("失败或源变化保留源", content)
        self.assertIn("不预造入口或参数", content)
        self.assertIn("不自动生成目标私有治理文档", content)

    def test_new_documents_remain_proposals_without_runtime_claims(self):
        for relative in (PROCEDURE, CONTRACT):
            with self.subTest(relative=relative):
                content = (SUITE / relative).read_text(encoding="utf-8")
                header = content.split("---", 2)[1]
                self.assertIn("status: PROPOSED", header)
                self.assertIn("runtime_verified: false", header)
        self.assertIn("入口名称与参数从当前实现读取",
                      (SUITE / PROCEDURE).read_text(encoding="utf-8"))

    def test_source_mapping_contains_public_closure_not_private_governance(self):
        files, modes, sources = collect_source(SUITE, ())
        for relative in reference_closure(SUITE, PROCEDURE):
            with self.subTest(relative=relative):
                self.assertEqual(files[PLUGIN + relative], sources[relative])
        self.assertEqual(modes, {})
        self.assertFalse(any(relative.startswith(("specs/", "docs/", "_bmad-output/"))
                             for relative in sources))
        for private in (ROOT / "specs/governance").glob("*.md"):
            content = private.read_bytes()
            self.assertFalse(any(content in value.content for value in sources.values()),
                             f"套件不能嵌入私有规范全文：{private.name}")
        verify_source(SUITE, sources)

    def test_ci_explicitly_collects_portable_governance_regression(self):
        ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("Test Portable Governance Contracts", ci)
        self.assertIn("test -f tests/roo_distribution/test_portable_governance.py", ci)
        self.assertIn('pattern="test_portable_governance.py"', ci)
        self.assertIn("suite.countTestCases() == 0", ci)
        self.assertIn("result.wasSuccessful() and not result.skipped", ci)


class PortableGovernanceDistribution(unittest.TestCase):
    setUp = fixtures.CliSafety.setUp
    run_cli = fixtures.CliSafety.run_cli
    install = fixtures.CliSafety.install
    tree = fixtures.CliSafety.tree

    def test_isolated_install_resolves_closure_without_project_document_creation(self):
        self.source = SUITE
        _, _, before_source = collect_source(SUITE, ())
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        mirror = self.target / PLUGIN
        self.assertEqual(reference_closure(mirror, PROCEDURE),
                         {PROCEDURE, CONTRACT, TEMPLATE})
        provenance = json.loads((mirror / ".manifest.json").read_bytes())
        for relative in (PROCEDURE, CONTRACT, TEMPLATE):
            with self.subTest(relative=relative):
                self.assertEqual((mirror / relative).read_bytes(),
                                 before_source[relative].content)
                self.assertEqual(provenance["source_files"][relative],
                                 provenance["managed_files"][PLUGIN + relative])
        for private in ("AGENTS.md", "specs", "docs", "_bmad-output"):
            with self.subTest(private=private):
                self.assertFalse((self.target / private).exists())
        verify_source(SUITE, before_source)
        before_target = self.tree()
        repeated = self.install()
        self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
        self.assertEqual(self.tree(), before_target)
        verify_source(SUITE, before_source)


if __name__ == "__main__":
    unittest.main()
