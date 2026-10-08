"""版本切换失败关闭测试；仅使用独立仓库与项目内部署目标。"""
import unittest

from test_gitops_dry_run import GitOpsDryRun


class GitOpsSwitchSafety(GitOpsDryRun):
    def assert_rejected_without_changes(self, *arguments):
        before_repo = self.tree(self.repo)
        before_target = self.tree(self.target)
        result = self.run_command(["bash", "bs.sh", *arguments])
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.tree(self.repo), before_repo,
                         "拒绝操作前不得修改仓库、引用或缓存")
        self.assertEqual(self.tree(self.target), before_target,
                         "拒绝操作不得修改部署目标")
        return result

    def test_dirty_latest_rejected_before_switching(self):
        self.git("checkout", "-b", "fixture-feature")
        source = self.repo / "bmad-suite-v4/plugin.json"
        source.write_bytes(source.read_bytes() + b"\n")
        self.assert_rejected_without_changes("--latest")
        self.assertEqual(self.git("branch", "--show-current").strip(),
                         "fixture-feature")

    def test_dirty_update_rejected_before_fetch(self):
        source = self.repo / "bmad-suite-v4/plugin.json"
        source.write_bytes(source.read_bytes() + b"\n")
        self.assert_rejected_without_changes("--update")
        self.assertFalse((self.repo / ".git/FETCH_HEAD").exists())

    def test_untracked_asset_blocks_latest(self):
        self.git("checkout", "-b", "fixture-feature")
        (self.repo / "personal.txt").write_bytes(b"preserve user work\n")
        self.assert_rejected_without_changes("--latest")

    def test_tag_and_latest_rejected_before_cache_creation(self):
        self.assert_rejected_without_changes(
            "--tag", "fixture-release", "--latest"
        )
        self.assertFalse((self.repo / ".versions").exists())

    def test_tag_and_update_rejected_before_remote_access(self):
        self.assert_rejected_without_changes(
            "--tag", "fixture-release", "--update"
        )
        self.assertFalse((self.repo / ".git/FETCH_HEAD").exists())


    def test_missing_main_rejected_without_deployment(self):
        self.git("branch", "-m", "fixture-only")
        self.assert_rejected_without_changes("--latest")
        self.assertEqual(self.git("branch", "--show-current").strip(),
                         "fixture-only")

    def test_detached_latest_actually_selects_main(self):
        self.git("checkout", "--detach", "HEAD")
        result = self.run_command(["bash", "bs.sh", "--latest"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git("branch", "--show-current").strip(), "main",
                         "成功提示必须对应真实分支切换，不能停留在游离状态")
        self.assertTrue((self.target / ".roo/rules/02-bmad-core.md").is_file())


    def prepare_local_remote_update(self):
        remote = self.sandbox / "remote.git"
        self.git("clone", "--bare", str(self.repo), str(remote))
        self.git("remote", "add", "origin", str(remote))
        self.git("checkout", "-b", "fixture-upstream")
        rule = self.repo / "bmad-suite-v4/roo/rules/02-bmad-core.md"
        updated = rule.read_bytes() + b"\n<!-- local remote fixture -->\n"
        rule.write_bytes(updated)
        self.git("add", "bmad-suite-v4/roo/rules/02-bmad-core.md")
        self.git("-c", "commit.gpgsign=false", "commit", "-m", "upstream fixture")
        commit = self.git("rev-parse", "HEAD").strip()
        self.git("push", "origin", "HEAD:refs/heads/main")
        self.git("checkout", "main")
        return commit, updated

    def test_update_from_detached_head_deploys_fetched_commit(self):
        commit, updated = self.prepare_local_remote_update()
        self.git("checkout", "--detach", "HEAD")
        result = self.run_command(["bash", "bs.sh", "--update"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git("branch", "--show-current").strip(), "main")
        self.assertEqual(self.git("rev-parse", "HEAD").strip(), commit)
        deployed = self.target / ".roo/rules/02-bmad-core.md"
        self.assertEqual(deployed.read_bytes(), updated)

    def test_diverged_main_blocks_switch_and_deployment(self):
        self.prepare_local_remote_update()
        personal = self.repo / "personal.txt"
        personal.write_bytes(b"local committed work\n")
        self.git("add", "personal.txt")
        self.git("-c", "commit.gpgsign=false", "commit", "-m", "local divergence")
        main_before = self.git("rev-parse", "main").strip()
        self.git("checkout", "-b", "fixture-current")
        before_target = self.tree(self.target)
        before_worktree = {
            key: value for key, value in self.tree(self.repo).items()
            if key != ".git" and not key.startswith(".git/")
        }
        result = self.run_command(["bash", "bs.sh", "--update"])
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.git("branch", "--show-current").strip(),
                         "fixture-current")
        self.assertEqual(self.git("rev-parse", "main").strip(), main_before)
        self.assertEqual(self.tree(self.target), before_target)
        after_worktree = {
            key: value for key, value in self.tree(self.repo).items()
            if key != ".git" and not key.startswith(".git/")
        }
        # 真实 fetch 可更新远端跟踪引用，但分歧不得改变本地工作树或部署目标。
        self.assertEqual(after_worktree, before_worktree)

    def test_missing_main_update_rejected_before_fetch(self):
        self.git("branch", "-m", "fixture-only")
        self.assert_rejected_without_changes("--update")
        self.assertFalse((self.repo / ".git/FETCH_HEAD").exists())


if __name__ == "__main__":
    unittest.main()
