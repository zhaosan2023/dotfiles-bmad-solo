"""唯一 V4 标签身份、提交绑定、缓存保留和退役拒绝。"""
import json
import unittest

import test_gitops_dry_run as fixtures


class SuiteTagCache(unittest.TestCase):
    setUp = fixtures.GitOpsDryRun.setUp
    run_command = fixtures.GitOpsDryRun.run_command
    git = fixtures.GitOpsDryRun.git
    tree = fixtures.GitOpsDryRun.tree
    MANIFEST = '.gemini/config/plugins/bmad-suite/.manifest.json'

    def deploy_tag(self, tag='fixture-release'):
        result = self.run_command(['bash', 'bs.sh', '--tag', tag])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads((self.target / self.MANIFEST).read_bytes())

    def test_v4_cache_identity_and_idempotence(self):
        commit = self.git('rev-parse', 'HEAD').strip()
        manifest = self.deploy_tag()
        cache = self.repo / '.versions' / ('commit-' + commit)
        self.assertTrue((cache / 'bmad-suite-v4/plugin.json').is_file())
        self.assertFalse((cache / 'bmralph-suite-v5').exists())
        self.assertEqual((cache / 'commit.txt').read_text(), commit + '\n')
        self.assertEqual(manifest['major_version'], 'v4')
        self.assertEqual(manifest['source_path'], 'bmad-suite-v4')
        self.assertEqual(manifest['source_commit'], commit)
        self.assertEqual(manifest['source_kind'], 'commit_cache')
        self.assertIs(manifest['source_dirty'], False)
        self.assertEqual(manifest['source_directory'], str(cache / 'bmad-suite-v4'))
        before_cache, before_target = self.tree(cache), self.tree(self.target)
        self.assertEqual(self.deploy_tag(), manifest)
        self.assertEqual(self.tree(cache), before_cache)
        self.assertEqual(self.tree(self.target), before_target)

    def test_retired_suite_and_tag_hint_fail_before_cache_or_deployment(self):
        before_repo, before_target = self.tree(self.repo), self.tree(self.target)
        for arguments in (('v5', '--tag', 'fixture-release'),
                          ('--suite', 'v3', '--tag', 'fixture-release'),
                          ('--tag', 'v5.0.0')):
            with self.subTest(arguments=arguments):
                result = self.run_command(['bash', 'bs.sh', *arguments])
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.tree(self.repo), before_repo)
                self.assertEqual(self.tree(self.target), before_target)
                self.assertFalse((self.repo / '.versions').exists())

    def test_modified_cache_is_not_repaired_or_replaced(self):
        commit = self.git('rev-parse', 'HEAD').strip()
        self.deploy_tag()
        cache = self.repo / '.versions' / ('commit-' + commit)
        path = cache / 'bmad-suite-v4/plugin.json'
        path.write_bytes(path.read_bytes() + b'\n')
        before_cache, before_target = self.tree(cache), self.tree(self.target)
        result = self.run_command(['bash', 'bs.sh', '--tag', 'fixture-release'])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('缓存内容或权限与实际提交不符', result.stderr)
        self.assertEqual(self.tree(cache), before_cache)
        self.assertEqual(self.tree(self.target), before_target)

    def test_moved_tag_uses_new_commit_and_preserves_old_cache(self):
        first = self.git('rev-parse', 'HEAD').strip()
        self.deploy_tag()
        first_cache = self.repo / '.versions' / ('commit-' + first)
        before_first = self.tree(first_cache)
        relative = 'bmad-suite-v4/roo/rules/02-bmad-core.md'
        source = self.repo / relative
        updated = source.read_bytes() + b'\n<!-- moved V4 tag fixture -->\n'
        source.write_bytes(updated)
        self.git('add', relative)
        self.git('-c', 'commit.gpgsign=false', 'commit', '-m', 'fixture moved V4 tag')
        second = self.git('rev-parse', 'HEAD').strip()
        self.git('tag', '-f', 'fixture-release')
        manifest = self.deploy_tag()
        self.assertNotEqual(first, second)
        self.assertTrue((self.repo / '.versions' / ('commit-' + second)).is_dir())
        self.assertEqual(manifest['source_commit'], second)
        self.assertEqual(self.tree(first_cache), before_first)
        self.assertEqual((self.target / '.roo/rules/02-bmad-core.md').read_bytes(), updated)

    def test_snapshot_records_selected_commit_not_later_head(self):
        selected = self.git('rev-parse', 'HEAD').strip()
        relative = 'bmad-suite-v4/roo/rules/02-bmad-core.md'
        source = self.repo / relative
        original = source.read_bytes()
        source.write_bytes(original + b'\n<!-- later worktree commit -->\n')
        self.git('add', relative)
        self.git('-c', 'commit.gpgsign=false', 'commit', '-m', 'fixture later commit')
        self.assertNotEqual(self.git('rev-parse', 'HEAD').strip(), selected)
        manifest = self.deploy_tag()
        self.assertEqual(manifest['source_commit'], selected)
        self.assertIs(manifest['source_dirty'], False)
        self.assertEqual((self.target / '.roo/rules/02-bmad-core.md').read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
