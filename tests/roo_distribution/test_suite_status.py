"""部署身份诊断及机器接口；仅操作项目内独立仓库和临时部署根。"""
import hashlib
import json
import shutil
import unittest

import test_gitops_dry_run as fixtures


class SuiteStatus(unittest.TestCase):
    setUp = fixtures.GitOpsDryRun.setUp
    run_command = fixtures.GitOpsDryRun.run_command
    git = fixtures.GitOpsDryRun.git
    tree = fixtures.GitOpsDryRun.tree
    RELATIVE = '.gemini/config/plugins/bmad-suite/.manifest.json'

    def deploy(self):
        result = self.run_command([
            'python3', '-B', 'scripts/deploy-managed-cli.py',
            '--root', str(self.target), '--repository', str(self.repo),
            '--source', str(self.repo / 'bmad-suite-v4'),
        ])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def status(self, machine=False):
        before = self.tree(self.target)
        args = ['python3', '-B', 'scripts/deployment-status.py',
                '--root', str(self.target)]
        if machine:
            args.append('--active-suite')
        result = self.run_command(args)
        self.assertEqual(self.tree(self.target), before)
        return result

    def revise_provenance_fixture(self, mutate):
        # 模拟合法的旧格式记录或一致性矛盾，不伪称正常资产防篡改。
        path = self.target / self.RELATIVE
        data = json.loads(path.read_bytes())
        mutate(data)
        content = (json.dumps(data, sort_keys=True) + '\n').encode('utf-8')
        path.write_bytes(content)
        owner_path = self.target / '.bmad-solo-deployment/ownership.json'
        owner = json.loads(owner_path.read_bytes())
        owner['files'][self.RELATIVE]['sha256'] = hashlib.sha256(content).hexdigest()
        owner_path.write_text(json.dumps(owner), encoding='utf-8')

    def test_v4_identity_and_uncommitted_source_are_reported(self):
        source = self.repo / 'bmad-suite-v4/roo/rules/02-bmad-core.md'
        source.write_bytes(source.read_bytes() + b'\n<!-- fixture source change -->\n')
        self.deploy()
        result = self.status()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('bmad-suite-v4', result.stdout)
        self.assertIn('套件主版本：v4', result.stdout)
        self.assertIn('套件源差异状态：有差异', result.stdout)
        machine = self.status(machine=True)
        self.assertEqual(machine.returncode, 0, machine.stderr)
        self.assertEqual(machine.stdout, 'v4\n')

    def test_legacy_v4_without_new_fields_is_identified_without_writes(self):
        self.deploy()
        def legacy(data):
            for key in ('suite_id', 'major_version', 'source_path'):
                del data[key]
        self.revise_provenance_fixture(legacy)
        result = self.status(machine=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'v4\n')

    def test_unknown_legacy_source_is_not_defaulted(self):
        self.deploy()
        def unknown(data):
            for key in ('suite_id', 'major_version', 'source_path'):
                del data[key]
            data['source_directory'] = str(self.repo / 'generic-suite')
        self.revise_provenance_fixture(unknown)
        result = self.status()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('套件身份：未知', result.stdout)
        machine = self.status(machine=True)
        self.assertNotEqual(machine.returncode, 0)
        self.assertEqual(machine.stdout, '')
        self.assertIn('显式选择', machine.stderr)

    def test_retired_identity_is_rejected_even_with_matching_owner_digest(self):
        self.deploy()
        self.revise_provenance_fixture(lambda data: data.update(major_version='v5'))
        result = self.status(machine=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')
        self.assertIn('退役', result.stderr)
        before_repo, before_target = self.tree(self.repo), self.tree(self.target)
        for arguments in ((), ('v4',), ('--suite', 'v4'), ('--update',)):
            with self.subTest(arguments=arguments):
                rejected = self.run_command(['bash', 'bs.sh', *arguments])
                self.assertNotEqual(rejected.returncode, 0)
                self.assertEqual(self.tree(self.repo), before_repo)
                self.assertEqual(self.tree(self.target), before_target)

    def test_partial_optional_identity_cannot_downgrade_to_legacy_v4(self):
        source = self.repo / 'bmad-suite-v4/suite.json'
        source.write_text(json.dumps({
            'schema_version': 1, 'suite_id': 'bmad-suite-v4',
            'major_version': 'v4', 'source_path': 'bmad-suite-v4',
        }), encoding='utf-8')
        self.deploy()
        self.revise_provenance_fixture(lambda data: data['source_files'].pop('suite.json'))
        result = self.status(machine=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')
        self.assertIn('存在性不一致', result.stderr)
        before_repo, before_target = self.tree(self.repo), self.tree(self.target)
        for arguments in ((), ('v4',), ('--update',)):
            with self.subTest(arguments=arguments):
                rejected = self.run_command(['bash', 'bs.sh', *arguments])
                self.assertNotEqual(rejected.returncode, 0)
                self.assertEqual(self.tree(self.repo), before_repo)
                self.assertEqual(self.tree(self.target), before_target)

    def test_modified_v4_plugin_cannot_produce_machine_version(self):
        self.deploy()
        path = self.target / '.gemini/config/plugins/bmad-suite/plugin.json'
        path.write_bytes(b'{}\n')
        result = self.status(machine=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')

    def test_absent_deployment_has_no_machine_version(self):
        result = self.status(machine=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
