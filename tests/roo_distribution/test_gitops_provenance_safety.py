"""来源清单的所有权、冲突和失败恢复；仅使用项目内隔离目标。"""
import hashlib
import json
import runpy
import unittest
from unittest.mock import patch

import test_asset_safety_cli as fixtures
import asset_transaction


class ProvenanceSafety(unittest.TestCase):
    setUp = fixtures.CliSafety.setUp
    run_cli = fixtures.CliSafety.run_cli
    install = fixtures.CliSafety.install
    tree = fixtures.CliSafety.tree

    RELATIVE = '.gemini/config/plugins/bmad-suite/.manifest.json'

    def test_unowned_manifest_collision_blocks_all_writes(self):
        manifest = self.target / self.RELATIVE
        manifest.parent.mkdir(parents=True)
        manifest.write_bytes(b'personal manifest\n')
        before = self.tree()
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.tree(), before)
        self.assertFalse((self.target / '.roo').exists())
        self.assertFalse((self.target / '.bmad-solo-deployment').exists())

    def test_modified_manifest_blocks_update_and_uninstall(self):
        installed = self.install()
        self.assertEqual(installed.returncode, 0, installed.stderr)
        manifest = self.target / self.RELATIVE
        manifest.write_bytes(manifest.read_bytes() + b'\n')
        before = self.tree()
        for arguments in (
            ('--source', str(self.source), '--mode-target', self.mode),
            ('--uninstall',),
        ):
            with self.subTest(arguments=arguments):
                result = self.run_cli(*arguments)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(self.RELATIVE, result.stderr)
                self.assertEqual(self.tree(), before)

    def test_manifest_and_owned_asset_digests_agree(self):
        installed = self.install()
        self.assertEqual(installed.returncode, 0, installed.stderr)
        manifest_path = self.target / self.RELATIVE
        content = manifest_path.read_bytes()
        provenance = json.loads(content)
        ownership = json.loads((
            self.target / '.bmad-solo-deployment/ownership.json'
        ).read_bytes())
        record = ownership['files'][self.RELATIVE]
        self.assertEqual(record['sha256'], hashlib.sha256(content).hexdigest())
        self.assertEqual(record['mode'], manifest_path.stat().st_mode & 0o777)
        expected_files = dict(ownership['files'])
        del expected_files[self.RELATIVE]
        self.assertEqual(provenance['managed_files'], expected_files)
        self.assertEqual(provenance['managed_modes'], ownership['modes'])
        self.assertIsNone(provenance['source_commit'])
        self.assertIsNone(provenance['source_dirty'])
        self.assertEqual(provenance['source_kind'], 'unversioned')

    def test_later_commit_failure_restores_manifest_and_assets(self):
        installed = self.install()
        self.assertEqual(installed.returncode, 0, installed.stderr)
        before = self.tree()
        source_rule = self.source / 'roo/rules/02-bmad-core.md'
        source_rule.write_bytes(b'updated source\n')
        original_apply = asset_transaction.apply_snapshot
        manifest_path = self.target / self.RELATIVE
        ownership_path = self.target / '.bmad-solo-deployment/ownership.json'
        written = []

        def fail_ownership(path, expected, desired):
            if path == ownership_path:
                raise OSError('模拟来源清单提交后的所有权写入失败')
            result = original_apply(path, expected, desired)
            written.append(path)
            return result

        entry = runpy.run_path(str(fixtures.ROOT / 'scripts/deploy-managed-cli.py'))
        with patch.object(asset_transaction, 'apply_snapshot', side_effect=fail_ownership):
            result = entry['main']([
                '--root', str(self.target), '--source', str(self.source),
                '--mode-target', self.mode,
            ])
        self.assertEqual(result, 1)
        self.assertIn(manifest_path, written,
                      '故障必须发生在来源清单实际写入之后')
        after = self.tree()
        for relative, value in before.items():
            self.assertEqual(after[relative], value, relative)
        added = set(after) - set(before)
        self.assertTrue(added, '恢复后必须保留新增事务取证记录')
        self.assertTrue(all(
            relative.startswith('.bmad-solo-deployment/transaction-')
            for relative in added
        ))
        new_journals = [relative for relative in added
                        if relative.endswith('/transaction.json')]
        self.assertEqual(len(new_journals), 1)
        journal = json.loads((self.target / new_journals[0]).read_bytes())
        self.assertEqual(journal['status'], 'ROLLED_BACK')
        retried = self.install()
        self.assertEqual(retried.returncode, 0, retried.stderr)
        self.assertEqual((self.target / '.roo/rules/02-bmad-core.md').read_bytes(),
                         b'updated source\n')


if __name__ == '__main__':
    unittest.main()
