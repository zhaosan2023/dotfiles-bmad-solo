"""验证原子替换的权限设置及失败边界；不代表多文件事务通过。"""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from asset_safety import AssetError, Snapshot, atomic_replace, snapshot


class AtomicReplaceSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="sandbox-", dir=Path(__file__).parent
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "managed.md"

    def prepare_existing(self):
        self.path.write_bytes(b"original")
        self.path.chmod(0o640)
        return snapshot(self.path)

    def assert_no_temporary_files(self):
        self.assertEqual(list(self.root.glob(".bmad-write-*")), [])

    def test_explicit_mode_for_new_file(self):
        atomic_replace(self.path, b"new", Snapshot(None, None), mode=0o755)
        self.assertEqual(snapshot(self.path), Snapshot(b"new", 0o755))
        self.assert_no_temporary_files()

    def test_explicit_mode_for_existing_file(self):
        before = self.prepare_existing()
        atomic_replace(self.path, b"updated", before, mode=0o600)
        self.assertEqual(snapshot(self.path), Snapshot(b"updated", 0o600))
        self.assert_no_temporary_files()

    def test_invalid_modes_leave_original_unchanged(self):
        before = self.prepare_existing()
        for mode in (True, -1, 0o1000, 0o4755, "600"):
            with self.subTest(mode=mode):
                with self.assertRaises(AssetError):
                    atomic_replace(self.path, b"updated", before, mode=mode)
                self.assertEqual(snapshot(self.path), before)
                self.assert_no_temporary_files()

    def test_non_byte_content_leaves_original_unchanged(self):
        before = self.prepare_existing()
        with self.assertRaises(AssetError):
            atomic_replace(self.path, "not bytes", before)
        self.assertEqual(snapshot(self.path), before)
        self.assert_no_temporary_files()

    def test_file_sync_failure_preserves_original(self):
        before = self.prepare_existing()
        with patch("asset_safety.os.fsync", side_effect=OSError("模拟文件同步失败")):
            with self.assertRaises(OSError):
                atomic_replace(self.path, b"updated", before)
        self.assertEqual(snapshot(self.path), before)
        self.assert_no_temporary_files()

    def test_replace_failure_preserves_original(self):
        before = self.prepare_existing()
        with patch("asset_safety.os.replace", side_effect=OSError("模拟替换失败")):
            with self.assertRaises(OSError):
                atomic_replace(self.path, b"updated", before)
        self.assertEqual(snapshot(self.path), before)
        self.assert_no_temporary_files()

    def test_directory_sync_failure_reports_error_after_replacement(self):
        before = self.prepare_existing()
        # 第一次文件同步成功；第二次目录同步失败时替换已经发生。
        with patch("asset_safety.os.fsync", side_effect=[None, OSError("模拟目录同步失败")]):
            with self.assertRaises(OSError):
                atomic_replace(self.path, b"updated", before, mode=0o600)
        self.assertEqual(snapshot(self.path), Snapshot(b"updated", 0o600))
        self.assert_no_temporary_files()
        # 恢复必须依据当前真实状态，不能误用替换前的快照。
        atomic_replace(self.path, before.content, snapshot(self.path), mode=before.mode)
        self.assertEqual(snapshot(self.path), before)


if __name__ == "__main__":
    unittest.main()
