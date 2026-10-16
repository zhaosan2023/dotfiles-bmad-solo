"""继承部署锁的内核证据与借用边界；仅操作项目内临时目录。

描述符编号不是授权或持锁证据。这里不执行部署、版本更新或 Agent，
也不将同账号协作锁描述为恶意代码隔离。
"""
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from asset_safety import (
    AssetError, deployment_lock, validate_inherited_deployment_lock,
)


class InheritedDeploymentLock(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix="sandbox-inherited-lock-", dir=Path(__file__).parent,
        )
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root / "deployment.lock"

    def open_unlocked(self):
        descriptor = os.open(
            self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600,
        )
        self.addCleanup(os.close, descriptor)
        return descriptor

    def assert_writer_blocked(self):
        with self.assertRaisesRegex(AssetError, "另一部署进程持有锁"):
            with deployment_lock(self.path):
                self.fail("借用期间及退出后不得释放外层排他锁")

    def test_exclusive_descriptor_can_be_validated_and_borrowed(self):
        with deployment_lock(self.path) as descriptor:
            validate_inherited_deployment_lock(self.path, descriptor)
            with deployment_lock(self.path, inherited_fd=descriptor) as borrowed:
                self.assertEqual(borrowed, descriptor)
                self.assert_writer_blocked()
            os.fstat(descriptor)
            validate_inherited_deployment_lock(self.path, descriptor)
            self.assert_writer_blocked()
        with deployment_lock(self.path):
            self.assertTrue(self.path.is_file())

    def test_borrowed_failure_preserves_exception_and_outer_lock(self):
        failure = RuntimeError("真实调用方失败")
        with deployment_lock(self.path) as descriptor:
            with self.assertRaises(RuntimeError) as caught:
                with deployment_lock(self.path, inherited_fd=descriptor):
                    raise failure
            self.assertIs(caught.exception, failure)
            validate_inherited_deployment_lock(self.path, descriptor)
            self.assert_writer_blocked()

    def test_unlocked_descriptor_is_not_upgraded_to_exclusive(self):
        descriptor = self.open_unlocked()
        with self.assertRaisesRegex(AssetError, "未持有可核验的排他部署锁"):
            with deployment_lock(self.path, inherited_fd=descriptor):
                self.fail("未持锁描述符不能借用")
        with deployment_lock(self.path):
            self.assertTrue(self.path.is_file())

    def test_shared_descriptor_is_not_upgraded_or_released(self):
        descriptor = self.open_unlocked()
        fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
        with self.assertRaisesRegex(AssetError, "未持有可核验的排他部署锁"):
            validate_inherited_deployment_lock(self.path, descriptor)
        self.assert_writer_blocked()
        # 第二个共享读取者仍能进入，证明失败核验没有升级原共享锁。
        reader = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            fcntl.flock(reader, fcntl.LOCK_SH | fcntl.LOCK_NB)
        finally:
            os.close(reader)

    def test_separate_unlocked_descriptor_cannot_claim_another_lock(self):
        with deployment_lock(self.path):
            descriptor = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                with self.assertRaisesRegex(AssetError, "未持有可核验的排他部署锁"):
                    validate_inherited_deployment_lock(self.path, descriptor)
            finally:
                os.close(descriptor)
            self.assert_writer_blocked()

    def test_wrong_file_descriptor_and_invalid_numbers_fail_closed(self):
        other = self.root / "other.lock"
        with deployment_lock(other) as descriptor:
            self.path.write_bytes(b"")
            with self.assertRaisesRegex(AssetError, "身份发生变化"):
                validate_inherited_deployment_lock(self.path, descriptor)
        for descriptor in (True, False, -1, 0, 1, 2, "3", 3.0):
            with self.subTest(descriptor=descriptor):
                with self.assertRaisesRegex(AssetError, "描述符非法"):
                    validate_inherited_deployment_lock(self.path, descriptor)

    def test_external_replacement_is_rejected_and_preserved(self):
        with deployment_lock(self.path) as descriptor:
            replacement = self.root / "replacement.lock"
            replacement.write_bytes(b"external replacement\n")
            os.replace(replacement, self.path)
            with self.assertRaisesRegex(AssetError, "身份发生变化"):
                validate_inherited_deployment_lock(self.path, descriptor)
            self.assertEqual(self.path.read_bytes(), b"external replacement\n")
        self.assertEqual(self.path.read_bytes(), b"external replacement\n")

    def test_multiple_hard_links_are_rejected(self):
        with deployment_lock(self.path) as descriptor:
            alias = self.root / "alias.lock"
            os.link(self.path, alias)
            with self.assertRaisesRegex(AssetError, "单硬链接普通文件"):
                validate_inherited_deployment_lock(self.path, descriptor)
            self.assertTrue(alias.is_file())

    def test_missing_kernel_evidence_fails_without_releasing_lock(self):
        with deployment_lock(self.path) as descriptor:
            with patch("asset_safety.open", create=True,
                       side_effect=PermissionError("fdinfo unavailable")):
                with self.assertRaisesRegex(AssetError, "无法核验继承部署锁"):
                    validate_inherited_deployment_lock(self.path, descriptor)
            validate_inherited_deployment_lock(self.path, descriptor)
            self.assert_writer_blocked()

    def test_subprocess_can_borrow_real_inherited_descriptor_without_unlocking(self):
        with deployment_lock(self.path) as descriptor:
            code = (
                "import pathlib,sys; "
                "sys.path.insert(0,sys.argv[1]); "
                "from asset_safety import deployment_lock; "
                "context=deployment_lock(pathlib.Path(sys.argv[2]),"
                "inherited_fd=int(sys.argv[3])); "
                "borrowed=context.__enter__(); "
                "assert borrowed==int(sys.argv[3]); "
                "context.__exit__(None,None,None); "
                "print('INHERITED_LOCK_VALIDATED')"
            )
            result = subprocess.run(
                [sys.executable, "-I", "-B", "-c", code,
                 str(ROOT / "scripts"), str(self.path), str(descriptor)],
                cwd=self.root, stdin=subprocess.DEVNULL,
                capture_output=True, text=True, timeout=15,
                pass_fds=(descriptor,), check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stdout.strip(), "INHERITED_LOCK_VALIDATED")
            validate_inherited_deployment_lock(self.path, descriptor)
            self.assert_writer_blocked()
        with deployment_lock(self.path):
            self.assertTrue(self.path.is_file())


if __name__ == "__main__":
    unittest.main()
