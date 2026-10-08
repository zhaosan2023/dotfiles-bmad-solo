"""项目内验证批次提交、备份及恢复；不代表部署入口已接入。"""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import asset_transaction as transaction
from asset_safety import AssetError, Snapshot, deployment_lock, snapshot
from asset_transaction import TargetChange, TransactionError, commit_changes


class TransactionSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sandbox-", dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.target = self.root / "targets"
        self.target.mkdir()
        self.journal = self.root / "journal"
        self.first = self.target / "first.md"
        self.second = self.target / "second.md"
        self.first.write_bytes(b"original-first")
        self.second.write_bytes(b"original-second")
        self.first.chmod(0o640)
        self.second.chmod(0o600)
        self.before_first = snapshot(self.first)
        self.before_second = snapshot(self.second)
        self.changes = (
            TargetChange(self.first, self.before_first, Snapshot(b"new-first", 0o600)),
            TargetChange(self.second, self.before_second, Snapshot(b"new-second", 0o640)),
        )

    def commit(self, changes=None):
        with deployment_lock(self.root / "deployment.lock"):
            return commit_changes(self.changes if changes is None else changes,
                                  (self.target,), self.journal)

    def state(self):
        return json.loads((self.journal / "transaction.json").read_text(encoding="utf-8"))

    def assert_originals(self):
        self.assertEqual(snapshot(self.first), self.before_first)
        self.assertEqual(snapshot(self.second), self.before_second)

    def test_success_preserves_backups_and_records_permissions(self):
        path = self.commit()
        self.assertEqual(path, self.journal / "transaction.json")
        for index, change in enumerate(self.changes):
            self.assertEqual(snapshot(change.path), change.after)
            backup = self.journal / f"{index:06d}.before"
            self.assertEqual(backup.read_bytes(), change.before.content)
            self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        state = self.state()
        self.assertEqual(state["status"], "COMMITTED")
        self.assertEqual([item["status"] for item in state["targets"]], ["APPLIED", "APPLIED"])
        self.assertEqual(state["targets"][0]["before_mode"], 0o640)

    def test_preflight_later_conflict_leaves_all_other_targets_unchanged(self):
        self.second.write_bytes(b"external edit")
        with self.assertRaises(AssetError):
            self.commit()
        self.assertEqual(snapshot(self.first), self.before_first)
        self.assertEqual(self.second.read_bytes(), b"external edit")
        self.assertFalse(self.journal.exists())

    def test_duplicate_or_outside_target_rejected_before_journal_creation(self):
        outside = self.root / "outside.md"
        outside.write_bytes(b"outside")
        variants = (
            (self.changes[0], self.changes[0]),
            (TargetChange(outside, snapshot(outside), Snapshot(b"new", 0o600)),),
        )
        for changes in variants:
            with self.subTest(changes=changes), self.assertRaises(AssetError):
                self.commit(changes)
            self.assertFalse(self.journal.exists())
            self.assert_originals()
        self.assertEqual(outside.read_bytes(), b"outside")

    def test_existing_journal_never_overwritten(self):
        self.journal.mkdir()
        marker = self.journal / "keep"
        marker.write_bytes(b"history")
        with self.assertRaises(AssetError):
            self.commit()
        self.assertEqual(marker.read_bytes(), b"history")
        self.assert_originals()

    def test_backup_failure_happens_before_target_writes(self):
        original = transaction.atomic_replace

        def fail_second_backup(path, content, expected, **kwargs):
            if Path(path).name == "000001.before":
                raise OSError("injected backup failure")
            return original(path, content, expected, **kwargs)

        with patch.object(transaction, "atomic_replace", side_effect=fail_second_backup):
            with self.assertRaises(OSError):
                self.commit()
        self.assert_originals()
        self.assertEqual((self.journal / "000000.before").read_bytes(), b"original-first")

    def test_second_target_failure_restores_first(self):
        original = transaction.apply_snapshot

        def fail_second(path, expected, desired):
            if path == self.second and desired == self.changes[1].after:
                raise OSError("injected second-target failure")
            return original(path, expected, desired)

        with patch.object(transaction, "apply_snapshot", side_effect=fail_second):
            with self.assertRaises(TransactionError):
                self.commit()
        self.assert_originals()
        self.assertEqual(self.state()["status"], "ROLLED_BACK")

    def test_failure_after_actual_replacement_still_restores_target(self):
        original = transaction.apply_snapshot

        def fail_after_replace(path, expected, desired):
            original(path, expected, desired)
            if path == self.second and desired == self.changes[1].after:
                raise OSError("injected failure after replacement")

        with patch.object(transaction, "apply_snapshot", side_effect=fail_after_replace):
            with self.assertRaises(TransactionError):
                self.commit()
        self.assert_originals()
        self.assertEqual(self.state()["status"], "ROLLED_BACK")

    def test_external_edit_during_failure_is_preserved(self):
        original = transaction.apply_snapshot

        def edit_and_fail(path, expected, desired):
            if path == self.second and desired == self.changes[1].after:
                self.first.write_bytes(b"external edit after first commit")
                raise OSError("injected failure with external edit")
            return original(path, expected, desired)

        with patch.object(transaction, "apply_snapshot", side_effect=edit_and_fail):
            with self.assertRaises(TransactionError):
                self.commit()
        self.assertEqual(self.first.read_bytes(), b"external edit after first commit")
        self.assertEqual(snapshot(self.second), self.before_second)
        state = self.state()
        self.assertEqual(state["status"], "RECOVERY_BLOCKED")
        self.assertEqual(state["targets"][0]["status"], "RECOVERY_BLOCKED")
        self.assertEqual((self.journal / "000000.before").read_bytes(), b"original-first")

    def test_create_and_delete_success(self):
        new = self.target / "new.md"
        changes = (
            TargetChange(new, Snapshot(None, None), Snapshot(b"created", 0o644)),
            TargetChange(self.first, self.before_first, Snapshot(None, None)),
        )
        self.commit(changes)
        self.assertEqual(snapshot(new), Snapshot(b"created", 0o644))
        self.assertFalse(self.first.exists())
        self.assertEqual(snapshot(self.second), self.before_second)
        self.assertIsNone(self.state()["targets"][0]["backup"])

    def test_failed_batch_restores_deleted_file_and_removes_created_file(self):
        new = self.target / "new.md"
        changes = (
            TargetChange(new, Snapshot(None, None), Snapshot(b"created", 0o644)),
            TargetChange(self.first, self.before_first, Snapshot(None, None)),
            self.changes[1],
        )
        original = transaction.apply_snapshot

        def fail_last(path, expected, desired):
            if path == self.second:
                raise OSError("injected final target failure")
            return original(path, expected, desired)

        with patch.object(transaction, "apply_snapshot", side_effect=fail_last):
            with self.assertRaises(TransactionError):
                self.commit(changes)
        self.assertFalse(new.exists())
        self.assert_originals()
        self.assertEqual(self.state()["status"], "ROLLED_BACK")

    def test_unchanged_target_is_not_replaced(self):
        inode = self.first.stat().st_ino
        self.commit((TargetChange(self.first, self.before_first, self.before_first),))
        self.assertEqual(self.first.stat().st_ino, inode)
        self.assertEqual(self.state()["targets"][0]["status"], "UNCHANGED")


if __name__ == "__main__":
    unittest.main()
