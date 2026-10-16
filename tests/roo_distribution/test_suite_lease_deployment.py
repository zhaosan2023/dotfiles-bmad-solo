"""套件共享租约与真实部署子进程互斥；仅操作项目内临时根。

不启动 Agent、不修改宿主配置或真实仓库引用。这里验证协作锁协议，
不证明任务循环已经接入租约、来源绑定或取消后子进程清理。
"""
from pathlib import Path
import sys
import unittest

import test_gitops_dry_run as fixtures
import test_suite_selection as selection

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "bmralph-suite-v5/scripts"))
from asset_safety import deployment_lock
from bmad_suite_lease import suite_lease
from bmad_supervisor import SupervisorError


class SuiteLeaseDeployment(unittest.TestCase):
    setUp = fixtures.GitOpsDryRun.setUp
    run_command = fixtures.GitOpsDryRun.run_command
    git = fixtures.GitOpsDryRun.git
    tree = fixtures.GitOpsDryRun.tree
    add_v5 = selection.SuiteSelection.add_v5
    deploy = selection.SuiteSelection.deploy
    MANIFEST = selection.SuiteSelection.MANIFEST

    def install_v5(self):
        self.add_v5()
        self.deploy("v5")
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

    def test_task_lease_blocks_shell_idempotent_deploy_update_switch_and_uninstall(self):
        self.install_v5()
        source = self.repo / "bmralph-suite-v5/roo/rules/02-bmad-core.md"
        original = source.read_bytes()
        with suite_lease(self.target):
            self.assert_shell_blocked("v5")
            source.write_bytes(original + b"\n")
            self.assert_shell_blocked("v5")
            self.assertEqual(source.read_bytes(), original + b"\n")
            self.assert_shell_blocked("v4")
            self.assert_shell_blocked("--uninstall")
        # 租约释放后，仍须通过正常受管预检，才能应用候选更新。
        updated = self.deploy("v5")
        self.assertEqual(updated["major_version"], "v5")
        deployed = self.target / ".roo/rules/02-bmad-core.md"
        self.assertEqual(deployed.read_bytes(), source.read_bytes())

    def test_deployment_writer_blocks_task_entry_then_release_allows_lease(self):
        self.install_v5()
        before = self.tree(self.target)
        with deployment_lock(self.lock):
            with self.assertRaisesRegex(SupervisorError, "部署正在进行"):
                with suite_lease(self.target):
                    self.fail("部署写入期间不得进入任务")
        with suite_lease(self.target):
            self.assertEqual(self.tree(self.target), before)
        self.assertEqual(self.tree(self.target), before)

    def test_nested_readers_keep_shell_writer_blocked_until_last_reader_exits(self):
        self.install_v5()
        with suite_lease(self.target):
            with suite_lease(self.target):
                self.assert_shell_blocked("v4")
            self.assert_shell_blocked("--uninstall")
        switched = self.deploy("v4")
        self.assertEqual(switched["major_version"], "v4")

    def test_read_only_preflight_and_status_do_not_release_or_modify_task_lease(self):
        self.install_v5()
        before_repo = self.tree(self.repo)
        before_target = self.tree(self.target)
        before_home = self.tree(self.home)
        with suite_lease(self.target):
            for arguments in (("v5", "--preflight"), ("--status",)):
                with self.subTest(arguments=arguments):
                    result = self.run_command(["bash", "bs.sh", *arguments])
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(self.tree(self.repo), before_repo)
                    self.assertEqual(self.tree(self.target), before_target)
                    self.assertEqual(self.tree(self.home), before_home)
            self.assert_shell_blocked("--uninstall")


class SuiteLeaseVersionOperations(unittest.TestCase):
    """版本动作也须在持租约期间失败关闭，不重复发现部署测试。"""

    setUp = SuiteLeaseDeployment.setUp
    run_command = SuiteLeaseDeployment.run_command
    git = SuiteLeaseDeployment.git
    tree = SuiteLeaseDeployment.tree
    add_v5 = SuiteLeaseDeployment.add_v5
    deploy = SuiteLeaseDeployment.deploy
    MANIFEST = SuiteLeaseDeployment.MANIFEST
    assert_shell_blocked = SuiteLeaseDeployment.assert_shell_blocked

    def install_committed_v5(self):
        self.add_v5(committed=True)
        self.deploy("v5")
        self.git("tag", "fixture-v5-lease")

    def test_lease_blocks_latest_before_new_entry_handoff(self):
        self.install_committed_v5()
        with suite_lease(self.target):
            result = self.assert_shell_blocked("v5", "--latest")
        self.assertNotIn("显式移交磁盘新版部署入口", result.stdout)

    def test_lease_blocks_remote_update_before_fetch(self):
        self.install_committed_v5()
        # 不配置远端：应先被租约拒绝，而不是尝试获取后才失败。
        with suite_lease(self.target):
            result = self.assert_shell_blocked("v5", "--update")
        self.assertNotIn("获取 origin/main 与标签", result.stdout)
        self.assertNotIn("显式移交磁盘新版部署入口", result.stdout)

    def test_lease_blocks_tag_before_cache_preparation(self):
        self.install_committed_v5()
        with suite_lease(self.target):
            self.assert_shell_blocked("v5", "--tag", "fixture-v5-lease")
        self.assertFalse((self.repo / ".versions").exists())


if __name__ == "__main__":
    unittest.main()
