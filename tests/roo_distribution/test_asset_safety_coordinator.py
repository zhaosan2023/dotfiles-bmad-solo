"""部署协调器隔离测试；不证明 Shell 入口或 Roo 运行时已通过。"""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from asset_safety import AssetError, Snapshot, deployment_lock, parse_modes
from deploy_managed import deploy
import asset_transaction as transaction


class CoordinatorSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sandbox-", dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / "state"
        self.state.mkdir()
        self.files = {"rules/managed.md": Snapshot(b"managed", 0o644)}
        self.modes = {"settings/custom_modes.yaml": b"customModes: [{slug: bmad-engineer, name: Engineer}]\n"}

    def run_deploy(self, **options):
        return deploy(self.root, self.state, self.files, self.modes, **options)

    def tree(self):
        return {str(path.relative_to(self.root)): (path.read_bytes(), path.stat().st_mode)
                for path in self.root.rglob("*") if path.is_file()}

    def test_install_and_idempotence(self):
        journal = self.run_deploy()
        self.assertTrue(journal.is_file())
        self.assertEqual((self.root / "rules/managed.md").read_bytes(), b"managed")
        manifest = json.loads((self.state / "ownership.json").read_bytes())
        self.assertEqual(set(manifest["files"]), set(self.files))
        self.assertEqual(set(manifest["modes"]), set(self.modes))
        before = self.tree()
        self.assertIsNone(self.run_deploy())
        self.assertEqual(self.tree(), before)

    def test_dry_run_creates_no_directories_lock_or_manifest(self):
        before = self.tree()
        directories = sorted(str(path) for path in self.root.rglob("*"))
        changes = self.run_deploy(dry_run=True)
        self.assertTrue(changes)
        self.assertEqual(self.tree(), before)
        self.assertEqual(sorted(str(path) for path in self.root.rglob("*")), directories)

    def test_corrupt_mode_prevents_other_target_writes(self):
        settings = self.root / "settings"
        settings.mkdir()
        target = settings / "custom_modes.yaml"
        target.write_bytes(b"customModes: [")
        with self.assertRaises(AssetError):
            self.run_deploy()
        self.assertEqual(target.read_bytes(), b"customModes: [")
        self.assertFalse((self.root / "rules").exists())
        self.assertFalse((self.state / "ownership.json").exists())
        self.assertEqual(list(self.state.glob("transaction-*")), [])

    def test_uninstall_preserves_third_party_assets(self):
        self.run_deploy()
        personal = self.root / "rules/personal.md"
        personal.write_bytes(b"personal")
        target = self.root / "settings/custom_modes.yaml"
        target.write_bytes(target.read_bytes() + b"theme: dark\n")
        deploy(self.root, self.state, {}, {}, uninstall=True)
        self.assertFalse((self.root / "rules/managed.md").exists())
        self.assertEqual(personal.read_bytes(), b"personal")
        self.assertEqual(parse_modes(target.read_bytes()), {"customModes": [], "theme": "dark"})
        manifest = json.loads((self.state / "ownership.json").read_bytes())
        self.assertEqual(manifest["files"], {})
        self.assertEqual(manifest["modes"], {})

    def test_user_modified_owned_file_blocks_entire_update(self):
        self.run_deploy()
        (self.root / "rules/managed.md").write_bytes(b"user edit")
        before = self.tree()
        with self.assertRaises(AssetError):
            self.run_deploy()
        self.assertEqual(self.tree(), before)

    def test_unfinished_transaction_blocks_new_deployment(self):
        pending = self.state / "transaction-interrupted"
        pending.mkdir()
        (pending / "transaction.json").write_text('{"status":"COMMITTING"}')
        with self.assertRaises(AssetError):
            self.run_deploy()
        self.assertFalse((self.root / "rules").exists())

    def test_second_writer_is_rejected(self):
        with deployment_lock(self.state / "deployment.lock"):
            with self.assertRaises(AssetError):
                self.run_deploy()
        self.assertFalse((self.root / "rules").exists())

    def test_manifest_failure_rolls_back_all_new_assets(self):
        original = transaction.apply_snapshot

        def fail_manifest(path, expected, desired):
            if path == self.state / "ownership.json":
                raise OSError("模拟所有权清单提交失败")
            return original(path, expected, desired)

        with patch.object(transaction, "apply_snapshot", side_effect=fail_manifest):
            with self.assertRaises(transaction.TransactionError):
                self.run_deploy()
        self.assertFalse((self.root / "rules").exists())
        self.assertFalse((self.root / "settings").exists())
        self.assertFalse((self.state / "ownership.json").exists())
        journals = list(self.state.glob("transaction-*/transaction.json"))
        self.assertEqual(len(journals), 1)
        self.assertEqual(json.loads(journals[0].read_bytes())["status"], "ROLLED_BACK")

    def test_source_cannot_target_state_directory(self):
        with self.assertRaises(AssetError):
            deploy(self.root, self.state,
                   {"state/ownership.json": Snapshot(b"overwrite", 0o600)}, {})
        self.assertFalse((self.state / "ownership.json").exists())


if __name__ == "__main__":
    unittest.main()
