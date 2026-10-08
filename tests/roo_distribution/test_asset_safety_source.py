"""套件源采集与边界验证；不触碰真实部署目录。"""
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from asset_safety import AssetError
from deployment_source import REQUIRED_FILES, collect_source, verify_source


class SourceSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="sandbox-", dir=Path(__file__).parent
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "suite"
        self.source.mkdir()
        for relative in REQUIRED_FILES:
            path = self.source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fixture\n")
        (self.source / "plugin.json").write_bytes(b'{"name":"bmad-suite"}\n')
        (self.source / "roo/settings/custom_modes.yaml").write_bytes(
            b"customModes: [{slug: bmad-engineer, name: Engineer}]\n"
        )
        self.targets = ("ide/settings/custom_modes.yaml",)

    def test_collect_maps_assets_without_writing_targets(self):
        before = {str(path.relative_to(self.source)): path.read_bytes()
                  for path in self.source.rglob("*") if path.is_file()}
        files, modes, sources = collect_source(self.source, self.targets)
        self.assertEqual(set(sources), set(REQUIRED_FILES))
        self.assertEqual(set(modes), set(self.targets))
        self.assertEqual(modes[self.targets[0]], sources["roo/settings/custom_modes.yaml"].content)
        self.assertIn(".gemini/config/plugins/bmad-suite/plugin.json", files)
        self.assertIn(".gemini/config/rules/bmad-core.md", files)
        self.assertIn(".roo/rules/02-bmad-core.md", files)
        self.assertIn(".roo/rules-bmad-engineer/01-bmad-engineer-core.md", files)
        self.assertNotIn(".roo/settings/custom_modes.yaml", files)
        verify_source(self.source, sources)
        self.assertFalse((self.root / "ide").exists())
        self.assertEqual(before, {str(path.relative_to(self.source)): path.read_bytes()
                                 for path in self.source.rglob("*") if path.is_file()})

    def test_missing_required_asset_rejected(self):
        for relative in REQUIRED_FILES:
            path = self.source / relative
            content = path.read_bytes()
            path.unlink()
            try:
                with self.subTest(relative=relative), self.assertRaises(AssetError):
                    collect_source(self.source, self.targets)
            finally:
                path.write_bytes(content)

    def test_symlink_file_directory_and_dangling_link_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "keep").write_bytes(b"protected")
        link = self.source / "link"
        for destination in (outside, outside / "keep", outside / "missing"):
            link.symlink_to(destination)
            try:
                with self.subTest(destination=destination), self.assertRaises(AssetError):
                    collect_source(self.source, self.targets)
            finally:
                link.unlink()
        self.assertEqual((outside / "keep").read_bytes(), b"protected")

    def test_fifo_rejected_without_reading(self):
        os.mkfifo(self.source / "fifo")
        with self.assertRaises(AssetError):
            collect_source(self.source, self.targets)

    def test_hardlink_rejected(self):
        os.link(self.source / "plugin.json", self.source / "alias.json")
        with self.assertRaises(AssetError):
            collect_source(self.source, self.targets)

    def test_generated_manifest_rejected(self):
        (self.source / ".manifest.json").write_bytes(b"{}")
        with self.assertRaises(AssetError):
            collect_source(self.source, self.targets)

    def test_invalid_mode_source_rejected(self):
        path = self.source / "roo/settings/custom_modes.yaml"
        for content in (b"", b"{}", b"customModes: []", b"customModes: [",
                        b"customModes: [{slug: x}, {slug: x}]",
                        b"customModes: [{slug: x}]\ntheme: dark\n"):
            path.write_bytes(content)
            with self.subTest(content=content), self.assertRaises(AssetError):
                collect_source(self.source, self.targets)

    def test_invalid_duplicate_and_overlapping_targets_rejected(self):
        variants = (
            [self.targets[0]],
            ("../escape.yaml",),
            ("/absolute.yaml",),
            (self.targets[0], self.targets[0]),
            (".gemini/config/plugins/bmad-suite/plugin.json",),
        )
        for targets in variants:
            with self.subTest(targets=targets), self.assertRaises(AssetError):
                collect_source(self.source, targets)

    def test_source_changes_and_removal_detected(self):
        _, _, sources = collect_source(self.source, self.targets)
        path = self.source / "plugin.json"
        original = path.read_bytes()
        path.write_bytes(b"changed")
        with self.assertRaises(AssetError):
            verify_source(self.source, sources)
        path.write_bytes(original)
        verify_source(self.source, sources)
        path.unlink()
        with self.assertRaises(AssetError):
            verify_source(self.source, sources)

    def test_empty_mode_targets_do_not_imply_runtime_activation(self):
        files, modes, sources = collect_source(self.source, ())
        self.assertTrue(files)
        self.assertEqual(modes, {})
        self.assertTrue(sources)


if __name__ == "__main__":
    unittest.main()
