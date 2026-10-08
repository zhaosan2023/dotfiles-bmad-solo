"""项目内隔离验证安全原语；不代表完整部署事务已通过。"""
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from asset_safety import (
    AssetError, Snapshot, atomic_replace, checked_path,
    check_writable_parent, deployment_lock, parse_modes,
    require_unchanged, snapshot,
)


class AssetSafetyPrimitives(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="sandbox-", dir=Path(__file__).parent
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_yaml_preserves_unmanaged_data(self):
        data = parse_modes(b"theme: dark\ncustomModes:\n  - slug: third-party\n    name: Custom\n")
        self.assertEqual(data["theme"], "dark")
        self.assertEqual(data["customModes"][0]["slug"], "third-party")
        self.assertEqual(parse_modes(b"{}"), {})

    def test_invalid_yaml_rejected_without_writing(self):
        inputs = (
            b"", b"null", b"[]", b"customModes: [",
            b"customModes: {}", b"customModes: [null]",
            b"customModes: [{}]", b"customModes: []\ncustomModes: []",
            b"customModes: [{slug: x}, {slug: x}]",
            b"customModes: [{slug: x, slug: y}]", b"\xff",
        )
        path = self.root / "modes.yaml"
        for content in inputs:
            with self.subTest(content=content):
                path.write_bytes(content)
                with self.assertRaises(AssetError):
                    parse_modes(path.read_bytes())
                self.assertEqual(path.read_bytes(), content)

    def test_missing_snapshot_and_create(self):
        path = self.root / "new.md"
        missing = snapshot(path)
        self.assertEqual(missing, Snapshot(None, None))
        atomic_replace(path, b"new content", missing)
        self.assertEqual(path.read_bytes(), b"new content")
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_replace_preserves_mode(self):
        path = self.root / "existing.md"
        path.write_bytes(b"original")
        path.chmod(0o640)
        before = snapshot(path)
        self.assertIsNotNone(before.digest)
        atomic_replace(path, b"replacement", before)
        self.assertEqual(path.read_bytes(), b"replacement")
        self.assertEqual(path.stat().st_mode & 0o777, 0o640)
        self.assertEqual(list(self.root.glob(".bmad-write-*")), [])

    def test_external_edit_rejected(self):
        path = self.root / "existing.md"
        path.write_bytes(b"original")
        before = snapshot(path)
        path.write_bytes(b"user edit")
        with self.assertRaises(AssetError):
            atomic_replace(path, b"deployment", before)
        self.assertEqual(path.read_bytes(), b"user edit")

    def test_mode_change_rejected(self):
        path = self.root / "existing.md"
        path.write_bytes(b"original")
        path.chmod(0o600)
        before = snapshot(path)
        path.chmod(0o640)
        with self.assertRaises(AssetError):
            require_unchanged(path, before)

    def test_symlink_and_parent_symlink_rejected(self):
        target = self.root / "target"
        target.mkdir()
        link = self.root / "link"
        link.symlink_to(target, target_is_directory=True)
        for path in (link, link / "new.md"):
            with self.subTest(path=path), self.assertRaises(AssetError):
                checked_path(path)
        dangling = self.root / "dangling"
        dangling.symlink_to(self.root / "missing")
        with self.assertRaises(AssetError):
            snapshot(dangling)

    def test_hardlink_rejected(self):
        path = self.root / "original"
        path.write_bytes(b"protected")
        os.link(path, self.root / "alias")
        with self.assertRaises(AssetError):
            snapshot(path)
        self.assertEqual(path.read_bytes(), b"protected")

    def test_fifo_rejected_without_blocking(self):
        path = self.root / "fifo"
        os.mkfifo(path)
        with self.assertRaises(AssetError):
            snapshot(path)

    def test_parent_traversal_rejected(self):
        with self.assertRaises(AssetError):
            checked_path(self.root / ".." / "other")

    def test_read_only_parent_rejected(self):
        directory = self.root / "readonly"
        directory.mkdir()
        directory.chmod(0o500)
        try:
            with self.assertRaises(AssetError):
                check_writable_parent(directory / "new.md")
        finally:
            directory.chmod(0o700)

    def test_lock_excludes_second_writer_and_releases(self):
        path = self.root / "deployment.lock"
        with deployment_lock(path):
            inode = path.stat().st_ino
            with self.assertRaises(AssetError):
                with deployment_lock(path):
                    self.fail("第二写入者不应获得锁")
        self.assertTrue(path.exists())
        with deployment_lock(path):
            self.assertEqual(path.stat().st_ino, inode)

    def test_lock_releases_after_exception(self):
        path = self.root / "deployment.lock"
        with self.assertRaises(RuntimeError):
            with deployment_lock(path):
                raise RuntimeError("模拟调用者失败")
        with deployment_lock(path):
            self.assertTrue(path.is_file())


if __name__ == "__main__":
    unittest.main()
