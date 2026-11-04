"""两段新发布、单源展示和旧套件兼容；仅使用项目内临时文件。"""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from asset_safety import AssetError
from release_version import check_repository, main, read_release, validate_release


class ReleaseVersions(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="sandbox-release-", dir=Path(__file__).parent)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "bmad-suite-v4"
        self.source.mkdir()
        self.version_file = self.source / "VERSION"
        self.version_file.write_bytes(b"v4.3\n")
        self.readme = self.root / "README.md"
        self.readme.write_text(
            "[![Version](https://img.shields.io/badge/version-v4.3-blue.svg)]"
            "(bmad-suite-v4/VERSION)\n", encoding="utf-8",
        )

    def test_current_repository_uses_one_declared_release(self):
        declared = read_release(ROOT / "bmad-suite-v4")
        self.assertEqual(validate_release(declared), declared)
        self.assertEqual(check_repository(ROOT), declared)

    def test_two_segment_releases_allow_minor_growth(self):
        for version in ("v4.0", "v4.3", "v4.10", "v4.100"):
            with self.subTest(version=version):
                self.assertEqual(validate_release(version), version)

    def test_new_release_format_rejects_other_versions_and_shell_content(self):
        for version in (None, "", "v4", "4.3", "v5.3", "v4.03", "v4.3.0",
                        "v4.3-rc1", "v4.3\n", "v4.3; echo invalid", "../v4.3"):
            with self.subTest(version=version), self.assertRaises(AssetError):
                validate_release(version)

    def test_matching_tag_and_badge_are_accepted_without_writes(self):
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(check_repository(self.root, tag="v4.3"), "v4.3")
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_mismatched_or_patch_tag_is_not_a_new_release(self):
        for tag in ("v4.4", "v4.3.0", "release-2026"):
            with self.subTest(tag=tag), self.assertRaises(AssetError):
                check_repository(self.root, tag=tag)

    def test_display_mismatch_duplicate_and_unpublished_link_are_rejected(self):
        original = self.readme.read_text(encoding="utf-8")
        for content in (original.replace("v4.3-blue", "v4.2-blue"), original * 2,
                        original.replace("bmad-suite-v4/VERSION", "https://example.invalid/releases/v4.3")):
            self.readme.write_text(content, encoding="utf-8")
            with self.assertRaises(AssetError):
                check_repository(self.root)

    def test_missing_version_is_only_supported_for_explicit_legacy_read(self):
        self.version_file.unlink()
        with self.assertRaises(AssetError):
            read_release(self.source)
        self.assertEqual(read_release(self.source, allow_legacy=True), "v4")
        with self.assertRaises(AssetError):
            check_repository(self.root)

    def test_corrupt_version_never_falls_back_to_legacy(self):
        for content in (b"", b"v4.3", b"v4.3\n\n", b" v4.3\n", b"v4.3.0\n", b"\xff\n"):
            self.version_file.write_bytes(content)
            with self.subTest(content=content), self.assertRaises(AssetError):
                read_release(self.source, allow_legacy=True)

    def test_linked_version_and_linked_source_are_rejected(self):
        other = self.root / "other-version"
        other.write_bytes(b"v4.3\n")
        self.version_file.unlink()
        self.version_file.symlink_to(other)
        with self.assertRaises(AssetError):
            read_release(self.source)
        self.version_file.unlink()
        self.version_file.write_bytes(b"v4.3\n")
        alias = self.root / "alias"
        alias.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(AssetError):
            read_release(alias)

    def test_cli_rejects_legacy_permission_for_repository_check(self):
        with self.assertRaises(SystemExit) as result:
            main(["--root", str(self.root), "--allow-legacy"])
        self.assertEqual(result.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
