"""受管模式合并契约测试；不触碰真实部署目录。"""
from pathlib import Path
import sys
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from asset_safety import AssetError, parse_modes
from managed_modes import merge_modes, mode_digest


def encode(modes, **extra):
    return yaml.safe_dump({**extra, "customModes": modes}).encode("utf-8")


class ManagedModeSafety(unittest.TestCase):
    def setUp(self):
        self.managed = {"slug": "bmad-engineer", "name": "工程模式"}
        self.third_party = {"slug": "personal", "name": "用户模式"}
        self.source = encode([self.managed])

    def test_new_install_preserves_third_party_and_top_level(self):
        original = encode([self.third_party], theme="dark", options={"enabled": True})
        result = merge_modes(original, self.source, {})
        data = parse_modes(result.content)
        self.assertEqual(data["theme"], "dark")
        self.assertEqual(data["options"], {"enabled": True})
        self.assertEqual(data["customModes"], [self.third_party, self.managed])
        self.assertEqual(result.owned, {"bmad-engineer": mode_digest(self.managed)})

    def test_missing_destination_is_supported(self):
        result = merge_modes(None, self.source, {})
        self.assertEqual(parse_modes(result.content)["customModes"], [self.managed])

    def test_first_collision_requires_authorization_even_if_identical(self):
        with self.assertRaises(AssetError):
            merge_modes(self.source, self.source, {})
        result = merge_modes(self.source, self.source, {}, adopt={"bmad-engineer"})
        self.assertEqual(result.content, self.source)
        self.assertEqual(result.owned["bmad-engineer"], mode_digest(self.managed))

    def test_managed_update_preserves_order_and_other_modes(self):
        original = encode([self.managed, self.third_party])
        updated = {**self.managed, "name": "更新后的工程模式"}
        owned = {"bmad-engineer": mode_digest(self.managed)}
        result = merge_modes(original, encode([updated]), owned)
        self.assertEqual(parse_modes(result.content)["customModes"], [updated, self.third_party])
        self.assertEqual(result.owned["bmad-engineer"], mode_digest(updated))

    def test_user_edit_blocks_update_uninstall_and_adoption_override(self):
        edited = encode([{**self.managed, "name": "用户自定义"}])
        owned = {"bmad-engineer": mode_digest(self.managed)}
        for options in ({}, {"uninstall": True}, {"adopt": {"bmad-engineer"}}):
            with self.subTest(options=options), self.assertRaises(AssetError):
                merge_modes(edited, self.source, owned, **options)

    def test_missing_owned_mode_requires_reconciliation(self):
        with self.assertRaises(AssetError):
            merge_modes(encode([]), self.source,
                        {"bmad-engineer": mode_digest(self.managed)})

    def test_uninstall_only_removes_owned_modes(self):
        original = encode([self.managed, self.third_party], theme="dark")
        result = merge_modes(original, None,
                             {"bmad-engineer": mode_digest(self.managed)}, uninstall=True)
        self.assertEqual(parse_modes(result.content),
                         {"theme": "dark", "customModes": [self.third_party]})
        self.assertEqual(result.owned, {})

    def test_retired_mode_removed_only_when_ownership_matches(self):
        replacement = {"slug": "ana-architect", "name": "分析模式"}
        result = merge_modes(encode([self.managed, self.third_party]), encode([replacement]),
                             {"bmad-engineer": mode_digest(self.managed)})
        self.assertEqual(parse_modes(result.content)["customModes"],
                         [self.third_party, replacement])
        self.assertEqual(set(result.owned), {"ana-architect"})

    def test_idempotence_preserves_original_bytes(self):
        original = b"# user comment\ntheme: dark\ncustomModes:\n- slug: personal\n  name: User\n"
        result = merge_modes(original, None, {}, uninstall=True)
        self.assertEqual(result.content, original)
        installed = merge_modes(None, self.source, {})
        repeated = merge_modes(installed.content, self.source, installed.owned)
        self.assertEqual(repeated, installed)

    def test_invalid_destination_fails_closed(self):
        for original in (b"", b"null", b"customModes: [", b"customModes: []\ncustomModes: []"):
            with self.subTest(original=original), self.assertRaises(AssetError):
                merge_modes(original, self.source, {})

    def test_invalid_source_rejected(self):
        for source in (None, b"{}", encode([]), encode([self.managed], theme="dark")):
            with self.subTest(source=source), self.assertRaises(AssetError):
                merge_modes(None, source, {})

    def test_invalid_ownership_rejected(self):
        for owned in ([], {"bmad-engineer": "invalid"}, {"": "a" * 64}):
            with self.subTest(owned=owned), self.assertRaises(AssetError):
                merge_modes(None, self.source, owned)

    def test_adoption_must_be_scoped_and_not_used_for_uninstall(self):
        for options in ({"adopt": {"unknown"}}, {"adopt": "bmad-engineer"},
                        {"adopt": {"bmad-engineer"}, "uninstall": True}):
            with self.subTest(options=options), self.assertRaises(AssetError):
                merge_modes(None, self.source, {}, **options)

    def test_mode_digest_ignores_mapping_order(self):
        self.assertEqual(mode_digest({"slug": "x", "name": "X"}),
                         mode_digest({"name": "X", "slug": "x"}))

    def test_non_finite_mode_data_rejected(self):
        with self.assertRaises(AssetError):
            merge_modes(None, b"customModes: [{slug: x, value: .nan}]", {})


if __name__ == "__main__":
    unittest.main()
