"""安装入口失败关闭测试；仅使用独立仓库和项目内目标。"""
import shutil
import unittest

import test_gitops_dry_run as fixtures


class GitOpsInstaller(fixtures.GitOpsDryRun):
    def setUp(self):
        super().setUp()
        self.installer = self.sandbox / "install.sh"
        shutil.copy2(fixtures.ROOT / "install.sh", self.installer)
        self.env["BMAD_SOLO_DIR"] = str(self.repo)

    def test_dirty_repository_rejected_before_fetch_or_deployment(self):
        source = self.repo / "bmad-suite-v4/plugin.json"
        source.write_bytes(source.read_bytes() + b"\n")
        before_repo = self.tree(self.repo)
        before_target = self.tree(self.target)
        result = self.run_command(["bash", str(self.installer)])
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.tree(self.repo), before_repo,
                         "安装入口必须在获取远端前拒绝脏工作树")
        self.assertEqual(self.tree(self.target), before_target)
        self.assertNotIn("Installation Complete!", result.stdout)

    def test_missing_main_rejected_before_remote_access(self):
        self.git("branch", "-m", "fixture-only")
        before_repo = self.tree(self.repo)
        before_target = self.tree(self.target)
        result = self.run_command(["bash", str(self.installer)])
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.tree(self.repo), before_repo,
                         "缺少本地主分支时不得先修改远端获取状态")
        self.assertEqual(self.tree(self.target), before_target)
        self.assertEqual(self.git("branch", "--show-current").strip(),
                         "fixture-only")
        self.assertNotIn("Installation Complete!", result.stdout)


if __name__ == "__main__":
    unittest.main()
