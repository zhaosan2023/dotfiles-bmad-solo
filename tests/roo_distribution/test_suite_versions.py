"""唯一 V4 固定身份、可选身份文件及来源安全反例。"""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from asset_safety import AssetError
from suite_versions import SUITES, select_source, suite_spec, validate_identity, validate_tag_hint


class SuiteVersions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sandbox-", dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "bmad-suite-v4"
        self.source.mkdir()
        (self.source / "plugin.json").write_text('{"name":"bmad-suite"}', encoding="utf-8")
        self.identity = {"schema_version": 1, "suite_id": "bmad-suite-v4",
                         "major_version": "v4", "source_path": "bmad-suite-v4"}

    def test_only_v4_and_legacy_identity(self):
        self.assertEqual(set(SUITES), {"v4"})
        self.assertEqual(select_source(self.root, "v4"), self.source)
        (self.source / "suite.json").write_text(json.dumps(self.identity), encoding="utf-8")
        self.assertEqual(select_source(self.root, "v4"), self.source)

    def test_retired_unknown_and_implicit_identity_rejected(self):
        for version in (None, "", "4", "latest", "v1", "v3", "v5", "v6"):
            with self.subTest(version=version), self.assertRaises(AssetError):
                suite_spec(version)

    def test_missing_v4_never_uses_generic_suite(self):
        self.source.rename(self.root / "bmad-suite")
        with self.assertRaises(AssetError):
            select_source(self.root, "v4")

    def test_corrupt_optional_identity_rejected(self):
        for content in ("[]", "{", '{"schema_version":1,"schema_version":1}',
                        json.dumps(dict(self.identity, schema_version=True)),
                        json.dumps(dict(self.identity, major_version="v5"))):
            (self.source / "suite.json").write_text(content, encoding="utf-8")
            with self.subTest(content=content), self.assertRaises(AssetError):
                select_source(self.root, "v4")

    def test_wrong_directory_or_plugin_slot_rejected(self):
        moved = self.root / "other"
        self.source.rename(moved)
        with self.assertRaises(AssetError):
            validate_identity(moved, suite_spec("v4"))
        moved.rename(self.source)
        (self.source / "plugin.json").write_text('{"name":"other"}', encoding="utf-8")
        with self.assertRaises(AssetError):
            select_source(self.root, "v4")

    def test_source_or_identity_symlink_rejected(self):
        target = self.root / "identity.json"
        target.write_text(json.dumps(self.identity), encoding="utf-8")
        identity = self.source / "suite.json"
        identity.symlink_to(target)
        with self.assertRaises(AssetError):
            select_source(self.root, "v4")
        identity.unlink()
        relocated = self.root / "relocated"
        self.source.rename(relocated)
        self.source.symlink_to(relocated, target_is_directory=True)
        with self.assertRaises(AssetError):
            select_source(self.root, "v4")

    def test_commit_cache_name_keeps_v4_format(self):
        for commit in ("a" * 40, "b" * 64):
            self.assertEqual(suite_spec("v4").cache_name(commit), "commit-" + commit)
        for invalid in ("tag", "../escape", "a" * 39, None):
            with self.subTest(commit=invalid), self.assertRaises(AssetError):
                suite_spec("v4").cache_name(invalid)

    def test_tag_hint_conflict_is_fail_closed(self):
        validate_tag_hint("v4.2.0", suite_spec("v4"))
        validate_tag_hint("release-2026", suite_spec("v4"))
        for tag in ("v3.0.0", "v5.0.0", ""):
            with self.subTest(tag=tag), self.assertRaises(AssetError):
                validate_tag_hint(tag, suite_spec("v4"))


if __name__ == "__main__":
    unittest.main()
