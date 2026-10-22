"""显式 V5→V4 退役迁移；全部真实事务在项目内隔离夹具执行。"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

import yaml
import test_gitops_dry_run as fixtures

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from asset_safety import AssetError, Snapshot, deployment_lock, snapshot
from deploy_managed import deploy, load_manifest
from deployment_provenance import MANIFEST_TARGET, build_manifest
from deployment_source import collect_source
from managed_files import ownership_record

specification = importlib.util.spec_from_file_location(
    'retired_migration', ROOT / 'scripts/migrate-retired-deployment.py',
)
migration = importlib.util.module_from_spec(specification)
specification.loader.exec_module(migration)


class RetiredDeploymentMigration(unittest.TestCase):
    setUp = fixtures.GitOpsDryRun.setUp
    run_command = fixtures.GitOpsDryRun.run_command
    git = fixtures.GitOpsDryRun.git
    tree = fixtures.GitOpsDryRun.tree
    MODE = 'personal profile/settings/custom_modes.yaml'
    RETIRED = 'scripts/retired-must-not-run.py'

    def seed_retired(self, *, identity=True, modes=True):
        mode = self.target / self.MODE
        mode.parent.mkdir(parents=True)
        mode.write_bytes(b'theme: dark\ncustomModes: [{slug: personal, name: Personal}]\n')
        files, selected, sources = collect_source(
            self.repo / 'bmad-suite-v4', (self.MODE,) if modes else (),
        )
        retired = {
            'schema_version': 1, 'suite_id': 'bmralph-suite-v5',
            'major_version': 'v5', 'source_path': 'bmralph-suite-v5',
        }
        if identity:
            sources['suite.json'] = Snapshot(json.dumps(retired).encode(), 0o600)
        sources[self.RETIRED] = Snapshot(
            b"raise RuntimeError('retired code must never execute')\n", 0o600,
        )
        for name in ('suite.json', self.RETIRED):
            if name in sources:
                files['.gemini/config/plugins/bmad-suite/' + name] = sources[name]
        # 构造旧版本磁盘契约，不引入或执行旧套件运行依赖。
        provenance = json.loads(build_manifest(
            self.repo / 'bmad-suite-v4', sources, files, selected,
            repository=self.repo,
        ).content)
        provenance.update(retired)
        provenance['source_directory'] = str(self.repo / 'bmralph-suite-v5')
        files[MANIFEST_TARGET] = Snapshot(json.dumps(provenance).encode(), 0o600)
        deploy(self.target, self.target / '.bmad-solo-deployment', files, selected)
        personal = self.target / '.gemini/config/plugins/bmad-suite/personal.txt'
        personal.write_bytes(b'keep third-party asset\n')
        return provenance

    def run_migration(self, *arguments):
        return self.run_command([
            sys.executable, '-B', 'scripts/migrate-retired-deployment.py',
            '--root', str(self.target), '--repository', str(self.repo),
            '--from', 'v5', '--to', 'v4', *arguments,
        ])

    def assert_rejected_unchanged(self, *arguments):
        before_repo, before_target = self.tree(self.repo), self.tree(self.target)
        result = self.run_migration(*arguments)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.tree(self.repo), before_repo)
        self.assertEqual(self.tree(self.target), before_target)
        return result

    def test_read_only_preflight_and_success_preserve_personal_assets(self):
        self.seed_retired()
        before_repo, before_target = self.tree(self.repo), self.tree(self.target)
        preflight = self.run_migration('--preflight')
        self.assertEqual(preflight.returncode, 0, preflight.stdout + preflight.stderr)
        self.assertEqual(self.tree(self.repo), before_repo)
        self.assertEqual(self.tree(self.target), before_target)
        self.assertIn('未创建锁、事务或任务', preflight.stdout)
        result = self.run_migration()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('受管退役事务完成', result.stdout)
        self.assertEqual(self.tree(self.repo), before_repo)
        provenance = json.loads((self.target / MANIFEST_TARGET).read_bytes())
        self.assertEqual(provenance['major_version'], 'v4')
        self.assertEqual(provenance['source_path'], 'bmad-suite-v4')
        self.assertEqual(provenance['source_directory'], str(self.repo / 'bmad-suite-v4'))
        self.assertFalse((self.target / '.gemini/config/plugins/bmad-suite' / self.RETIRED).exists())
        self.assertEqual((self.target / '.gemini/config/plugins/bmad-suite/personal.txt').read_bytes(),
                         b'keep third-party asset\n')
        data = yaml.safe_load((self.target / self.MODE).read_bytes())
        self.assertEqual(data['theme'], 'dark')
        self.assertIn({'slug': 'personal', 'name': 'Personal'}, data['customModes'])
        for path in (self.repo, self.target):
            self.assertFalse((path / '.bmad-control').exists())
            self.assertFalse((path / '.bmad-runtime').exists())
        status = self.run_command([
            sys.executable, '-B', 'scripts/deployment-status.py',
            '--root', str(self.target), '--active-suite',
        ])
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertEqual(status.stdout.strip(), 'v4')
        self.assert_rejected_unchanged()
        before = self.tree(self.target)
        repeated = self.run_command(['bash', 'bs.sh', '--mode-target', self.MODE])
        self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
        self.assertEqual(self.tree(self.target), before)

    def test_ordinary_deployment_keeps_retired_rejection(self):
        self.seed_retired()
        for arguments in ((), ('v4',), ('--preflight',), ('--update',)):
            with self.subTest(arguments=arguments):
                before_repo, before_target = self.tree(self.repo), self.tree(self.target)
                result = self.run_command(['bash', 'bs.sh', *arguments])
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.tree(self.repo), before_repo)
                self.assertEqual(self.tree(self.target), before_target)
                self.assertIn('仅支持 V4', result.stderr)

    def test_modified_owned_file_blocks_without_changes(self):
        self.seed_retired()
        path = self.target / '.roo/rules/02-bmad-core.md'
        path.write_bytes(path.read_bytes() + b'\n# user edit\n')
        self.assert_rejected_unchanged()

    def test_modified_owned_mode_blocks_without_changes(self):
        self.seed_retired()
        path = self.target / self.MODE
        data = yaml.safe_load(path.read_bytes())
        next(item for item in data['customModes'] if item['slug'] == 'bmad-engineer')['name'] = 'User edited'
        path.write_text(yaml.safe_dump(data), encoding='utf-8')
        self.assert_rejected_unchanged()

    def test_corrupt_or_partial_identity_blocks_without_changes(self):
        self.seed_retired()
        path = self.target / MANIFEST_TARGET
        provenance = json.loads(path.read_bytes())
        provenance['suite_id'] = 'unknown'
        path.write_bytes(json.dumps(provenance).encode())
        ownership = self.target / '.bmad-solo-deployment/ownership.json'
        data = load_manifest(ownership.read_bytes())
        data['files'][MANIFEST_TARGET] = ownership_record(snapshot(path))
        ownership.write_bytes(json.dumps(data).encode())
        self.assert_rejected_unchanged()

    def test_missing_suite_identity_blocks_without_changes(self):
        self.seed_retired(identity=False)
        result = self.assert_rejected_unchanged()
        self.assertIn('suite.json', result.stderr)

    def test_missing_mode_target_blocks_without_changes(self):
        self.seed_retired(modes=False)
        self.assert_rejected_unchanged()

    def test_target_expansion_or_duplicate_blocks_without_changes(self):
        self.seed_retired()
        self.assert_rejected_unchanged('--mode-target', 'another/settings/custom_modes.yaml')
        self.assert_rejected_unchanged('--mode-target', self.MODE, '--mode-target', self.MODE)

    def test_missing_lock_blocks_without_recreating_it(self):
        self.seed_retired()
        (self.target / '.bmad-solo-deployment/deployment.lock').unlink()
        self.assert_rejected_unchanged()

    def test_active_lock_blocks_without_changes(self):
        self.seed_retired()
        with deployment_lock(self.target / '.bmad-solo-deployment/deployment.lock', create=False):
            self.assert_rejected_unchanged()

    def test_unfinished_transaction_blocks_without_changes(self):
        self.seed_retired()
        directory = self.target / '.bmad-solo-deployment/transaction-incomplete'
        directory.mkdir()
        (directory / 'transaction.json').write_bytes(b'{"status":"PREPARED"}')
        self.assert_rejected_unchanged()

    def test_unfinished_task_cleanup_blocks_without_changes(self):
        self.seed_retired()
        directory = self.target / '.bmad-solo-deployment/task-runs'
        directory.mkdir()
        run_id = 'a' * 32
        (directory / (run_id + '.json')).write_text(json.dumps({
            'schema_version': 1, 'run_id': run_id, 'workspace': str(self.repo),
            'run_copy_file': '.bmad-control/run-copies/' + run_id + '/binding.json',
            'status': 'EXECUTING', 'cleanup_ok': False, 'final_receipt': None,
        }), encoding='utf-8')
        self.assert_rejected_unchanged('--preflight')
        self.assert_rejected_unchanged()

    def test_missing_v4_source_blocks_without_changes(self):
        self.seed_retired()
        (self.repo / 'bmad-suite-v4').rename(self.repo / 'missing-v4')
        self.assert_rejected_unchanged()

    def test_new_unknown_collision_is_not_adopted(self):
        self.seed_retired()
        source = self.repo / 'bmad-suite-v4/personal.txt'
        source.write_bytes(b'not the user asset\n')
        self.assert_rejected_unchanged()

    def test_ownership_race_is_rejected_before_transaction(self):
        self.seed_retired()
        original = migration.inspect_retired
        calls = []
        path = self.target / '.bmad-solo-deployment/ownership.json'
        def changed_after_inspection(root):
            original(root)
            calls.append(root)
            if len(calls) == 1:
                path.write_bytes(path.read_bytes() + b'\n')
        with mock.patch.object(migration, 'inspect_retired', side_effect=changed_after_inspection), \
                mock.patch.object(migration, 'deploy') as operation, \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(AssetError):
            migration.migrate(self.target, self.repo)
        operation.assert_not_called()

    def test_transaction_failure_rolls_back_business_assets(self):
        self.seed_retired()
        before = self.tree(self.target)
        import asset_transaction
        original = asset_transaction.apply_snapshot
        calls = []
        def fail_once(path, expected, desired):
            calls.append(path)
            if len(calls) == 2:
                raise OSError('injected business target commit failure')
            return original(path, expected, desired)
        # 在首个业务目标已修改后注入失败，不误伤备份准备或日志写入。
        with mock.patch.object(asset_transaction, 'apply_snapshot', side_effect=fail_once), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(asset_transaction.TransactionError):
            migration.migrate(self.target, self.repo)
        self.assertGreaterEqual(len(calls), 3, '必须实际尝试提交并恢复已修改目标')
        after = self.tree(self.target)
        self.assertEqual({key: value for key, value in after.items()
                          if not key.startswith('.bmad-solo-deployment/transaction-')},
                         {key: value for key, value in before.items()
                          if not key.startswith('.bmad-solo-deployment/transaction-')})
        records = list((self.target / '.bmad-solo-deployment').glob('transaction-*/transaction.json'))
        self.assertGreaterEqual(len(records), 2)
        self.assertIn('ROLLED_BACK', [json.loads(path.read_bytes())['status'] for path in records])


if __name__ == '__main__':
    unittest.main()
