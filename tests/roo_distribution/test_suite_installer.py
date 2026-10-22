"""安装版本透传；只使用项目内独立仓库、本地文件远端和临时部署根。"""
import json
import shutil
import unittest

import test_gitops_dry_run as fixtures


class SuiteInstaller(unittest.TestCase):
    setUp = fixtures.GitOpsDryRun.setUp
    run_command = fixtures.GitOpsDryRun.run_command
    git = fixtures.GitOpsDryRun.git
    tree = fixtures.GitOpsDryRun.tree
    MANIFEST = '.gemini/config/plugins/bmad-suite/.manifest.json'

    def prepare_installer(self):
        self.remote = self.sandbox / 'local source.git'
        self.git('clone', '--bare', str(self.repo), str(self.remote))
        self.git('remote', 'add', 'origin', str(self.remote))
        self.installer = self.sandbox / 'install.sh'
        # 用本地受控夹具替换固定远端；测试不访问网络、不执行 push。
        content = (fixtures.ROOT / 'install.sh').read_text(encoding='utf-8')
        original = 'REPO_URL="https://github.com/zhaosan2023/dotfiles-bmad-solo.git"'
        self.assertIn(original, content)
        self.installer.write_text(content.replace(original, f'REPO_URL="{self.remote}"'),
                                  encoding='utf-8')
        self.env['BMAD_SOLO_DIR'] = str(self.repo)

    def run_installer(self, *arguments):
        result = self.run_command(['bash', str(self.installer), *arguments])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads((self.target / self.MANIFEST).read_bytes())

    def test_explicit_v4_existing_repository_update_is_forwarded(self):
        self.prepare_installer()
        manifest = self.run_installer('--suite', 'v4')
        self.assertEqual(manifest['major_version'], 'v4')
        self.assertEqual(manifest['source_path'], 'bmad-suite-v4')
        self.assertEqual(list(self.home.iterdir()), [])

    def test_implicit_update_preserves_previously_deployed_v4(self):
        self.prepare_installer()
        deployed = self.run_command(['bash', 'bs.sh'])
        self.assertEqual(deployed.returncode, 0, deployed.stdout + deployed.stderr)
        before = self.tree(self.target)
        manifest = self.run_installer()
        self.assertEqual(manifest['major_version'], 'v4')
        self.assertEqual(self.tree(self.target), before)

    def test_fresh_clone_explicit_v4(self):
        self.prepare_installer()
        clone = self.sandbox / 'new repository'
        self.env['BMAD_SOLO_DIR'] = str(clone)
        manifest = self.run_installer('v4')
        self.assertEqual(manifest['major_version'], 'v4')
        self.assertEqual(manifest['source_repository'], str(clone))
        self.assertTrue((clone / 'bmad-suite-v4/plugin.json').is_file())
        self.assertFalse((clone / 'bmralph-suite-v5').exists())

    def test_fresh_clone_without_version_defaults_to_v4(self):
        self.prepare_installer()
        clone = self.sandbox / 'new default repository'
        self.env['BMAD_SOLO_DIR'] = str(clone)
        manifest = self.run_installer()
        self.assertEqual(manifest['major_version'], 'v4')
        self.assertEqual(manifest['source_repository'], str(clone))

    def test_conflicting_or_unknown_versions_fail_before_clone_or_fetch(self):
        self.prepare_installer()
        clone = self.sandbox / 'never cloned'
        self.env['BMAD_SOLO_DIR'] = str(clone)
        before_repo, before_target = self.tree(self.repo), self.tree(self.target)
        for args in (('v3',), ('v5',), ('--v5',), ('v4', 'v5'),
                     ('--suite', 'v5', '--v4'), ('--suite', 'v3'),
                     ('--suite', 'v6'), ('--suite',), ('--unknown',)):
            with self.subTest(args=args):
                result = self.run_command(['bash', str(self.installer), *args])
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(clone.exists())
                self.assertEqual(self.tree(self.repo), before_repo)
                self.assertEqual(self.tree(self.target), before_target)

    def test_help_has_no_clone_update_or_deploy_side_effects(self):
        self.prepare_installer()
        before_repo, before_target = self.tree(self.repo), self.tree(self.target)
        result = self.run_command(['bash', str(self.installer), '--help'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('V4', result.stdout)
        self.assertNotIn('v5', result.stdout)
        self.assertIn('不启动 Ralph', result.stdout)
        self.assertEqual(self.tree(self.repo), before_repo)
        self.assertEqual(self.tree(self.target), before_target)


if __name__ == '__main__':
    unittest.main()
