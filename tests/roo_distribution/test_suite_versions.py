"""套件身份与固定版本映射；仅使用项目内临时夹具。"""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from asset_safety import AssetError
from suite_versions import (
    select_source, suite_spec, validate_identity, validate_tag_hint,
)


class SuiteVersions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="sandbox-", dir=Path(__file__).parent
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def make_suite(self, version):
        spec = suite_spec(version)
        source = self.root / spec.source_path
        source.mkdir()
        plugin = {"name": "bmad-suite"}
        if version == "v5":
            plugin["displayName"] = "BMRalph V5"
            identity = {
                "schema_version": 1, "suite_id": spec.suite_id,
                "major_version": version, "source_path": spec.source_path,
            }
            (source / "suite.json").write_text(json.dumps(identity), encoding="utf-8")
        (source / "plugin.json").write_text(json.dumps(plugin), encoding="utf-8")
        return source

    def test_explicit_v5_and_legacy_v4_identity(self):
        for version in ("v4", "v5"):
            with self.subTest(version=version):
                source = self.make_suite(version)
                self.assertEqual(select_source(self.root, version), source)

    def test_missing_v5_never_falls_back(self):
        self.make_suite("v4")
        (self.root / "bmad-suite").mkdir()
        with self.assertRaises(AssetError):
            select_source(self.root, "v5")

    def test_unknown_or_implicit_version_rejected(self):
        for version in (None, "", "5", "latest", "v6"):
            with self.subTest(version=version), self.assertRaises(AssetError):
                suite_spec(version)

    def test_v5_missing_or_corrupt_identity_rejected(self):
        source = self.make_suite("v5")
        identity = source / "suite.json"
        identity.unlink()
        with self.assertRaises(AssetError):
            select_source(self.root, "v5")
        for content in ("[]", "{", '{"schema_version":1,"schema_version":1}',
                        '{"schema_version":true}',
                        '{"schema_version":1,"major_version":"v4"}'):
            identity.write_text(content, encoding="utf-8")
            with self.subTest(content=content), self.assertRaises(AssetError):
                select_source(self.root, "v5")

    def test_wrong_version_or_plugin_slot_rejected(self):
        source = self.make_suite("v5")
        with self.assertRaises(AssetError):
            validate_identity(source, suite_spec("v4"))
        (source / "plugin.json").write_text('{"name":"other"}', encoding="utf-8")
        with self.assertRaises(AssetError):
            select_source(self.root, "v5")

    def test_source_or_identity_symlink_rejected(self):
        source = self.make_suite("v5")
        identity = source / "suite.json"
        target = self.root / "identity.json"
        identity.rename(target)
        identity.symlink_to(target)
        with self.assertRaises(AssetError):
            select_source(self.root, "v5")
        identity.unlink()
        target.rename(identity)
        relocated = self.root / "relocated"
        source.rename(relocated)
        source.symlink_to(relocated, target_is_directory=True)
        with self.assertRaises(AssetError):
            select_source(self.root, "v5")

    def test_cache_names_keep_v4_compatibility_and_separate_v5(self):
        commit = "a" * 40
        self.assertEqual(suite_spec("v4").cache_name(commit), "commit-" + commit)
        self.assertEqual(suite_spec("v5").cache_name(commit), "v5-commit-" + commit)
        for invalid in ("tag", "../escape", "a" * 39, None):
            with self.subTest(commit=invalid), self.assertRaises(AssetError):
                suite_spec("v5").cache_name(invalid)

    def test_tag_hint_conflict_is_fail_closed(self):
        validate_tag_hint("v5.0.0", suite_spec("v5"))
        validate_tag_hint("release-2026", suite_spec("v5"))
        with self.assertRaises(AssetError):
            validate_tag_hint("v4.1.0", suite_spec("v5"))


if __name__ == "__main__":
    unittest.main()
