"""唯一 V4 分发、退役拒绝及受管保护；仅使用项目内隔离夹具。"""
import json
import unittest

import yaml

import test_gitops_dry_run as fixtures


class SuiteSelection(unittest.TestCase):
    setUp = fixtures.GitOpsDryRun.setUp
    run_command = fixtures.GitOpsDryRun.run_command
    git = fixtures.GitOpsDryRun.git
    tree = fixtures.GitOpsDryRun.tree
    MANIFEST = '.gemini/config/plugins/bmad-suite/.manifest.json'

    def deploy(self, *arguments):
        result = self.run_command(['bash', 'bs.sh', *arguments])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads((self.target / self.MANIFEST).read_bytes())

    def assert_rejected_without_changes(self, *arguments):
        before_repo = self.tree(self.repo)
        before_target = self.tree(self.target)
        result = self.run_command(['bash', 'bs.sh', *arguments])
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.tree(self.repo), before_repo,
                         '失败关闭不得修改仓库引用、缓存或工作树')
        self.assertEqual(self.tree(self.target), before_target,
                         '失败关闭不得修改部署资产或事务记录')
        return result

    def test_new_install_and_v4_aliases_are_idempotent(self):
        manifest = self.deploy()
        self.assertEqual(manifest['major_version'], 'v4')
        self.assertEqual(manifest['suite_id'], 'bmad-suite-v4')
        self.assertEqual(manifest['source_path'], 'bmad-suite-v4')
        before = self.tree(self.target)
        for arguments in (('v4',), ('--suite', 'v4'), ('--v4',)):
            with self.subTest(arguments=arguments):
                self.assertEqual(self.deploy(*arguments), manifest)
                self.assertEqual(self.tree(self.target), before)

    def test_latest_handoff_keeps_v4_once(self):
        self.deploy()
        result = self.run_command(['bash', 'bs.sh', '--latest'])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count('显式移交磁盘新版部署入口'), 1)
        manifest = json.loads((self.target / self.MANIFEST).read_bytes())
        self.assertEqual(manifest['major_version'], 'v4')
        self.assertEqual(manifest['source_path'], 'bmad-suite-v4')

    def test_retired_versions_unknown_and_conflicting_tags_fail_without_writes(self):
        for arguments in (
            ('v3',), ('v5',), ('--v3',), ('--v5',),
            ('--suite', 'v5'), ('--suite', 'v3'), ('--suite', 'v6'),
            ('--suite',), ('v4', 'v5'), ('--update', 'v3'),
            ('--tag', 'fixture-release', '--tag', 'other-release'),
            ('--tag', 'v5.0.0'), ('--tag', 'fixture-release', '--update'),
        ):
            with self.subTest(arguments=arguments):
                self.assert_rejected_without_changes(*arguments)

    def test_missing_v4_does_not_use_generic_source(self):
        (self.repo / 'bmad-suite-v4').rename(self.repo / 'bmad-suite')
        self.assert_rejected_without_changes()

    def test_untrusted_existing_assets_block_before_update_even_with_v4_alias(self):
        path = self.target / '.gemini/config/plugins/bmad-suite/plugin.json'
        path.parent.mkdir(parents=True)
        path.write_bytes(b'{"name":"bmad-suite"}\n')
        for arguments in (('--update',), ('--update', 'v4'), ('--suite', 'v4')):
            with self.subTest(arguments=arguments):
                result = self.assert_rejected_without_changes(*arguments)
                self.assertIn('所有权清单', result.stderr)

    def test_unknown_initial_plugin_directory_blocks_without_deleting_personal_asset(self):
        unrelated = self.target / '.gemini/config/plugins/bmad-suite/personal.txt'
        unrelated.parent.mkdir(parents=True)
        unrelated.write_bytes(b'preserve personal asset\n')
        result = self.assert_rejected_without_changes('v4')
        self.assertIn('所有权清单', result.stderr)
        self.assertEqual(unrelated.read_bytes(), b'preserve personal asset\n')

    def test_v4_preserves_third_party_assets_and_modes(self):
        relative = 'personal profile/settings/custom_modes.yaml'
        mode = self.target / relative
        mode.parent.mkdir(parents=True)
        mode.write_text('theme: dark\ncustomModes: [{slug: personal, name: Personal}]\n',
                        encoding='utf-8')
        # 首次只处理可确认的新 V4 目标；未知插件目录的拒绝另有反例。
        self.deploy('--mode-target', relative)
        unrelated = self.target / '.gemini/config/plugins/bmad-suite/personal.txt'
        unrelated.write_bytes(b'preserve personal asset\n')
        source = self.repo / 'bmad-suite-v4/roo/rules/02-bmad-core.md'
        source.write_bytes(source.read_bytes() + b'\n<!-- V4 update fixture -->\n')
        # 非幂等更新也须保留第三方文件、个人模式和顶层字段。
        self.deploy('--mode-target', relative)
        before = self.tree(self.target)
        self.deploy('v4', '--mode-target', relative)
        self.assertEqual(self.tree(self.target), before)
        self.assertEqual(unrelated.read_bytes(), b'preserve personal asset\n')
        modes = yaml.safe_load(mode.read_bytes())
        self.assertEqual(modes['theme'], 'dark')
        self.assertEqual(next(item for item in modes['customModes']
                              if item['slug'] == 'personal')['name'], 'Personal')
        self.assertEqual((self.target / '.roo/rules/02-bmad-core.md').read_bytes(),
                         (self.repo / 'bmad-suite-v4/roo/rules/02-bmad-core.md').read_bytes())

    def test_modified_managed_asset_blocks_even_explicit_v4(self):
        self.deploy()
        path = self.target / '.roo/rules/02-bmad-core.md'
        path.write_bytes(path.read_bytes() + b'\n# user change\n')
        self.assert_rejected_without_changes('v4')

    def test_preflight_has_no_asset_cache_or_task_start_side_effects(self):
        before_repo, before_target = self.tree(self.repo), self.tree(self.target)
        result = self.run_command(['bash', 'bs.sh', '--preflight'])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.tree(self.repo), before_repo)
        self.assertEqual(self.tree(self.target), before_target)
        self.assertIn('未执行写入', result.stdout)
        self.assertFalse((self.repo / '.versions').exists())
        for root in (self.repo, self.target):
            self.assertFalse((root / '.bmad-control').exists())
            self.assertFalse((root / '.bmad-runtime').exists())


if __name__ == '__main__':
    unittest.main()
