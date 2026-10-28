"""F3 三文件迁移的真实磁盘隔离回归；不运行宿主或修改真实任务。

测试夹具全部位于项目内，成功路径与失败保全、恢复和引用语义互补。
"""
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import test_contracts as fixtures

ROOT = fixtures.ROOT
SCRIPT = ROOT / '.scratch/F3-20261023-document-governance-01/migrate_batch.py'
SPEC = importlib.util.spec_from_file_location('f3_migration', SCRIPT)
migration = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(migration)


class BatchMigration(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='sandbox-f3-', dir=Path(__file__).parent)
        self.root = Path(temporary.name)

        def cleanup():
            temporary.cleanup()
            self.assertFalse(self.root.exists(), '夹具清理必须完成')
        self.addCleanup(cleanup)
        self.original = {}
        for index, (source, _) in enumerate(migration.FILES):
            path = self.root / source
            path.parent.mkdir(parents=True, exist_ok=True)
            content = ('# 隔离原始文档\n\n- Status: PROPOSED\n\n'
                       '- 原始授权仅为历史；不能证明运行时验收。\n'
                       '- 证据 [公共原文](../../evidence.md:2)\n'
                       '- 旧任务 [原任务](../pending_implementation_plan.md:1)\n'
                       '- 未创建候选 [候选](../../future/)\n'
                       f'- 同批引用 [对象]({self.peer_link(index)}:1)\n'
                       '\n正文保留中文、\\n 字面转义与研究编号 [4]。\n')
            path.write_bytes(content.encode('utf-8'))
            path.chmod(0o640)
            self.original[source] = path.read_bytes()
        (self.root / 'evidence.md').write_text('# 原始来源\n第二行\n', encoding='utf-8')
        (self.root / '_bmad-output/pending_implementation_plan.md').write_bytes(b'old blocked task\n')
        (self.root / '_bmad-output/project-context.md').write_bytes(b'private context\n')
        (self.root / '_bmad-output/adrs/unrelated.md').write_bytes(b'unrelated proposed ADR\n')
        (self.root / migration.PLAN).write_text(
            '---\n' + f'plan_id: "{migration.PLAN_ID}"\n'
            + f'adr_file: "{migration.FILES[0][1]}"\n'
            + 'supplemental_adrs:\n' + f'  - "{migration.FILES[1][1]}"\n'
            + '---\n契约版本：4\n', encoding='utf-8')

    def peer_link(self, index):
        if index == 2:
            return '../adrs/' + Path(migration.FILES[0][0]).name
        return '../analysis/' + Path(migration.FILES[2][0]).name

    def preserve(self):
        return migration.preserve(self.root)

    def prepare(self):
        self.preserve()
        return migration.prepare(self.root)

    def assert_sources(self):
        for source, _ in migration.FILES:
            self.assertEqual((self.root / source).read_bytes(), self.original[source])

    def assert_targets_absent(self):
        for _, target in migration.FILES:
            self.assertFalse((self.root / target).exists())

    def test_preservation_keeps_exact_bytes_mode_identity_and_directory_context(self):
        result = self.preserve()
        self.assertEqual(result['files'], 3)
        record = migration.load_preserved(self.root)
        self.assertEqual(len(record['original_directories']), 2)
        self.assert_sources()
        self.assert_targets_absent()
        self.assertTrue(migration.verify_preserved(self.root)['original_bytes_and_identity_verified'])
        for entry in record['files']:
            backup = self.root / entry['backup']
            self.assertEqual(backup.read_bytes(), self.original[entry['source']])
            self.assertEqual(backup.stat().st_mode & 0o777, 0o640)
            self.assertIn('inode', entry['identity'])
            self.assertTrue(any(not item['existed'] for item in entry['references']))
        self.assertEqual((self.root / migration.MANIFEST).stat().st_mode & 0o777, 0o600)

    def test_prepare_preserves_sources_and_relocates_links_without_rewriting_prose(self):
        self.prepare()
        record = migration.load_preserved(self.root)
        self.assertEqual(migration.verify_targets(self.root, record), 12)
        self.assert_sources()
        for entry in record['files']:
            before = self.original[entry['source']].decode('utf-8')
            after = (self.root / entry['target']).read_text(encoding='utf-8')
            self.assertEqual(migration.LINK.sub('](REFERENCE)', before),
                             migration.LINK.sub('](REFERENCE)', after))
            self.assertIn('](../../evidence.md:2)', after)
            self.assertIn('](../../_bmad-output/pending_implementation_plan.md:1)', after)
            self.assertEqual((self.root / entry['target']).stat().st_mode & 0o777, 0o640)

    def test_complete_batch_and_cli_audit_have_structured_success(self):
        self.prepare()
        result = migration.retire(self.root)
        self.assertTrue(result['cleanup_ok'])
        self.assertEqual(result['adr_status'], 'PROPOSED')
        for source, _ in migration.FILES:
            self.assertFalse((self.root / source).exists())
        command = subprocess.run([sys.executable, '-B', str(SCRIPT), 'audit',
                                  '--root', str(self.root)], cwd=ROOT,
                                 stdin=subprocess.DEVNULL, capture_output=True,
                                 text=True, timeout=10)
        self.assertEqual(command.returncode, 0, command.stderr)
        self.assertEqual(json.loads(command.stdout)['files'], 3)

    def test_target_conflict_is_rejected_before_any_target_write(self):
        self.preserve()
        target = self.root / migration.FILES[1][1]
        target.parent.mkdir(parents=True)
        target.write_bytes(b'third party content\n')
        with self.assertRaises(migration.BatchError):
            migration.prepare(self.root)
        self.assert_sources()
        self.assertEqual(target.read_bytes(), b'third party content\n')
        self.assertFalse((self.root / migration.FILES[0][1]).exists())

    def test_repeated_preservation_never_overwrites_evidence(self):
        self.preserve()
        before = (self.root / migration.MANIFEST).read_bytes()
        with self.assertRaises(migration.BatchError):
            self.preserve()
        self.assertEqual((self.root / migration.MANIFEST).read_bytes(), before)
        self.assert_sources()

    def test_changed_source_prevents_prepare_without_touching_other_sources(self):
        self.preserve()
        source = migration.FILES[0][0]
        (self.root / source).write_bytes(b'user changed source\n')
        with self.assertRaises(migration.BatchError):
            migration.prepare(self.root)
        self.assert_targets_absent()
        self.assertEqual((self.root / source).read_bytes(), b'user changed source\n')
        for other, _ in migration.FILES[1:]:
            self.assertEqual((self.root / other).read_bytes(), self.original[other])

    def test_equal_bytes_with_replaced_source_identity_are_rejected(self):
        self.preserve()
        source = migration.FILES[0][0]
        path = self.root / source
        replacement = path.with_suffix('.replacement')
        replacement.write_bytes(self.original[source])
        replacement.chmod(0o640)
        replacement.replace(path)
        with self.assertRaises(migration.BatchError):
            migration.prepare(self.root)
        self.assert_sources()
        self.assert_targets_absent()

    def test_corrupt_backup_blocks_prepare_and_restore(self):
        self.preserve()
        entry = migration.load_preserved(self.root)['files'][0]
        (self.root / entry['backup']).write_bytes(b'corrupt preservation\n')
        for action in (migration.prepare, migration.restore):
            with self.subTest(action=action.__name__), self.assertRaises(migration.BatchError):
                action(self.root)
        self.assert_sources()
        self.assert_targets_absent()

    def test_symlink_ancestor_cannot_escape_or_write_outside_batch(self):
        self.preserve()
        outside = self.root / 'outside'
        outside.mkdir()
        (self.root / 'docs').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(migration.BatchError):
            migration.prepare(self.root)
        self.assertEqual(list(outside.iterdir()), [])
        self.assert_sources()

    def test_source_symlink_is_not_accepted_for_preservation(self):
        source = migration.FILES[0][0]
        path = self.root / source
        path.unlink()
        path.symlink_to(self.root / 'evidence.md')
        with self.assertRaises(migration.BatchError):
            self.preserve()
        self.assertFalse((self.root / migration.MANIFEST).exists())

    def test_interrupted_prepare_keeps_saved_target_sources_and_preservation(self):
        self.preserve()
        actual = migration.exclusive_write
        calls = []

        def interrupted(root, relative, data, mode):
            calls.append(relative)
            if len(calls) == 2:
                raise OSError('隔离中断')
            return actual(root, relative, data, mode)

        with mock.patch.object(migration, 'exclusive_write', side_effect=interrupted):
            with self.assertRaises(OSError):
                migration.prepare(self.root)
        self.assert_sources()
        first = self.root / migration.FILES[0][1]
        before = first.read_bytes()
        self.assertFalse((self.root / migration.FILES[1][1]).exists())
        migration.verify_preserved(self.root)
        with self.assertRaises(migration.BatchError):
            migration.prepare(self.root)
        self.assertEqual(first.read_bytes(), before)

    def test_changed_target_prevents_retirement_of_all_sources(self):
        self.prepare()
        target = self.root / migration.FILES[2][1]
        target.write_bytes(b'user modified destination\n')
        with self.assertRaises(migration.BatchError):
            migration.retire(self.root)
        self.assert_sources()
        self.assertEqual(target.read_bytes(), b'user modified destination\n')

    def test_changed_source_after_prepare_prevents_retirement(self):
        self.prepare()
        source = self.root / migration.FILES[2][0]
        source.write_bytes(b'new original version\n')
        with self.assertRaises(migration.BatchError):
            migration.retire(self.root)
        self.assertEqual(source.read_bytes(), b'new original version\n')
        for original, _ in migration.FILES[:2]:
            self.assertEqual((self.root / original).read_bytes(), self.original[original])

    def test_stale_plan_binding_cannot_retire_sources(self):
        self.prepare()
        (self.root / migration.PLAN).write_text('---\nplan_id: other\n---\n契约版本：3\n',
                                               encoding='utf-8')
        with self.assertRaises(migration.BatchError):
            migration.retire(self.root)
        self.assert_sources()

    def test_scope_outside_batch_is_preserved_and_external_change_blocks(self):
        self.prepare()
        protected = self.root / '_bmad-output/adrs/unrelated.md'
        protected.write_bytes(b'user changed unrelated ADR\n')
        with self.assertRaises(migration.BatchError):
            migration.retire(self.root)
        self.assert_sources()
        self.assertEqual(protected.read_bytes(), b'user changed unrelated ADR\n')

    def test_originally_valid_reference_loss_blocks_retirement(self):
        self.prepare()
        (self.root / 'evidence.md').unlink()
        with self.assertRaises(migration.BatchError):
            migration.retire(self.root)
        self.assert_sources()

    def test_restore_missing_sources_exactly_and_keeps_destinations(self):
        self.prepare()
        migration.retire(self.root)
        before = {target: (self.root / target).read_bytes() for _, target in migration.FILES}
        result = migration.restore(self.root)
        self.assertTrue(result['targets_retained'])
        self.assert_sources()
        for target, content in before.items():
            self.assertEqual((self.root / target).read_bytes(), content)

    def test_restore_conflict_never_overwrites_user_source_or_creates_other_sources(self):
        self.prepare()
        migration.retire(self.root)
        source = self.root / migration.FILES[1][0]
        source.write_bytes(b'user recovery content\n')
        with self.assertRaises(migration.BatchError):
            migration.restore(self.root)
        self.assertEqual(source.read_bytes(), b'user recovery content\n')
        self.assertFalse((self.root / migration.FILES[0][0]).exists())

    def test_interrupted_retirement_retains_evidence_and_can_restore_missing_source(self):
        self.prepare()
        actual = Path.unlink
        calls = []

        def interrupted(path, *args, **kwargs):
            if path in [self.root / source for source, _ in migration.FILES]:
                calls.append(path)
                if len(calls) == 2:
                    raise OSError('隔离移除中断')
            return actual(path, *args, **kwargs)

        with mock.patch.object(Path, 'unlink', interrupted):
            with self.assertRaises(OSError):
                migration.retire(self.root)
        self.assertFalse((self.root / migration.FILES[0][0]).exists())
        self.assertTrue((self.root / migration.FILES[1][0]).exists())
        migration.load_preserved(self.root)
        migration.restore(self.root)
        self.assert_sources()

    def test_cli_missing_preservation_reports_blocked_and_keeps_sources(self):
        command = subprocess.run([sys.executable, '-B', str(SCRIPT), 'retire',
                                  '--root', str(self.root)], cwd=ROOT,
                                 stdin=subprocess.DEVNULL, capture_output=True,
                                 text=True, timeout=10)
        self.assertNotEqual(command.returncode, 0)
        self.assertEqual(json.loads(command.stderr)['status'], 'BLOCKED')
        self.assert_sources()
        self.assert_targets_absent()

    def test_new_adr_paths_validate_without_mutating_original_default_or_targets(self):
        self.prepare()
        default = self.root / '_bmad-output/pending_implementation_plan.md'
        before = default.read_bytes()
        data = {
            'plan_id': migration.PLAN_ID, 'status': 'BLOCKED', 'scenario': 'structural',
            'impact_tier': 'M', 'requires_adr': True, 'adr_file': migration.FILES[0][1],
            'supplemental_adrs': [migration.FILES[1][1]], 'session_id': None,
            'verification_type': 'config_syntax', 'verification_command_status': 'AVAILABLE',
            'authorization': '仅隔离契约',
            'verification_command': 'timeout --kill-after=2s 30s python3 check.py < /dev/null',
        }
        targets = {target: (self.root / target).read_bytes() for _, target in migration.FILES}
        fixtures.contracts.validate_plan(data, self.root)
        self.assertEqual(default.read_bytes(), before)
        for target, content in targets.items():
            self.assertEqual((self.root / target).read_bytes(), content)


class ActualBatchContract(unittest.TestCase):
    def test_explicit_contract_and_readme_reference_new_targets_without_permission_expansion(self):
        data = fixtures.contracts.frontmatter((ROOT / migration.PLAN).read_text(encoding='utf-8'))
        self.assertEqual(data['plan_id'], migration.PLAN_ID)
        self.assertEqual(data['adr_file'], migration.FILES[0][1])
        self.assertEqual(data['supplemental_adrs'], [migration.FILES[1][1]])
        self.assertEqual(data['status'], 'BLOCKED')
        self.assertIsNone(data['session_id'])
        self.assertIn('](' + migration.FILES[1][1] + ':1)',
                      (ROOT / 'README.md').read_text(encoding='utf-8'))
        modes = fixtures.source_modes()
        fixtures.contracts.validate_modes(modes)
        pattern = re.compile(modes['customModes'][0]['groups'][1][1]['fileRegex'])
        for _, target in migration.FILES:
            self.assertIsNone(pattern.search(target))
        self.assertNotIn('command', modes['customModes'][0]['groups'])

    def test_actual_preservation_valid_and_current_phase_consistent(self):
        record = migration.load_preserved(ROOT)
        targets = [(ROOT / target).exists() for _, target in migration.FILES]
        sources = [(ROOT / source).exists() for source, _ in migration.FILES]
        self.assertTrue(all(sources) or all(targets), '不得接受缺少完整源及目标的批次')
        if all(sources):
            migration.verify_sources(ROOT, record)
        if all(targets):
            self.assertGreater(migration.verify_targets(ROOT, record), 0)
        if not any(sources):
            self.assertTrue(migration.audit(ROOT)['cleanup_ok'])


if __name__ == '__main__':
    unittest.main()
