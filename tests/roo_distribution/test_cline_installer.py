"""外层安装的 Cline 参数透传回归；仅使用项目内本地文件远端。

不联网、不安装或启动真实宿主，不证明技能自动触发或模式绑定。
"""
import unittest

import test_gitops_dry_run as fixtures
import test_suite_installer as installer


ENTRY = ".cline/skills/bmad-solo/SKILL.md"


class ClineInstaller(unittest.TestCase):
    setUp = fixtures.GitOpsDryRun.setUp
    run_command = fixtures.GitOpsDryRun.run_command
    git = fixtures.GitOpsDryRun.git
    tree = fixtures.GitOpsDryRun.tree
    MANIFEST = installer.SuiteInstaller.MANIFEST
    prepare_installer = installer.SuiteInstaller.prepare_installer
    run_installer = installer.SuiteInstaller.run_installer

    def test_existing_repository_forwards_cline_selection_through_update(self):
        self.prepare_installer()
        manifest = self.run_installer("--cline-skills")
        self.assertEqual(manifest["major_version"], "v4")
        self.assertIn(ENTRY, manifest["managed_files"])
        self.assertTrue((self.target / ENTRY).is_file())
        self.assertEqual(list(self.home.iterdir()), [])

    def test_fresh_clone_forwards_cline_selection_through_latest_handoff(self):
        self.prepare_installer()
        clone = self.sandbox / "new cline repository"
        self.env["BMAD_SOLO_DIR"] = str(clone)
        manifest = self.run_installer("--suite", "v4", "--cline-skills")
        self.assertEqual(manifest["source_repository"], str(clone))
        self.assertIn(ENTRY, manifest["managed_files"])
        self.assertTrue((self.target / ENTRY).is_file())
        self.assertTrue((self.target / ".roo/rules/02-bmad-core.md").is_file())

    def test_default_installer_update_keeps_previously_selected_skills(self):
        self.prepare_installer()
        self.run_installer("--cline-skills")
        before = self.tree(self.target)
        manifest = self.run_installer()
        self.assertIn(ENTRY, manifest["managed_files"])
        self.assertEqual(self.tree(self.target), before)

    def test_cline_selection_does_not_bypass_invalid_parameter_rejection(self):
        self.prepare_installer()
        clone = self.sandbox / "must not clone"
        self.env["BMAD_SOLO_DIR"] = str(clone)
        before_repo, before_target = self.tree(self.repo), self.tree(self.target)
        for arguments in (("--cline-skills", "--suite", "v5"),
                          ("--cline-skills", "--unknown")):
            with self.subTest(arguments=arguments):
                result = self.run_command(["bash", str(self.installer), *arguments])
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(clone.exists())
                self.assertEqual(self.tree(self.repo), before_repo)
                self.assertEqual(self.tree(self.target), before_target)


if __name__ == "__main__":
    unittest.main()
