"""V4 分析返修的隔离分发回归；不触碰真实宿主或启动模型任务。"""
import json
import unittest

import yaml

import test_gitops_dry_run as fixtures


class V4AnalysisDistribution(unittest.TestCase):
    setUp = fixtures.GitOpsDryRun.setUp
    run_command = fixtures.GitOpsDryRun.run_command
    git = fixtures.GitOpsDryRun.git
    tree = fixtures.GitOpsDryRun.tree

    def test_repaired_native_and_roo_entries_are_distributed_without_starting_tasks(self):
        source = self.repo / "bmad-suite-v4"
        before_source = self.tree(source)
        mode_relative = "personal profile/settings/custom_modes.yaml"
        mode_path = self.target / mode_relative
        mode_path.parent.mkdir(parents=True)
        mode_path.write_text(
            "theme: dark\ncustomModes: [{slug: personal, name: Personal}]\n",
            encoding="utf-8",
        )
        personal = self.target / "personal.txt"
        personal.write_bytes(b"preserve unrelated asset\n")
        result = self.run_command([
            "bash", "bs.sh", "--suite", "v4", "--mode-target", mode_relative,
        ])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        plugin = self.target / ".gemini/config/plugins/bmad-suite"
        manifest = json.loads((plugin / ".manifest.json").read_bytes())
        self.assertEqual(manifest["major_version"], "v4")
        self.assertEqual(manifest["suite_id"], "bmad-suite-v4")
        self.assertEqual(manifest["source_path"], "bmad-suite-v4")
        for relative in (
            "skills/ana-solo/SKILL.md",
            "skills/ana-solo/references/convergence-locks.md",
            "skills/ana-solo/references/paper-reading-guide.md",
            "skills/bmad/references/procedures/algorithm-fit.md",
            "skills/bmad/references/templates/implementation-plan.template.md",
            "roo/settings/custom_modes.yaml",
            "roo/rules-ana-architect/01-ana-solo-core.md",
            "roo/rules-bmad-engineer/01-bmad-engineer-core.md",
            "roo/rules/01-bmad-constitution.md",
            "roo/rules/02-bmad-core.md",
        ):
            with self.subTest(asset=relative):
                self.assertEqual((plugin / relative).read_bytes(),
                                 (source / relative).read_bytes())
        for relative in (
            "rules-ana-architect/01-ana-solo-core.md",
            "rules-bmad-engineer/01-bmad-engineer-core.md",
            "rules/01-bmad-constitution.md",
            "rules/02-bmad-core.md",
        ):
            with self.subTest(roo_rule=relative):
                self.assertEqual((self.target / ".roo" / relative).read_bytes(),
                                 (source / "roo" / relative).read_bytes())
        actual = yaml.safe_load(mode_path.read_bytes())
        expected = yaml.safe_load((source / "roo/settings/custom_modes.yaml").read_bytes())
        self.assertEqual(actual["theme"], "dark")
        by_slug = {mode["slug"]: mode for mode in actual["customModes"]}
        self.assertEqual(by_slug["personal"], {"slug": "personal", "name": "Personal"})
        for mode in expected["customModes"]:
            self.assertEqual(by_slug[mode["slug"]], mode)
        self.assertEqual(personal.read_bytes(), b"preserve unrelated asset\n")
        self.assertEqual(self.tree(source), before_source)
        for root in (self.target, plugin):
            self.assertFalse((root / ".bmad-control").exists())
            self.assertFalse((root / ".bmad-runtime").exists())
        # 仅证明隔离根中的资产分发与未生成任务目录，不证明宿主加载或模型行为。


if __name__ == "__main__":
    unittest.main()
