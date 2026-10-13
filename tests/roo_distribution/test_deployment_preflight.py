"""只读聚合迁移范围；所有旧镜像、模式及状态都是项目内夹具。"""
import json
import unittest
from unittest.mock import patch

import test_asset_safety_cli as fixtures


class DeploymentPreflight(unittest.TestCase):
    setUp = fixtures.CliSafety.setUp
    run_cli = fixtures.CliSafety.run_cli
    install = fixtures.CliSafety.install
    tree = fixtures.CliSafety.tree

    def seed_legacy(self):
        first = '.gemini/config/plugins/bmad-suite/plugin.json'
        second = '.gemini/config/rules/bmad-core.md'
        for relative in (first, second):
            path = self.target / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'legacy mirror\n')
        mode = self.target / self.mode
        mode.parent.mkdir(parents=True)
        mode.write_bytes(b'theme: dark\ncustomModes: [{slug: bmad-engineer, name: Old}, {slug: personal, name: Personal}]\n')
        unknown = self.target / '.gemini/config/plugins/bmad-suite/legacy-only.txt'
        unknown.write_bytes(b'old asset must remain')
        return first, second

    def test_all_legacy_collisions_reported_and_preflight_never_writes(self):
        first, second = self.seed_legacy()
        before = self.tree()
        directories = sorted(p.relative_to(self.target).as_posix() for p in self.target.rglob('*') if p.is_dir())
        for option in ('--preflight', '--dry-run'):
            result = self.install(option)
            self.assertNotEqual(result.returncode, 0)
            for relative in (first, second):
                self.assertIn('文件接管待授权：' + relative, result.stdout)
            self.assertIn('模式接管待授权：' + self.mode + '=bmad-engineer', result.stdout)
            self.assertIn('保留个人模式=personal', result.stdout)
            self.assertIn('legacy-only.txt', result.stdout)
            self.assertEqual(self.tree(), before)
            self.assertEqual(sorted(p.relative_to(self.target).as_posix() for p in self.target.rglob('*') if p.is_dir()), directories)
            self.assertFalse((self.target / '.bmad-solo-deployment').exists())

    def test_same_bytes_still_require_explicit_ownership_authorization(self):
        relative = '.gemini/config/plugins/bmad-suite/plugin.json'
        path = self.target / relative
        path.parent.mkdir(parents=True)
        path.write_bytes((self.source / 'plugin.json').read_bytes())
        path.chmod((self.source / 'plugin.json').stat().st_mode & 0o777)
        result = self.install('--preflight')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('内容及权限相同', result.stdout)
        self.assertIn('文件接管待授权：' + relative, result.stdout)

    def test_corrupt_mode_and_file_collisions_both_reported(self):
        first, second = self.seed_legacy()
        (self.target / self.mode).write_bytes(b'customModes: [')
        before = self.tree()
        result = self.install('--preflight')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(first, result.stdout)
        self.assertIn(second, result.stdout)
        self.assertIn('模式配置解析失败', result.stdout)
        self.assertEqual(self.tree(), before)

    def test_preflight_rejects_adoption_and_version_mutations(self):
        before = self.tree()
        for option in (('--adopt-file', '.gemini/config/plugins/bmad-suite/plugin.json'),
                       ('--adopt-mode', self.mode + '=bmad-engineer'), ('--uninstall',)):
            result = self.install('--preflight', *option)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(self.tree(), before)

    def test_existing_incomplete_transaction_blocks_read_only(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        journal = self.target / '.bmad-solo-deployment/transaction-incomplete'
        journal.mkdir()
        (journal / 'transaction.json').write_text(json.dumps({'status': 'APPLYING'}))
        before = self.tree()
        result = self.install('--preflight')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('事务未完成', result.stdout)
        self.assertEqual(self.tree(), before)

    def test_in_process_preflight_calls_no_write_primitives(self):
        import sys
        sys.path.insert(0, str(fixtures.ROOT / 'scripts'))
        from deployment_preflight import inspect_migration
        from deployment_source import collect_source
        self.seed_legacy()
        files, modes, _ = collect_source(self.source, (self.mode,))
        with patch('pathlib.Path.mkdir', side_effect=AssertionError('mkdir forbidden')), \
             patch('asset_safety.atomic_replace', side_effect=AssertionError('write forbidden')), \
             patch('asset_safety.deployment_lock', side_effect=AssertionError('lock forbidden')), \
             patch('deploy_managed.commit_changes', side_effect=AssertionError('commit forbidden')):
            result = inspect_migration(self.target, self.target / '.bmad-solo-deployment', files, modes)
        self.assertEqual(len(result.adopt_files), 2)
        self.assertEqual(len(result.adopt_modes), 1)
        self.assertTrue(result.errors)


if __name__ == '__main__':
    unittest.main()
