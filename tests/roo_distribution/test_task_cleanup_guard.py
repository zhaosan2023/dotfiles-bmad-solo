"""任务清理未知时的持久部署阻断；仅使用项目内临时根。

不启动 Agent、不激活宿主；记录只是协作协议，不保证同账号防篡改。
"""
import fcntl
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from asset_safety import AssetError, deployment_lock


class TaskCleanupGuard(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix="sandbox-task-cleanup-", dir=Path(__file__).parent)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.state = self.root / ".bmad-solo-deployment"
        self.state.mkdir()
        self.lock = self.state / "deployment.lock"
        self.lock.write_bytes(b"existing lock\n")
        self.directory = self.state / "task-runs"
        self.identifier = "a" * 32
        self.data = {
            "schema_version": 1, "run_id": self.identifier,
            "workspace": str(self.root / "workspace"),
            "run_copy_file": ".bmad-control/run-copies/" + "b" * 32 + "/binding.json",
            "status": "EXECUTING", "cleanup_ok": False, "final_receipt": None,
        }

    def save(self, data=None):
        self.directory.mkdir(exist_ok=True)
        path = self.directory / (self.identifier + ".json")
        path.write_text(json.dumps(self.data if data is None else data), encoding="utf-8")
        return path

    def tree(self):
        return {path.relative_to(self.root).as_posix(): path.read_bytes()
                for path in self.root.rglob("*")
                if path.is_file() and not path.is_symlink()}

    def assert_blocked(self):
        before = self.tree()
        with self.assertRaises(AssetError):
            with deployment_lock(self.lock, create=False):
                self.fail("清理未知时不得进入部署")
        self.assertEqual(self.tree(), before)
        # 阻断不会遗留本次调用的排他锁；持久记录承担后续阻断。
        with self.lock.open("rb") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    def test_existing_deployment_without_task_records_remains_compatible(self):
        before = self.tree()
        with deployment_lock(self.lock, create=False):
            pass
        self.assertEqual(self.tree(), before)
        self.assertFalse(self.directory.exists())

    def test_released_shared_lease_does_not_clear_unknown_cleanup(self):
        with self.lock.open("rb") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
            self.save()
        self.assert_blocked()
        self.assert_blocked()

    def test_terminal_status_without_confirmed_cleanup_still_blocks(self):
        for status in ("BLOCKED", "SUSPENDED", "COMPLETED"):
            with self.subTest(status=status):
                self.save(dict(self.data, status=status))
                self.assert_blocked()

    def test_confirmed_terminal_record_allows_writer_without_deleting_evidence(self):
        for status in ("BLOCKED", "SUSPENDED", "COMPLETED"):
            with self.subTest(status=status):
                self.save(dict(self.data, status=status, cleanup_ok=True,
                               final_receipt=".bmad-runtime/loop-" + self.identifier + ".json"))
                before = self.tree()
                with deployment_lock(self.lock, create=False):
                    pass
                self.assertEqual(self.tree(), before)

    def test_active_record_or_missing_final_receipt_cannot_claim_cleanup(self):
        for changes in ({"cleanup_ok": True},
                        {"status": "COMPLETED", "cleanup_ok": True}):
            with self.subTest(changes=changes):
                self.save(dict(self.data, **changes))
                self.assert_blocked()

    def test_inherited_writer_rechecks_records_without_releasing_outer_lock(self):
        with deployment_lock(self.lock, create=False) as descriptor:
            self.save()
            with self.assertRaises(AssetError):
                with deployment_lock(self.lock, inherited_fd=descriptor):
                    self.fail("借用锁也必须核验清理记录")
            with self.lock.open("rb") as reader:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(reader.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.fstat(descriptor)
        self.assert_blocked()

    def test_corrupt_duplicate_or_oversized_record_blocks_without_repair(self):
        path = self.save()
        for content in (b"{", b'{"schema_version":1,"schema_version":1}', b"x" * 16385):
            with self.subTest(size=len(content)):
                path.write_bytes(content)
                self.assert_blocked()
                self.assertEqual(path.read_bytes(), content)

    def test_unknown_asset_directory_and_links_fail_closed(self):
        self.directory.mkdir()
        extra = self.directory / "personal.txt"
        extra.write_bytes(b"preserve third party\n")
        self.assert_blocked()
        extra.unlink()
        path = self.save()
        alias = self.root / "record-alias.json"
        os.link(path, alias)
        self.assert_blocked()
        alias.unlink()
        path.unlink()
        path.symlink_to(self.lock)
        self.assert_blocked()
        path.unlink()
        path.mkdir()
        self.assert_blocked()

    def test_malformed_identity_and_receipt_paths_fail_closed(self):
        for changes in ({"schema_version": True}, {"run_id": "c" * 32},
                        {"workspace": "relative"}, {"cleanup_ok": 1},
                        {"run_copy_file": "../binding.json"},
                        {"status": "COMPLETED", "cleanup_ok": True,
                         "final_receipt": "../outside.json"}):
            with self.subTest(changes=changes):
                self.save(dict(self.data, **changes))
                self.assert_blocked()

    def test_unrelated_cache_lock_does_not_adopt_deployment_task_protocol(self):
        self.save()
        cache_lock = self.state / "cache.lock"
        with deployment_lock(cache_lock):
            pass
        self.assertTrue(cache_lock.is_file())
        self.assert_blocked()


if __name__ == "__main__":
    unittest.main()
