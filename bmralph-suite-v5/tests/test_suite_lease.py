"""V5 套件读取租约反例；仅操作项目内临时目录。

不启动 Agent、不核验宿主加载。租约与部署写锁互斥不等于完整
活动任务防护；来源核验、在途进程结束与循环接入仍须独立验证。
"""
import fcntl
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "scripts"))
import bmad_suite_lease as lease
from bmad_supervisor import SupervisorError


class SuiteLeaseGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="sandbox-suite-lease-", dir=SUITE.parent / "tests",
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "deployment with 'quote'"
        self.root.mkdir()
        self.lock = self.root / lease.LOCK_FILE
        self.lock.parent.mkdir()
        self.lock.write_bytes(b"existing deployment lock\n")
        self.lock.chmod(0o600)
        self.personal = self.root / "personal.txt"
        self.personal.write_bytes(b"preserve user changes\n")

    def snapshot(self):
        return {
            path.relative_to(self.root).as_posix(): (
                path.read_bytes(), path.stat().st_mode, path.stat().st_ino,
            )
            for path in self.root.rglob("*") if path.is_file()
        }

    def assert_writer_available(self):
        with self.lock.open("rb") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def test_existing_lock_shared_lease_is_read_only_and_releases(self):
        before = self.snapshot()
        with lease.suite_lease(self.root):
            self.assertEqual(self.snapshot(), before)
            with self.lock.open("rb") as stream:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.assertEqual(self.snapshot(), before)
        self.assert_writer_available()

    def test_multiple_readers_keep_writer_blocked_until_all_release(self):
        with lease.suite_lease(self.root):
            with lease.suite_lease(self.root):
                with self.lock.open("rb") as stream:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.lock.open("rb") as stream:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.assert_writer_available()

    def test_existing_deployment_writer_blocks_before_entering_task(self):
        before = self.snapshot()
        with self.lock.open("rb") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(SupervisorError, "部署正在进行"):
                with lease.suite_lease(self.root):
                    self.fail("任务不得在部署期间进入")
        self.assertEqual(self.snapshot(), before)
        self.assert_writer_available()

    def test_missing_lock_is_not_created(self):
        self.lock.unlink()
        before = self.snapshot()
        with self.assertRaises(FileNotFoundError):
            with lease.suite_lease(self.root):
                self.fail("缺失锁不得视为安全")
        self.assertFalse(self.lock.exists())
        self.assertEqual(self.snapshot(), before)

    def test_missing_state_directory_is_not_created(self):
        self.lock.unlink()
        self.lock.parent.rmdir()
        with self.assertRaises(FileNotFoundError):
            with lease.suite_lease(self.root):
                self.fail("不得隐式准备部署状态")
        self.assertFalse(self.lock.parent.exists())
        self.assertEqual(self.personal.read_bytes(), b"preserve user changes\n")

    def test_missing_root_is_not_created(self):
        missing = self.root / "missing deployment"
        with self.assertRaises(FileNotFoundError):
            with lease.suite_lease(missing):
                self.fail("不得创建部署根")
        self.assertFalse(missing.exists())

    def test_lock_symlink_is_rejected_without_touching_destination(self):
        self.lock.unlink()
        self.lock.symlink_to(self.personal)
        with self.assertRaises(SupervisorError):
            with lease.suite_lease(self.root):
                self.fail("不得跟随锁链接")
        self.assertTrue(self.lock.is_symlink())
        self.assertEqual(self.personal.read_bytes(), b"preserve user changes\n")

    def test_state_directory_symlink_is_rejected(self):
        self.lock.unlink()
        self.lock.parent.rmdir()
        destination = self.root / "other state"
        destination.mkdir()
        (destination / "deployment.lock").write_bytes(b"other lock\n")
        self.lock.parent.symlink_to(destination, target_is_directory=True)
        with self.assertRaises(SupervisorError):
            with lease.suite_lease(self.root):
                self.fail("不得通过状态目录链接")
        self.assertEqual((destination / "deployment.lock").read_bytes(), b"other lock\n")

    def test_deployment_root_symlink_is_rejected(self):
        alias = Path(self.temp.name) / "alias deployment"
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(SupervisorError):
            with lease.suite_lease(alias):
                self.fail("不得通过根目录链接")
        self.assert_writer_available()

    def test_fifo_directory_and_multiple_hardlinks_are_rejected(self):
        self.lock.unlink()
        os.mkfifo(self.lock)
        with self.assertRaises(SupervisorError):
            with lease.suite_lease(self.root):
                self.fail("不得打开 FIFO 等待输入")
        self.lock.unlink()
        self.lock.mkdir()
        with self.assertRaises(SupervisorError):
            with lease.suite_lease(self.root):
                self.fail("目录不是锁文件")
        self.lock.rmdir()
        self.lock.write_bytes(b"lock\n")
        alias = self.root / "hardlink.lock"
        os.link(self.lock, alias)
        with self.assertRaises(SupervisorError):
            with lease.suite_lease(self.root):
                self.fail("多硬链接不得作为租约锁")
        self.assertEqual(alias.read_bytes(), b"lock\n")

    def replace_lock(self):
        replacement = self.root / "replacement.lock"
        replacement.write_bytes(b"external replacement\n")
        os.replace(replacement, self.lock)

    def test_replacement_before_entry_blocks_and_preserves_external_file(self):
        original = lease.require_same_lock
        def replaced(root, descriptor):
            self.replace_lock()
            return original(root, descriptor)
        with mock.patch.object(lease, "require_same_lock", side_effect=replaced):
            with self.assertRaisesRegex(SupervisorError, "锁身份发生变化"):
                with lease.suite_lease(self.root):
                    self.fail("不得在锁替换后进入")
        self.assertEqual(self.lock.read_bytes(), b"external replacement\n")
        self.assert_writer_available()

    def test_replacement_during_lease_blocks_exit_without_restoring_old_lock(self):
        with self.assertRaisesRegex(SupervisorError, "锁身份发生变化"):
            with lease.suite_lease(self.root):
                self.replace_lock()
        self.assertEqual(self.lock.read_bytes(), b"external replacement\n")
        self.assert_writer_available()

    def test_removed_lock_at_exit_is_not_recreated(self):
        with self.assertRaises(FileNotFoundError):
            with lease.suite_lease(self.root):
                self.lock.unlink()
        self.assertFalse(self.lock.exists())

    def test_original_task_failure_is_preserved_and_lease_released(self):
        failure = RuntimeError("真实任务失败")
        with self.assertRaises(RuntimeError) as caught:
            with lease.suite_lease(self.root):
                raise failure
        self.assertIs(caught.exception, failure)
        self.assert_writer_available()

    def test_original_failure_not_hidden_by_external_lock_replacement(self):
        failure = RuntimeError("先发生的业务失败")
        with self.assertRaises(RuntimeError) as caught:
            with lease.suite_lease(self.root):
                self.replace_lock()
                raise failure
        self.assertIs(caught.exception, failure)
        self.assertEqual(self.lock.read_bytes(), b"external replacement\n")
        self.assert_writer_available()

    def test_cancellation_releases_without_deleting_lock_or_user_changes(self):
        before = self.snapshot()
        with self.assertRaises(KeyboardInterrupt):
            with lease.suite_lease(self.root):
                raise KeyboardInterrupt()
        self.assertEqual(self.snapshot(), before)
        self.assert_writer_available()

    def test_open_failure_does_not_create_or_modify_assets(self):
        before = self.snapshot()
        with mock.patch.object(lease.os, "open", side_effect=PermissionError("拒绝读取")):
            with self.assertRaises(PermissionError):
                with lease.suite_lease(self.root):
                    self.fail("拒绝权限不得进入")
        self.assertEqual(self.snapshot(), before)
        self.assert_writer_available()


if __name__ == "__main__":
    unittest.main()
