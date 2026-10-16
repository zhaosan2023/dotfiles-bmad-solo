"""V4/V5 标签缓存联合身份回归；仅使用项目内独立仓库和临时部署根。"""
import json
import shutil
import unittest

import test_gitops_dry_run as fixtures


class SuiteTagCache(unittest.TestCase):
    setUp = fixtures.GitOpsDryRun.setUp
    run_command = fixtures.GitOpsDryRun.run_command
    git = fixtures.GitOpsDryRun.git
    tree = fixtures.GitOpsDryRun.tree
    MANIFEST = '.gemini/config/plugins/bmad-suite/.manifest.json'

    def add_committed_v5(self):
        shutil.copytree(
            fixtures.ROOT / 'bmralph-suite-v5', self.repo / 'bmralph-suite-v5',
            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'),
        )
        self.git('add', 'bmralph-suite-v5')
        self.git('-c', 'commit.gpgsign=false', 'commit', '-m', 'fixture both suites')
        self.git('tag', 'fixture-both')
        return self.git('rev-parse', 'HEAD').strip()

    def deploy_tag(self, version, tag='fixture-both'):
        result = self.run_command([
            'bash', 'bs.sh', '--suite', version, '--tag', tag,
        ])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads((self.target / self.MANIFEST).read_bytes())

    def test_same_commit_has_separate_caches_and_correct_source_identity(self):
        commit = self.add_committed_v5()
        v4_manifest = self.deploy_tag('v4')
        v4_cache = self.repo / '.versions' / ('commit-' + commit)
        before_v4 = self.tree(v4_cache)
        v5_manifest = self.deploy_tag('v5')
        v5_cache = self.repo / '.versions' / ('v5-commit-' + commit)
        self.assertNotEqual(v4_cache, v5_cache)
        self.assertEqual(self.tree(v4_cache), before_v4,
                         '创建 V5 缓存不得修改同提交的兼容 V4 缓存')
        self.assertTrue((v4_cache / 'bmad-suite-v4/plugin.json').is_file())
        self.assertTrue((v5_cache / 'bmralph-suite-v5/suite.json').is_file())
        self.assertFalse((v5_cache / 'bmad-suite-v4').exists())
        self.assertFalse((v4_cache / 'bmralph-suite-v5').exists())
        for version, cache, manifest, source_path in (
            ('v4', v4_cache, v4_manifest, 'bmad-suite-v4'),
            ('v5', v5_cache, v5_manifest, 'bmralph-suite-v5'),
        ):
            with self.subTest(version=version):
                self.assertEqual((cache / 'commit.txt').read_text(), commit + '\n')
                self.assertEqual(manifest['major_version'], version)
                self.assertEqual(manifest['source_path'], source_path)
                self.assertEqual(manifest['source_commit'], commit)
                self.assertEqual(manifest['source_kind'], 'commit_cache')
                self.assertIs(manifest['source_dirty'], False)
                self.assertEqual(manifest['source_directory'], str(cache / source_path))
        before_v5 = self.tree(v5_cache)
        before_target = self.tree(self.target)
        self.assertEqual(self.deploy_tag('v5'), v5_manifest)
        self.assertEqual(self.tree(v5_cache), before_v5)
        self.assertEqual(self.tree(self.target), before_target)

    def test_tag_without_selected_v5_fails_before_cache_or_deployment_changes(self):
        self.add_committed_v5()
        before_repo = self.tree(self.repo)
        before_target = self.tree(self.target)
        result = self.run_command([
            'bash', 'bs.sh', 'v5', '--tag', 'fixture-release',
        ])
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.tree(self.repo), before_repo)
        self.assertEqual(self.tree(self.target), before_target)
        self.assertFalse((self.repo / '.versions').exists())

    def test_modified_v5_cache_is_not_repaired_or_replaced(self):
        commit = self.add_committed_v5()
        self.deploy_tag('v5')
        cache = self.repo / '.versions' / ('v5-commit-' + commit)
        path = cache / 'bmralph-suite-v5/suite.json'
        path.write_bytes(path.read_bytes() + b'\n')
        before_cache = self.tree(cache)
        before_target = self.tree(self.target)
        result = self.run_command([
            'bash', 'bs.sh', 'v5', '--tag', 'fixture-both',
        ])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('缓存内容或权限与实际提交不符', result.stderr)
        self.assertEqual(self.tree(cache), before_cache)
        self.assertEqual(self.tree(self.target), before_target)

    def test_moved_v5_tag_uses_new_commit_and_preserves_old_cache(self):
        first_commit = self.add_committed_v5()
        self.deploy_tag('v5')
        first_cache = self.repo / '.versions' / ('v5-commit-' + first_commit)
        before_first = self.tree(first_cache)
        relative = 'bmralph-suite-v5/roo/rules/02-bmad-core.md'
        source = self.repo / relative
        updated = source.read_bytes() + b'\n<!-- moved V5 tag fixture -->\n'
        source.write_bytes(updated)
        self.git('add', relative)
        self.git('-c', 'commit.gpgsign=false', 'commit', '-m', 'fixture moved V5 tag')
        second_commit = self.git('rev-parse', 'HEAD').strip()
        self.git('tag', '-f', 'fixture-both')
        manifest = self.deploy_tag('v5')
        second_cache = self.repo / '.versions' / ('v5-commit-' + second_commit)
        self.assertNotEqual(first_commit, second_commit)
        self.assertTrue(second_cache.is_dir())
        self.assertEqual(manifest['source_commit'], second_commit)
        self.assertEqual(self.tree(first_cache), before_first)
        self.assertEqual((self.target / '.roo/rules/02-bmad-core.md').read_bytes(), updated)

    def test_selected_v5_snapshot_records_tag_commit_not_later_head(self):
        selected = self.add_committed_v5()
        relative = 'bmralph-suite-v5/roo/rules/02-bmad-core.md'
        source = self.repo / relative
        original = source.read_bytes()
        source.write_bytes(original + b'\n<!-- later V5 worktree commit -->\n')
        self.git('add', relative)
        self.git('-c', 'commit.gpgsign=false', 'commit', '-m', 'fixture later V5 commit')
        self.assertNotEqual(self.git('rev-parse', 'HEAD').strip(), selected)
        manifest = self.deploy_tag('v5')
        self.assertEqual(manifest['source_commit'], selected)
        self.assertIs(manifest['source_dirty'], False)
        self.assertEqual((self.target / '.roo/rules/02-bmad-core.md').read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
