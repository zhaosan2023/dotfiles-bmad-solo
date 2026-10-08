"""首次部署状态目录创建的隔离验证，不触碰真实全局配置。"""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from asset_safety import AssetError, Snapshot
from deploy_managed import deploy


class BootstrapSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="sandbox-", dir=Path(__file__).parent
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / "metadata" / "deployment"
        self.files = {"rules/managed.md": Snapshot(b"managed", 0o644)}
        self.modes = {
            "settings/custom_modes.yaml":
                b"customModes: [{slug: bmad-engineer, name: Engineer}]\n"
        }

    def test_first_install_creates_state_after_preflight(self):
        journal = deploy(self.root, self.state, self.files, self.modes)
        self.assertTrue(journal.is_file())
        self.assertTrue((self.state / "ownership.json").is_file())
        self.assertTrue((self.state / "deployment.lock").is_file())
        self.assertEqual((self.root / "rules/managed.md").read_bytes(), b"managed")
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o700)

    def test_first_dry_run_does_not_create_state_or_targets(self):
        changes = deploy(self.root, self.state, self.files, self.modes, dry_run=True)
        self.assertTrue(changes)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_corrupt_target_does_not_create_state_directory(self):
        target = self.root / "settings/custom_modes.yaml"
        target.parent.mkdir()
        target.write_bytes(b"customModes: [")
        before = sorted(path.relative_to(self.root).as_posix()
                        for path in self.root.rglob("*"))
        with self.assertRaises(AssetError):
            deploy(self.root, self.state, self.files, self.modes)
        self.assertFalse(self.state.parent.exists())
        self.assertFalse((self.root / "rules").exists())
        self.assertEqual(target.read_bytes(), b"customModes: [")
        self.assertEqual(before, sorted(path.relative_to(self.root).as_posix()
                                       for path in self.root.rglob("*")))

    def test_unowned_collision_does_not_create_state_directory(self):
        target = self.root / "rules/managed.md"
        target.parent.mkdir()
        target.write_bytes(b"personal")
        with self.assertRaises(AssetError):
            deploy(self.root, self.state, self.files, self.modes)
        self.assertFalse(self.state.parent.exists())
        self.assertFalse((self.root / "settings").exists())
        self.assertEqual(target.read_bytes(), b"personal")

    def test_state_file_is_rejected_without_overwrite(self):
        self.state.parent.mkdir()
        self.state.write_bytes(b"keep")
        with self.assertRaises(AssetError):
            deploy(self.root, self.state, self.files, self.modes)
        self.assertEqual(self.state.read_bytes(), b"keep")
        self.assertFalse((self.root / "rules").exists())

    def test_symlink_state_parent_is_rejected(self):
        destination = self.root / "other"
        destination.mkdir()
        self.state.parent.symlink_to(destination, target_is_directory=True)
        with self.assertRaises(AssetError):
            deploy(self.root, self.state, self.files, self.modes)
        self.assertEqual(list(destination.iterdir()), [])
        self.assertFalse((self.root / "rules").exists())


if __name__ == "__main__":
    unittest.main()
