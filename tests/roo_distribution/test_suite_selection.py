"""显式套件选择与受管回切；仅操作项目内夹具仓库及临时部署根。"""
import json
import shutil
import sys
import unittest

import yaml

import test_gitops_dry_run as fixtures


class SuiteSelection(unittest.TestCase):
    setUp = fixtures.GitOpsDryRun.setUp
    run_command = fixtures.GitOpsDryRun.run_command
    git = fixtures.GitOpsDryRun.git
    tree = fixtures.GitOpsDryRun.tree
    MANIFEST = '.gemini/config/plugins/bmad-suite/.manifest.json'

    def add_v5(self, committed=False):
        shutil.copytree(
            fixtures.ROOT / 'bmralph-suite-v5', self.repo / 'bmralph-suite-v5',
            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'),
        )
        if committed:
            self.git('add', 'bmralph-suite-v5')
            self.git('-c', 'commit.gpgsign=false', 'commit', '-m', 'fixture V5 suite')

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

    def test_new_install_defaults_to_v4_even_when_v5_is_available(self):
        self.add_v5()
        manifest = self.deploy()
        self.assertEqual(manifest['major_version'], 'v4')
        self.assertEqual(manifest['suite_id'], 'bmad-suite-v4')
        self.assertEqual(manifest['source_path'], 'bmad-suite-v4')
        self.assertFalse((self.target / '.gemini/config/plugins/bmad-suite/suite.json').exists())

    def test_explicit_v5_then_implicit_deployment_preserves_v5(self):
        self.add_v5()
        first = self.deploy('--suite', 'v5')
        self.assertEqual(first['major_version'], 'v5')
        self.assertEqual(first['suite_id'], 'bmralph-suite-v5')
        self.assertEqual(first['source_path'], 'bmralph-suite-v5')
        before = self.tree(self.target)
        second = self.deploy()
        self.assertEqual(second, first)
        self.assertEqual(self.tree(self.target), before,
                         '省略版本不得回切 V4 或重写幂等部署')

    def test_implicit_latest_handoff_preserves_committed_v5(self):
        self.add_v5(committed=True)
        self.deploy('v5')
        result = self.run_command(['bash', 'bs.sh', '--latest'])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count('显式移交磁盘新版部署入口'), 1)
        manifest = json.loads((self.target / self.MANIFEST).read_bytes())
        self.assertEqual(manifest['major_version'], 'v5')
        self.assertEqual(manifest['source_path'], 'bmralph-suite-v5')

    def test_conflicting_versions_and_tags_fail_before_side_effects(self):
        for arguments in (
            ('v4', 'v5'),
            ('--suite', 'v5', '--v4'),
            ('--update', 'v3', 'v4'),
            ('--tag', 'fixture-release', '--tag', 'other-release'),
            ('v5', '--tag', 'v4.1.0'),
        ):
            with self.subTest(arguments=arguments):
                self.assert_rejected_without_changes(*arguments)

    def test_missing_selected_v5_does_not_use_v4_or_generic_suite(self):
        shutil.copytree(self.repo / 'bmad-suite-v4', self.repo / 'bmad-suite')
        result = self.assert_rejected_without_changes('v5')
        self.assertIn('不回退', result.stderr)

    def test_untrusted_existing_assets_block_implicit_update_before_git_changes(self):
        path = self.target / '.gemini/config/plugins/bmad-suite/plugin.json'
        path.parent.mkdir(parents=True)
        path.write_bytes(b'{"name":"bmad-suite"}\n')
        result = self.assert_rejected_without_changes('--update')
        self.assertIn('所有权清单', result.stderr)

    def test_v4_v5_v4_roundtrip_preserves_third_party_assets_and_modes(self):
        self.add_v5()
        mode_relative = 'personal profile/settings/custom_modes.yaml'
        mode_path = self.target / mode_relative
        mode_path.parent.mkdir(parents=True)
        mode_path.write_text(
            'theme: dark\ncustomModes: [{slug: personal, name: Personal}]\n',
            encoding='utf-8',
        )
        unrelated = self.target / '.gemini/config/plugins/bmad-suite/personal.txt'
        unrelated.parent.mkdir(parents=True)
        unrelated.write_bytes(b'preserve personal asset\n')
        arguments = ('--mode-target', mode_relative)
        self.deploy('v4', *arguments)
        self.deploy('v5', *arguments)
        identity = self.target / '.gemini/config/plugins/bmad-suite/suite.json'
        self.assertTrue(identity.is_file())
        self.assertEqual(yaml.safe_load(mode_path.read_bytes())['customModes'][0]['slug'],
                         'personal')
        manifest = self.deploy('v4', *arguments)
        self.assertEqual(manifest['major_version'], 'v4')
        self.assertFalse(identity.exists(), '回切只清理已确认所有权的 V5 退役资产')
        self.assertEqual(unrelated.read_bytes(), b'preserve personal asset\n')
        modes = yaml.safe_load(mode_path.read_bytes())
        self.assertEqual(modes['theme'], 'dark')
        self.assertEqual(next(item for item in modes['customModes']
                              if item['slug'] == 'personal')['name'], 'Personal')
        self.assertEqual((self.target / '.roo/rules/02-bmad-core.md').read_bytes(),
                         (self.repo / 'bmad-suite-v4/roo/rules/02-bmad-core.md').read_bytes())

    def test_modified_v5_asset_blocks_explicit_v4_roundtrip(self):
        self.add_v5()
        self.deploy('v5')
        path = self.target / '.gemini/config/plugins/bmad-suite/suite.json'
        path.write_bytes(path.read_bytes() + b'\n')
        result = self.assert_rejected_without_changes('v4')
        self.assertIn('suite.json', result.stdout + result.stderr)

    def test_v5_preflight_has_no_asset_cache_or_task_start_side_effects(self):
        self.add_v5()
        before_repo = self.tree(self.repo)
        before_target = self.tree(self.target)
        result = self.run_command(['bash', 'bs.sh', 'v5', '--preflight'])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.tree(self.repo), before_repo)
        self.assertEqual(self.tree(self.target), before_target)
        self.assertIn('未执行写入', result.stdout)
        self.assertFalse((self.repo / '.versions').exists())


    def test_deployed_v5_runtime_is_self_contained_and_install_does_not_start_tasks(self):
        self.add_v5()
        source = self.repo / 'bmralph-suite-v5'
        before_source = self.tree(source)
        manifest = self.deploy('v5')
        self.assertEqual(manifest['major_version'], 'v5')
        plugin = self.target / '.gemini/config/plugins/bmad-suite'
        scripts = source / 'scripts'
        source_scripts = sorted(scripts.glob('*.py'))
        self.assertTrue(source_scripts, '运行资产缺失不能视为分发通过')
        for path in source_scripts:
            deployed = plugin / 'scripts' / path.name
            self.assertTrue(deployed.is_file(), path.name)
            self.assertEqual(deployed.read_bytes(), path.read_bytes(), path.name)
        for name in ('bmad-exec.py', 'bmad_context.py', 'bmad_context_inputs.py',
                     'bmad_state.py', 'bmad_execution.py', 'bmad_environment.py',
                     'bmad_supervisor.py', 'bmad_test_runner.py'):
            self.assertTrue((plugin / 'scripts' / name).is_file(), name)
        self.assertEqual(self.tree(source), before_source)
        self.assertFalse((self.target / '.bmad-control').exists())
        self.assertFalse((self.target / '.bmad-runtime').exists())
        self.assertFalse((plugin / '.bmad-control').exists())
        self.assertFalse((plugin / '.bmad-runtime').exists())
        before_target = self.tree(self.target)
        before_home = self.tree(self.home)
        before_repo = self.tree(self.repo)
        cli = plugin / 'scripts/bmad-exec.py'
        result = self.run_command([sys.executable, '-B', str(cli), '--help'])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('assemble-input', result.stdout)
        self.assertIn('render-state', result.stdout)
        self.assertNotIn('race-test', result.stdout)
        self.assertEqual(self.tree(self.target), before_target)
        self.assertEqual(self.tree(self.home), before_home)
        self.assertEqual(self.tree(self.repo), before_repo)

        workspace = self.sandbox / 'runtime workspace'
        workspace.mkdir()
        verification = {
            'operation': 'unit-test',
            'environment_file': '.bmad-control/environment.json',
            'directory': 'tests', 'pattern': 'test_sample.py',
            'minimum_tests': 1, 'required_tests': [], 'inputs': [],
        }
        data = {
            'schema_version': 1, 'plan_id': 'DISTRIBUTION-LOCAL-01',
            'tasks': [
                {'task_id': 'T1', 'title': '当前任务', 'depends_on': [],
                 'status': 'PENDING', 'verification': verification,
                 'verdict_file': None},
                {'task_id': 'T2', 'title': '保留未完成任务', 'depends_on': ['T1'],
                 'status': 'PENDING', 'verification': verification,
                 'verdict_file': None},
            ],
        }
        (workspace / 'plan.md').write_text(
            '---\nplan_id: "DISTRIBUTION-LOCAL-01"\nstatus: READY\n---\n\n'
            '# 临时分发验证夹具\n\n```bmad-tasks\n' +
            json.dumps(data, ensure_ascii=False) + '\n```\n', encoding='utf-8',
        )
        before_workspace = self.tree(workspace)
        result = self.run_command([
            sys.executable, '-B', str(cli), 'render-state',
            '--workspace', str(workspace), '--plan-file', 'plan.md',
        ])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(result.stdout.splitlines()), 1)
        self.assertLessEqual(len(result.stdout.encode('utf-8')), 16384)
        projected = json.loads(result.stdout)
        self.assertEqual(projected['status'], 'READY')
        self.assertEqual(projected['ready_tasks'], ['T1'])
        self.assertEqual(projected['unfinished_count'], 2)
        self.assertIn('T2 [PENDING]', projected['view'])
        self.assertIs(projected['business_reexecuted'], False)
        self.assertIs(projected['state_saved'], False)
        self.assertEqual(self.tree(workspace), before_workspace)
        self.assertEqual(self.tree(self.target), before_target)
        self.assertEqual(self.tree(self.home), before_home)
        self.assertEqual(self.tree(self.repo), before_repo)
        # 仅证明临时根分发和已部署只读入口；不证明宿主加载、权限或 Agent 运行。


if __name__ == '__main__':
    unittest.main()
