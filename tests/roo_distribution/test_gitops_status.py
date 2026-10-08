"""状态诊断须读取指定部署根目录、识别受管漂移，且不修改目标。"""
import json
import unittest

import yaml

import test_asset_safety_shell as fixtures


class GitOpsStatus(unittest.TestCase):
    setUp = fixtures.ShellEntrySafety.setUp
    run_shell = fixtures.ShellEntrySafety.run_shell
    tree = fixtures.ShellEntrySafety.tree

    def install_fixture(self):
        result = self.run_shell()
        self.assertEqual(result.returncode, 0, result.stderr)

    def inspect_without_writes(self):
        before = self.tree()
        result = self.run_shell('--status')
        self.assertEqual(self.tree(), before,
                         '状态诊断不得修改部署文件、清单、锁或事务日志')
        self.assertEqual(list(self.home.iterdir()), [])
        return result

    def test_status_uses_explicit_deployment_root(self):
        self.install_fixture()
        result = self.inspect_without_writes()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(self.target), result.stdout,
                      '状态必须报告实际部署根目录，而非默认全局目录')
        self.assertNotIn('Rules active at', result.stdout,
                         '文件存在不能证明运行时规则已激活')

    def test_modified_managed_file_reports_drift(self):
        self.install_fixture()
        relative = '.roo/rules/02-bmad-core.md'
        (self.target / relative).write_bytes(b'user modified rule\n')
        result = self.inspect_without_writes()
        self.assertNotEqual(result.returncode, 0,
                            '受管文件漂移必须返回非零状态')
        self.assertIn(relative, result.stdout + result.stderr)

    def test_missing_managed_file_reports_drift(self):
        self.install_fixture()
        relative = '.roo/rules/02-bmad-core.md'
        (self.target / relative).unlink()
        result = self.inspect_without_writes()
        self.assertNotEqual(result.returncode, 0,
                            '受管文件缺失必须返回非零状态')
        self.assertIn(relative, result.stdout + result.stderr)

    def test_modified_managed_mode_reports_drift(self):
        self.install_fixture()
        data = yaml.safe_load(self.mode.read_bytes())
        for mode in data['customModes']:
            if mode['slug'] == 'bmad-engineer':
                mode['name'] = 'User modified engineer'
                break
        else:
            self.fail('夹具部署未生成受管工程模式')
        self.mode.write_text(yaml.safe_dump(data), encoding='utf-8')
        result = self.inspect_without_writes()
        self.assertNotEqual(result.returncode, 0,
                            '受管模式语义漂移必须返回非零状态')
        self.assertIn('bmad-engineer', result.stdout + result.stderr)

    def test_third_party_configuration_change_is_not_managed_drift(self):
        self.install_fixture()
        data = yaml.safe_load(self.mode.read_bytes())
        data['theme'] = 'light'
        for mode in data['customModes']:
            if mode['slug'] == 'personal':
                mode['name'] = 'Updated personal mode'
        self.mode.write_text(yaml.safe_dump(data), encoding='utf-8')
        result = self.inspect_without_writes()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(str(self.target), result.stdout)


    def test_status_reports_recorded_source_without_claiming_live_sync(self):
        self.install_fixture()
        relative = '.gemini/config/plugins/bmad-suite/.manifest.json'
        provenance = json.loads((self.target / relative).read_bytes())
        self.assertIsInstance(provenance['source_commit'], str)
        result = self.inspect_without_writes()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(provenance['source_commit'], result.stdout)
        self.assertIn(provenance['source_repository'], result.stdout)
        self.assertIn('未核验来源仓库当前状态', result.stdout)

    def test_modified_provenance_is_rejected_without_reporting_trusted_source(self):
        self.install_fixture()
        relative = '.gemini/config/plugins/bmad-suite/.manifest.json'
        path = self.target / relative
        provenance = json.loads(path.read_bytes())
        provenance['source_commit'] = 'f' * 40
        path.write_text(json.dumps(provenance), encoding='utf-8')
        result = self.inspect_without_writes()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(relative, result.stderr)
        self.assertNotIn('f' * 40, result.stdout)


if __name__ == '__main__':
    unittest.main()
