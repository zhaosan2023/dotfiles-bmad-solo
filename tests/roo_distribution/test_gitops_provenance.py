"""部署来源契约：记录实际源提交与源工作树状态，不误用当前 HEAD。"""
import json
import unittest

import test_gitops_dry_run as fixtures


class GitOpsProvenance(unittest.TestCase):
    setUp = fixtures.GitOpsDryRun.setUp
    run_command = fixtures.GitOpsDryRun.run_command
    git = fixtures.GitOpsDryRun.git
    tree = fixtures.GitOpsDryRun.tree

    def deploy_and_read_manifest(self, *arguments):
        result = self.run_command(['bash', 'bs.sh', *arguments])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        path = self.target / '.gemini/config/plugins/bmad-suite/.manifest.json'
        self.assertTrue(path.is_file(), '成功分发必须产生受管部署来源清单')
        return json.loads(path.read_bytes())

    def test_clean_worktree_records_actual_commit_and_is_idempotent(self):
        commit = self.git('rev-parse', 'HEAD').strip()
        manifest = self.deploy_and_read_manifest()
        self.assertEqual(manifest['source_commit'], commit)
        self.assertIs(manifest['source_dirty'], False)
        self.assertEqual(manifest['source_repository'], str(self.repo))
        before = self.tree(self.target)
        self.deploy_and_read_manifest()
        self.assertEqual(self.tree(self.target), before,
                         '相同来源与资产的重复部署不得仅因时间变化重写清单')

    def test_modified_source_records_dirty_state_and_deploys_actual_bytes(self):
        commit = self.git('rev-parse', 'HEAD').strip()
        source = self.repo / 'bmad-suite-v4/roo/rules/02-bmad-core.md'
        updated = source.read_bytes() + b'\n<!-- uncommitted fixture -->\n'
        source.write_bytes(updated)
        manifest = self.deploy_and_read_manifest()
        self.assertEqual(manifest['source_commit'], commit)
        self.assertIs(manifest['source_dirty'], True,
                      '未提交源改动不能被描述为纯提交快照')
        deployed = self.target / '.roo/rules/02-bmad-core.md'
        self.assertEqual(deployed.read_bytes(), updated)

    def test_tag_snapshot_records_selected_commit_not_current_head(self):
        selected = self.git('rev-parse', 'fixture-release^{commit}').strip()
        source = self.repo / 'bmad-suite-v4/roo/rules/02-bmad-core.md'
        original = source.read_bytes()
        source.write_bytes(original + b'\n<!-- later commit -->\n')
        self.git('add', 'bmad-suite-v4/roo/rules/02-bmad-core.md')
        self.git('-c', 'commit.gpgsign=false', 'commit', '-m', 'later source')
        self.assertNotEqual(self.git('rev-parse', 'HEAD').strip(), selected)
        manifest = self.deploy_and_read_manifest('--tag', 'fixture-release')
        self.assertEqual(manifest['source_commit'], selected,
                         '标签部署来源必须绑定已核验缓存提交，而非当前 HEAD')
        self.assertIs(manifest['source_dirty'], False,
                      '已核验标签快照不应因缓存目录未跟踪而标记为脏源')
        self.assertEqual(manifest['source_repository'], str(self.repo))
        deployed = self.target / '.roo/rules/02-bmad-core.md'
        self.assertEqual(deployed.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
