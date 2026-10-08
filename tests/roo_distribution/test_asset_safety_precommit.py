"""验证幂等目标仍须复核，不能把预检期间的外部修改接受为新基线。"""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import deploy_managed as coordinator
from asset_safety import AssetError, Snapshot


class PrecommitSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="sandbox-", dir=Path(__file__).parent
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / "state"
        self.state.mkdir()
        self.files = {"rules/managed.md": Snapshot(b"original", 0o644)}
        self.modes = {
            "settings/custom_modes.yaml":
                b"customModes: [{slug: bmad-engineer, name: Engineer}]\n"
        }
        coordinator.deploy(self.root, self.state, self.files, self.modes)
        self.mode_path = self.root / "settings/custom_modes.yaml"
        self.external = b"customModes: [{slug: bmad-engineer, name: External}]\n"

    def test_idempotent_deployment_rechecks_before_returning(self):
        original_prepare = coordinator.prepare
        manifest = (self.state / "ownership.json").read_bytes()
        journals = set(self.state.glob("transaction-*"))

        def prepare_then_external_edit(*args, **kwargs):
            changes = original_prepare(*args, **kwargs)
            self.mode_path.write_bytes(self.external)
            return changes

        with patch.object(coordinator, "prepare", side_effect=prepare_then_external_edit):
            with self.assertRaises(AssetError):
                coordinator.deploy(self.root, self.state, self.files, self.modes)
        self.assertEqual(self.mode_path.read_bytes(), self.external)
        self.assertEqual((self.state / "ownership.json").read_bytes(), manifest)
        self.assertEqual(set(self.state.glob("transaction-*")), journals)

    def test_unchanged_mode_keeps_snapshot_from_merge_validation(self):
        original_merge = coordinator.merge_modes
        updated_files = {"rules/managed.md": Snapshot(b"updated", 0o644)}

        def merge_then_external_edit(*args, **kwargs):
            result = original_merge(*args, **kwargs)
            self.mode_path.write_bytes(self.external)
            return result

        with patch.object(coordinator, "merge_modes", side_effect=merge_then_external_edit):
            with self.assertRaises(AssetError):
                coordinator.deploy(self.root, self.state, updated_files, self.modes)
        self.assertEqual(self.mode_path.read_bytes(), self.external)
        self.assertEqual((self.root / "rules/managed.md").read_bytes(), b"original")


if __name__ == "__main__":
    unittest.main()
