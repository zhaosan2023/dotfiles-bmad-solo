"""未激活 Cline 模板的静态及隔离分发回归。

仅验证模板、真实来源映射和项目内分发消费者；不运行 Cline，
不证明原生模式承载、自动技能绑定或执行/推进硬门禁。
"""
from pathlib import Path, PurePosixPath
import re
import sys
import unittest

import test_gitops_dry_run as fixtures

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from asset_safety import AssetError
from deployment_source import collect_source, verify_source

TEMPLATE = "cline/templates/bmad-router.md"
MIRROR = ".gemini/config/plugins/bmad-suite"


class HostTemplateContracts(unittest.TestCase):
    def setUp(self):
        self.source = ROOT / "bmad-suite-v4"
        self.content = (self.source / TEMPLATE).read_text(encoding="utf-8")

    def test_navigation_resolves_from_workspace_root_with_valid_lines(self):
        links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", self.content)
        self.assertTrue(links, "模板必须实际引用已有方法论，而非复制全文")
        expected = {
            "bmad-suite-v4/rules/bmad-constitution.md",
            "_bmad-output/project-context.md",
            "bmad-suite-v4/skills/ana-solo/SKILL.md",
            "bmad-suite-v4/skills/bmad/SKILL.md",
        }
        actual = set()
        for link in links:
            with self.subTest(link=link):
                relative, separator, line = link.rpartition(":")
                self.assertEqual(separator, ":")
                self.assertTrue(line.isdecimal())
                path = PurePosixPath(relative)
                self.assertFalse(path.is_absolute())
                self.assertNotIn("..", path.parts)
                target = ROOT / relative
                self.assertTrue(target.is_file(), relative)
                self.assertTrue(target.resolve().is_relative_to(ROOT))
                lines = target.read_text(encoding="utf-8").splitlines()
                self.assertGreaterEqual(int(line), 1)
                self.assertLessEqual(int(line), len(lines))
                actual.add(relative)
        self.assertEqual(actual, expected)

    def test_template_remains_navigation_not_embedded_role_documents(self):
        for relative in (
            "skills/ana-solo/SKILL.md", "skills/bmad/SKILL.md",
            "rules/bmad-constitution.md",
        ):
            with self.subTest(role=relative):
                role = (self.source / relative).read_text(encoding="utf-8")
                self.assertNotIn(role.strip(), self.content)
        self.assertIn("不同时常驻两套完整角色指令", self.content)
        self.assertIn("按当前工作区根目录解析", self.content)
        self.assertIn("信号缺失或矛盾", self.content)

    def test_static_text_discloses_permission_and_runtime_limits(self):
        # 这些断言只防止模板契约退化，不证明模型行为或程序拒绝。
        for requirement in (
            "未激活的项目级行为适配模板",
            "不是程序门禁或有效宿主配置",
            "不要求用户手动输入技能口令",
            "显式读取退路",
            "不使用终端、不实施生产代码",
            "仅文档保存任务",
            "必需失败不得登记完成或推进依赖",
            "零收集", "必需项跳过", "清理证据缺失",
            "仅重验受影响证据",
            "不在计划或 ADR 镜像逐轮流水",
            "相关硬门禁保持 BLOCKED",
            "静态模板验证不能替代这些运行时验收",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, self.content)

    def test_existing_source_mapping_keeps_template_in_inactive_mirror(self):
        files, modes, sources = collect_source(self.source, ())
        self.assertEqual(files[f"{MIRROR}/{TEMPLATE}"], sources[TEMPLATE])
        self.assertEqual(modes, {})
        self.assertFalse(any(
            relative.startswith((".cline/", ".clinerules/"))
            or relative in {".clinerules", "AGENTS.md"}
            for relative in files
        ))
        self.assertIn(".roo/rules/02-bmad-core.md", files)
        self.assertIn(".gemini/config/rules/bmad-core.md", files)
        verify_source(self.source, sources)

    def test_source_map_does_not_collect_project_private_material(self):
        files, _, sources = collect_source(self.source, ())
        self.assertFalse(any(
            relative.startswith(("_bmad-output/", "plans/", "specs/"))
            or relative.startswith("PLAN-")
            for relative in sources
        ))
        private = (ROOT / "_bmad-output/project-context.md").read_bytes()
        self.assertTrue(private)
        self.assertNotIn(private, [value.content for value in files.values()])


class HostTemplateDistribution(unittest.TestCase):
    setUp = fixtures.GitOpsDryRun.setUp
    run_command = fixtures.GitOpsDryRun.run_command
    git = fixtures.GitOpsDryRun.git
    tree = fixtures.GitOpsDryRun.tree

    def install(self, *arguments):
        result = self.run_command([
            "bash", "bs.sh", "--suite", "v4", *arguments,
        ])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_template_distribution_is_inactive_and_update_preserves_assets(self):
        source = self.repo / "bmad-suite-v4"
        before_source = self.tree(source)
        before_git = self.tree(self.repo / ".git")
        personal = self.target / "personal.txt"
        personal.write_bytes(b"preserve third party\n")
        mode_relative = "personal profile/settings/custom_modes.yaml"
        mode_path = self.target / mode_relative
        mode_path.parent.mkdir(parents=True)
        mode_path.write_bytes(b"theme: dark\ncustomModes: [{slug: personal, name: Personal}]\n")
        self.install("--mode-target", mode_relative)
        protected = {
            ".roo/rules/02-bmad-core.md",
            ".roo/rules-ana-architect/01-ana-solo-core.md",
            ".roo/rules-bmad-engineer/01-bmad-engineer-core.md",
            ".gemini/config/rules/bmad-core.md",
            mode_relative,
        }
        before_targets = {name: (self.target / name).read_bytes() for name in protected}
        self.install("--mode-target", mode_relative)
        for name, content in before_targets.items():
            with self.subTest(preserved=name):
                self.assertEqual((self.target / name).read_bytes(), content)
        self.assertEqual((self.target / MIRROR / TEMPLATE).read_bytes(),
                         (source / TEMPLATE).read_bytes())
        self.assertEqual(personal.read_bytes(), b"preserve third party\n")
        self.assertEqual(self.tree(source), before_source)
        self.assertEqual(self.tree(self.repo / ".git"), before_git)
        for relative in (".cline", ".clinerules", "AGENTS.md", ".bmad-control", ".bmad-runtime"):
            with self.subTest(inactive=relative):
                self.assertFalse((self.target / relative).exists())

    def test_conflicting_template_target_blocks_without_target_side_effects(self):
        conflicting = self.target / MIRROR / TEMPLATE
        conflicting.parent.mkdir(parents=True)
        conflicting.write_bytes(b"unmanaged user template\n")
        before_target = self.tree(self.target)
        before_source = self.tree(self.repo / "bmad-suite-v4")
        result = self.run_command(["bash", "bs.sh", "--suite", "v4"])
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.tree(self.target), before_target)
        self.assertEqual(self.tree(self.repo / "bmad-suite-v4"), before_source)
        self.assertEqual(conflicting.read_bytes(), b"unmanaged user template\n")

    def test_changed_template_source_is_rejected_before_deployment(self):
        source = self.repo / "bmad-suite-v4"
        _, _, sources = collect_source(source, ())
        template = source / TEMPLATE
        original = template.read_bytes()
        before_target = self.tree(self.target)
        template.write_bytes(original + b"\nfixture source mutation\n")
        with self.assertRaises(AssetError):
            verify_source(source, sources)
        self.assertEqual(self.tree(self.target), before_target)
        template.write_bytes(original)
        verify_source(source, sources)
        self.assertEqual(self.tree(self.target), before_target)


if __name__ == "__main__":
    unittest.main()
