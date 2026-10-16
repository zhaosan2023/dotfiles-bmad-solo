"""受控回滚反例：仅在临时根恢复受管批次，不恢复真实工作树。

复用公共事务；不构成 V5 的跨套件运行依赖，也不证明宿主回切。
"""
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


class ControlledRollbackGuards(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(
            prefix="sandbox-controlled-rollback-", dir=Path(__file__).parent
        )
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.journal = self.root / "transaction-evidence"
        self.lock = self.root / "deployment.lock"
        self.third_party = self.root / "third-party.md"
        self.user_file = self.root / "user-uncommitted.md"
        self.put(self.third_party, b"third-party asset", 0o640)
        self.put(self.user_file, b"user pre-existing uncommitted changes", 0o600)
        self.protected = {
            path: snapshot(path) for path in (self.third_party, self.user_file)
        }

    def put(self, path, content, mode):
        path.write_bytes(content)
        path.chmod(mode)
        return snapshot(path)

    def change(self, name, before, after):
        path = self.root / name
        if before.content is not None:
            self.put(path, before.content, before.mode)
        return transaction.TargetChange(path, before, after)

    def commit(self, changes):
        with deployment_lock(self.lock):
            return transaction.commit_changes(
                tuple(changes), (self.root,), self.journal
            )

    def state(self):
        return json.loads((self.journal / "transaction.json").read_bytes())

    def assert_protected(self):
        for path, expected in self.protected.items():
            self.assertEqual(snapshot(path), expected)
        self.assertEqual(list(self.root.rglob(".bmad-write-*")), [])

    def test_failure_restores_only_batch_bytes_modes_creation_and_deletion(self):
        changes = (
            self.change("managed-existing.md", Snapshot(b"user-edited baseline", 0o640),
                        Snapshot(b"this task edit", 0o600)),
            self.change("managed-new.md", Snapshot(None, None),
                        Snapshot(b"this task new file", 0o600)),
            self.change("managed-retired.md", Snapshot(b"original retired bytes", 0o644),
                        Snapshot(None, None)),
            self.change("managed-final.md", Snapshot(b"final original", 0o600),
                        Snapshot(b"final candidate", 0o640)),
        )
        actual_apply = transaction.apply_snapshot

        def fail_after_final_replace(path, expected, desired):
            actual_apply(path, expected, desired)
            if path == changes[-1].path and desired == changes[-1].after:
                raise OSError("injected failure after replacement")

        with patch.object(transaction, "apply_snapshot", side_effect=fail_after_final_replace):
            with self.assertRaises(transaction.TransactionError):
                self.commit(changes)
        state = self.state()
        self.assertEqual(state["status"], "ROLLED_BACK")
        self.assertTrue(all(item["status"] == "RESTORED" for item in state["targets"]))
        for change, record in zip(changes, state["targets"]):
            self.assertEqual(snapshot(change.path), change.before)
            if record["backup"] is not None:
                self.assertEqual((self.journal / record["backup"]).read_bytes(),
                                 change.before.content)
        self.assert_protected()

    def test_concurrent_managed_user_edit_blocks_restore_without_overwrite(self):
        first = self.change("managed-first.md", Snapshot(b"first before", 0o640),
                            Snapshot(b"first after", 0o600))
        second = self.change("managed-second.md", Snapshot(b"second before", 0o600),
                             Snapshot(b"second after", 0o640))
        concurrent = Snapshot(b"concurrent user edit on managed file", 0o644)
        actual_apply = transaction.apply_snapshot

        def conflict_before_second(path, expected, desired):
            if path == second.path and desired == second.after:
                self.put(first.path, concurrent.content, concurrent.mode)
                raise OSError("injected second-target failure")
            actual_apply(path, expected, desired)

        with patch.object(transaction, "apply_snapshot", side_effect=conflict_before_second):
            with self.assertRaises(transaction.TransactionError):
                self.commit((first, second))
        state = self.state()
        self.assertEqual(state["status"], "RECOVERY_BLOCKED")
        self.assertEqual(state["targets"][0]["status"], "RECOVERY_BLOCKED")
        self.assertEqual(state["targets"][1]["status"], "RESTORED")
        self.assertEqual(snapshot(first.path), concurrent)
        self.assertEqual(snapshot(second.path), second.before)
        self.assertEqual((self.journal / "000000.before").read_bytes(), first.before.content)
        self.assert_protected()

    def test_edit_between_restore_check_and_replace_is_preserved(self):
        first = self.change("managed-first.md", Snapshot(b"first before", 0o640),
                            Snapshot(b"first after", 0o600))
        second = self.change("managed-second.md", Snapshot(b"second before", 0o600),
                             Snapshot(b"second after", 0o640))
        concurrent = Snapshot(b"user edit during rollback", 0o644)
        actual_apply = transaction.apply_snapshot

        def mutate_at_restore(path, expected, desired):
            if path == second.path and desired == second.after:
                raise OSError("injected commit failure")
            if path == first.path and desired == first.before:
                self.put(path, concurrent.content, concurrent.mode)
            actual_apply(path, expected, desired)

        with patch.object(transaction, "apply_snapshot", side_effect=mutate_at_restore):
            with self.assertRaises(transaction.TransactionError):
                self.commit((first, second))
        self.assertEqual(self.state()["status"], "RECOVERY_BLOCKED")
        self.assertEqual(snapshot(first.path), concurrent)
        self.assertEqual(snapshot(second.path), second.before)
        self.assert_protected()

    def test_preflight_concurrent_change_blocks_before_any_batch_write(self):
        first = self.change("managed-first.md", Snapshot(b"first before", 0o640),
                            Snapshot(b"first after", 0o600))
        second = self.change("managed-second.md", Snapshot(b"second before", 0o600),
                             Snapshot(b"second after", 0o640))
        concurrent = self.put(second.path, b"user concurrent edit before commit", 0o644)
        with patch.object(transaction, "apply_snapshot") as apply:
            with self.assertRaises(AssetError):
                self.commit((first, second))
        apply.assert_not_called()
        self.assertFalse(self.journal.exists())
        self.assertEqual(snapshot(first.path), first.before)
        self.assertEqual(snapshot(second.path), concurrent)
        self.assert_protected()


if __name__ == "__main__":
    unittest.main()
