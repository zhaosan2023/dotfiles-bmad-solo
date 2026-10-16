"""版本操作全程互斥与继承参数反例；仅使用项目内临时仓库和文件远端。

Git 包装器在真实版本操作发生时尝试共享读取，检查排他锁并非只在
最终部署时获取。不启动 Agent，不证明来源绑定或取消后的进程清理。
"""
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

import test_gitops_dry_run as fixtures
import test_gitops_handoff as handoff
import test_suite_selection as selection

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "bmralph-suite-v5/scripts"))
from asset_safety import AssetError, deployment_lock
from bmad_suite_lease import suite_lease


class VersionGuard(unittest.TestCase):
    run_command = fixtures.GitOpsDryRun.run_command
    git = fixtures.GitOpsDryRun.git
    tree = fixtures.GitOpsDryRun.tree
    add_v5 = selection.SuiteSelection.add_v5
    deploy = selection.SuiteSelection.deploy
    MANIFEST = selection.SuiteSelection.MANIFEST
    prepare_update = handoff.GitOpsHandoff.prepare_update

    def setUp(self):
        fixtures.GitOpsDryRun.setUp(self)
        self.env.pop("BMAD_VERSION_LOCK_FD", None)
        self.env.pop("BMAD_HANDOFF_ACTIVE", None)

    def install_committed_v5(self):
        self.add_v5(committed=True)
        self.deploy("v5")
        self.lock = self.target / ".bmad-solo-deployment/deployment.lock"

    def track_exclusive_lock(self):
        real_git = shutil.which("git", path=self.env["PATH"])
        self.assertIsNotNone(real_git)
        wrappers = self.sandbox / "lock-checking wrappers"
        wrappers.mkdir()
        log = self.sandbox / "version-lock-checks.jsonl"
        wrapper = wrappers / "git"
        wrapper.write_text(
            '#!/usr/bin/env python3\n'
            'import fcntl,json,os,sys\n'
            'operations={"fetch","merge","switch","archive"}\n'
            'selected=[value for value in sys.argv[1:] if value in operations]\n'
            'if selected:\n'
            f'    descriptor=os.open({str(self.lock)!r},os.O_RDONLY|os.O_NOFOLLOW)\n'
            '    try:\n'
            '        try:\n'
            '            fcntl.flock(descriptor,fcntl.LOCK_SH|fcntl.LOCK_NB)\n'
            '        except BlockingIOError:\n'
            '            pass\n'
            '        else:\n'
            '            print("VERSION_OPERATION_WITHOUT_EXCLUSIVE_LOCK",file=sys.stderr)\n'
            '            raise SystemExit(93)\n'
            '    finally:\n'
            '        os.close(descriptor)\n'
            f'    with open({str(log)!r},"a") as stream:\n'
            '        stream.write(json.dumps(selected)+"\\n")\n'
            f'os.execv({real_git!r},[{real_git!r},*sys.argv[1:]])\n',
            encoding="utf-8",
        )
        wrapper.chmod(0o700)
        self.env["PATH"] = str(wrappers) + ":" + self.env["PATH"]
        return log

    def checked_operations(self, log):
        self.assertTrue(log.is_file(), "没有操作期锁证据不能记为通过")
        return {operation for line in log.read_text().splitlines()
                for operation in json.loads(line)}

    def assert_released(self):
        with suite_lease(self.target):
            self.assertTrue(self.lock.is_file())

    def test_update_keeps_exclusive_lock_during_fetch_merge_and_new_entry_deploy(self):
        self.install_committed_v5()
        commit, _ = self.prepare_update()
        log = self.track_exclusive_lock()
        result = self.run_command(["bash", "bs.sh", "--update"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count("显式移交磁盘新版部署入口"), 1)
        self.assertEqual(result.stdout.count("NEW_ENTRY_LOADED"), 1)
        self.assertTrue({"fetch", "merge", "archive"}.issubset(
            self.checked_operations(log)))
        manifest = json.loads((self.target / self.MANIFEST).read_bytes())
        self.assertEqual(manifest["major_version"], "v5")
        self.assertEqual(manifest["source_commit"], commit)
        self.assert_released()

    def test_latest_keeps_exclusive_lock_during_switch_and_handoff(self):
        self.install_committed_v5()
        self.git("checkout", "-b", "fixture-other-branch")
        log = self.track_exclusive_lock()
        result = self.run_command(["bash", "bs.sh", "--latest"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count("显式移交磁盘新版部署入口"), 1)
        self.assertIn("switch", self.checked_operations(log))
        self.assertEqual(self.git("branch", "--show-current").strip(), "main")
        self.assert_released()

    def test_tag_keeps_exclusive_lock_during_cache_preparation_and_deploy(self):
        self.install_committed_v5()
        self.git("tag", "fixture-v5-guard")
        log = self.track_exclusive_lock()
        result = self.run_command([
            "bash", "bs.sh", "v5", "--tag", "fixture-v5-guard",
        ])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("archive", self.checked_operations(log))
        manifest = json.loads((self.target / self.MANIFEST).read_bytes())
        self.assertEqual(manifest["major_version"], "v5")
        self.assertEqual(manifest["source_kind"], "commit_cache")
        self.assert_released()

    def test_forged_descriptor_environment_fails_before_version_side_effects(self):
        self.install_committed_v5()
        before_repo = self.tree(self.repo)
        before_target = self.tree(self.target)
        for value in ("not-a-descriptor", "2", "999999"):
            with self.subTest(value=value):
                self.env["BMAD_VERSION_LOCK_FD"] = value
                result = self.run_command(["bash", "bs.sh", "v5", "--latest"])
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertNotIn("显式移交磁盘新版部署入口", result.stdout)
                self.assertEqual(self.tree(self.repo), before_repo)
                self.assertEqual(self.tree(self.target), before_target)
        self.env.pop("BMAD_VERSION_LOCK_FD")
        self.assert_released()

    def test_cli_rejects_unlocked_and_shared_inherited_descriptors_without_writes(self):
        self.install_committed_v5()
        before_repo = self.tree(self.repo)
        before_target = self.tree(self.target)
        for shared in (False, True):
            with self.subTest(shared=shared):
                descriptor = os.open(self.lock, os.O_RDONLY | os.O_NOFOLLOW)
                try:
                    if shared:
                        fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
                    result = subprocess.run(
                        [sys.executable, "-B", str(self.repo / "scripts/deploy-managed-cli.py"),
                         "--root", str(self.target),
                         "--source", str(self.repo / "bmralph-suite-v5"),
                         "--repository", str(self.repo),
                         "--deployment-lock-fd", str(descriptor)],
                        cwd=self.repo, env=self.env, stdin=subprocess.DEVNULL,
                        capture_output=True, text=True, timeout=15,
                        pass_fds=(descriptor,), check=False,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("未持有可核验的排他部署锁", result.stderr)
                    self.assertEqual(self.tree(self.repo), before_repo)
                    self.assertEqual(self.tree(self.target), before_target)
                    if shared:
                        with self.assertRaises(AssetError):
                            with deployment_lock(self.lock):
                                self.fail("失败核验不得释放共享锁")
                        with suite_lease(self.target):
                            self.assertTrue(self.lock.is_file())
                finally:
                    os.close(descriptor)
        self.assert_released()

    def test_missing_existing_lock_is_not_recreated_by_version_operation(self):
        self.install_committed_v5()
        self.lock.unlink()
        before_repo = self.tree(self.repo)
        before_target = self.tree(self.target)
        result = self.run_command(["bash", "bs.sh", "v5", "--latest"])
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.lock.exists())
        self.assertNotIn("显式移交磁盘新版部署入口", result.stdout)
        self.assertEqual(self.tree(self.repo), before_repo)
        self.assertEqual(self.tree(self.target), before_target)

    def test_version_dry_run_remains_read_only_while_task_holds_lease(self):
        self.install_committed_v5()
        before_repo = self.tree(self.repo)
        before_target = self.tree(self.target)
        with suite_lease(self.target):
            result = self.run_command(["bash", "bs.sh", "v5", "--latest", "--dry-run"])
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(self.tree(self.repo), before_repo)
            self.assertEqual(self.tree(self.target), before_target)
            with self.assertRaises(AssetError):
                with deployment_lock(self.lock):
                    self.fail("只读预览不得释放任务租约")
        self.assert_released()


if __name__ == "__main__":
    unittest.main()
