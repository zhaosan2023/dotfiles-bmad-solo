"""V4 分发与内核共享锁互斥；仅使用项目内隔离夹具。

共享锁由测试夹具持有，不依赖退役运行时，不证明 Agent 生命周期。
"""
from pathlib import Path
import sys
import unittest

import test_gitops_dry_run as fixtures
import test_suite_selection as selection
from shared_lock_fixture import SharedLockError, suite_lease

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from asset_safety import deployment_lock


class SuiteLeaseDeployment(unittest.TestCase):
    setUp = fixtures.GitOpsDryRun.setUp
    run_command = fixtures.GitOpsDryRun.run_command
    git = fixtures.GitOpsDryRun.git
    tree = fixtures.GitOpsDryRun.tree
    deploy = selection.SuiteSelection.deploy
    MANIFEST = selection.SuiteSelection.MANIFEST

    def install_v4(self):
        self.deploy()
        self.lock = self.target / ".bmad-solo-deployment/deployment.lock"
        self.assertTrue(self.lock.is_file())

    def assert_shell_blocked(self, *arguments):
        before_repo = self.tree(self.repo)
        before_target = self.tree(self.target)
        before_home = self.tree(self.home)
        result = self.run_command(["bash", "bs.sh", *arguments])
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("另一部署进程持有锁", result.stderr)
        self.assertEqual(self.tree(self.repo), before_repo)
        self.assertEqual(self.tree(self.target), before_target)
        self.assertEqual(self.tree(self.home), before_home)
        return result

    def test_shared_lock_blocks_idempotent_deploy_changes_and_uninstall(self):
        self.install_v4()
        source = self.repo / "bmad-suite-v4/roo/rules/02-bmad-core.md"
        original = source.read_bytes()
        with suite_lease(self.target):
            self.assert_shell_blocked()
            source.write_bytes(original + b"\n")
            self.assert_shell_blocked("v4")
            self.assertEqual(source.read_bytes(), original + b"\n")
            self.assert_shell_blocked("--uninstall")
        updated = self.deploy()
        self.assertEqual(updated["major_version"], "v4")
        self.assertEqual((self.target / ".roo/rules/02-bmad-core.md").read_bytes(),
                         source.read_bytes())

    def test_deployment_writer_blocks_shared_reader_until_release(self):
        self.install_v4()
        before = self.tree(self.target)
        with deployment_lock(self.lock):
            with self.assertRaisesRegex(SharedLockError, "部署正在进行"):
                with suite_lease(self.target):
                    self.fail("部署写入期间不得获得共享锁")
        with suite_lease(self.target):
            self.assertEqual(self.tree(self.target), before)
        self.assertEqual(self.tree(self.target), before)

    def test_nested_readers_block_writer_until_last_reader_exits(self):
        self.install_v4()
        with suite_lease(self.target):
            with suite_lease(self.target):
                self.assert_shell_blocked("v4")
            self.assert_shell_blocked("--uninstall")
        self.assertEqual(self.deploy()["major_version"], "v4")

    def test_preflight_and_status_do_not_release_or_modify_shared_lock(self):
        self.install_v4()
        before_repo = self.tree(self.repo)
        before_target = self.tree(self.target)
        before_home = self.tree(self.home)
        with suite_lease(self.target):
            for arguments in (("--preflight",), ("--status",)):
                with self.subTest(arguments=arguments):
                    result = self.run_command(["bash", "bs.sh", *arguments])
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(self.tree(self.repo), before_repo)
                    self.assertEqual(self.tree(self.target), before_target)
                    self.assertEqual(self.tree(self.home), before_home)
            self.assert_shell_blocked("--uninstall")


class SuiteLeaseVersionOperations(unittest.TestCase):
    setUp = SuiteLeaseDeployment.setUp
    run_command = SuiteLeaseDeployment.run_command
    git = SuiteLeaseDeployment.git
    tree = SuiteLeaseDeployment.tree
    deploy = SuiteLeaseDeployment.deploy
    MANIFEST = SuiteLeaseDeployment.MANIFEST
    assert_shell_blocked = SuiteLeaseDeployment.assert_shell_blocked

    def install_committed_v4(self):
        self.deploy()
        self.git("tag", "fixture-v4-lease")

    def test_shared_lock_blocks_latest_before_handoff(self):
        self.install_committed_v4()
        with suite_lease(self.target):
            result = self.assert_shell_blocked("--latest")
        self.assertNotIn("显式移交磁盘新版部署入口", result.stdout)

    def test_shared_lock_blocks_update_before_fetch(self):
        self.install_committed_v4()
        with suite_lease(self.target):
            result = self.assert_shell_blocked("--update")
        self.assertNotIn("获取 origin/main 与标签", result.stdout)
        self.assertNotIn("显式移交磁盘新版部署入口", result.stdout)

    def test_shared_lock_blocks_tag_before_cache(self):
        self.install_committed_v4()
        with suite_lease(self.target):
            self.assert_shell_blocked("--tag", "fixture-v4-lease")
        self.assertFalse((self.repo / ".versions").exists())


if __name__ == "__main__":
    unittest.main()
