"""受管文件计划的隔离契约测试；不代表部署事务已通过。"""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from asset_safety import AssetError, Snapshot
from managed_files import ownership_record, plan_files, validate_relative_path


class ManagedFileSafety(unittest.TestCase):
    def setUp(self):
        self.path = "rules/managed.md"
        self.original = Snapshot(b"original", 0o640)
        self.updated = Snapshot(b"updated", 0o640)
        self.missing = Snapshot(None, None)
        self.owned = {self.path: ownership_record(self.original)}

    def test_new_file_and_unknown_file_preserved(self):
        current = {self.path: self.missing, "rules/personal.md": self.original}
        result = plan_files(current, {self.path: self.updated}, {})
        self.assertEqual(len(result.changes), 1)
        self.assertEqual(result.changes[0].relative_path, self.path)
        self.assertEqual(result.changes[0].after, self.updated)
        self.assertEqual(set(result.owned), {self.path})
        self.assertEqual(current["rules/personal.md"], self.original)

    def test_collision_requires_explicit_adoption_even_if_identical(self):
        current = {self.path: self.original}
        desired = dict(current)
        with self.assertRaises(AssetError):
            plan_files(current, desired, {})
        result = plan_files(current, desired, {}, adopt={self.path})
        self.assertEqual(result.changes, ())
        self.assertEqual(result.owned, self.owned)

    def test_managed_update_and_idempotence(self):
        result = plan_files({self.path: self.original},
                            {self.path: self.updated}, self.owned)
        self.assertEqual(result.changes[0].before, self.original)
        self.assertEqual(result.changes[0].after, self.updated)
        repeated = plan_files({self.path: self.updated},
                              {self.path: self.updated}, result.owned)
        self.assertEqual(repeated.changes, ())
        self.assertEqual(repeated.owned, result.owned)

    def test_user_changes_and_missing_owned_file_block(self):
        for value in (self.updated, Snapshot(b"original", 0o600), self.missing):
            for uninstall in (False, True):
                with self.subTest(value=value, uninstall=uninstall):
                    with self.assertRaises(AssetError):
                        plan_files({self.path: value},
                                   {} if uninstall else {self.path: self.updated},
                                   self.owned, uninstall=uninstall)

    def test_adoption_cannot_override_managed_conflict(self):
        with self.assertRaises(AssetError):
            plan_files({self.path: self.updated}, {self.path: self.original},
                       self.owned, adopt={self.path})

    def test_uninstall_only_removes_owned_files(self):
        result = plan_files({self.path: self.original, "personal.md": self.updated},
                            {}, self.owned, uninstall=True)
        self.assertEqual(len(result.changes), 1)
        self.assertEqual(result.changes[0].relative_path, self.path)
        self.assertEqual(result.changes[0].after, self.missing)
        self.assertEqual(result.owned, {})

    def test_retired_owned_file_removed(self):
        result = plan_files({self.path: self.original, "new.md": self.missing},
                            {"new.md": self.updated}, self.owned)
        changes = {change.relative_path: change for change in result.changes}
        self.assertEqual(changes[self.path].after, self.missing)
        self.assertEqual(changes["new.md"].after, self.updated)
        self.assertEqual(set(result.owned), {"new.md"})

    def test_missing_probe_is_not_missing_file(self):
        with self.assertRaises(AssetError):
            plan_files({}, {self.path: self.updated}, {})
        with self.assertRaises(AssetError):
            plan_files({}, {}, self.owned, uninstall=True)

    def test_invalid_paths(self):
        for path in ("", "/absolute", "../escape", "a/../b", "a/./b",
                     "a//b", "a/", "a\\b", "a\nb", "."):
            with self.subTest(path=path), self.assertRaises(AssetError):
                validate_relative_path(path)
        validate_relative_path("rules/normal-file.md")

    def test_file_directory_collision(self):
        desired = {"rules": self.updated, "rules/item.md": self.updated}
        with self.assertRaises(AssetError):
            plan_files({path: self.missing for path in desired}, desired, {})

    def test_invalid_source_snapshots(self):
        for value in (self.missing, Snapshot(b"x", 0o4755),
                      Snapshot(b"x", True), Snapshot("text", 0o600)):
            with self.subTest(value=value), self.assertRaises(AssetError):
                plan_files({self.path: self.missing}, {self.path: value}, {})

    def test_invalid_ownership(self):
        for record in ({}, {"sha256": "invalid", "mode": 0o640},
                       {"sha256": "a" * 64, "mode": True},
                       {**ownership_record(self.original), "extra": 1}):
            with self.subTest(record=record), self.assertRaises(AssetError):
                plan_files({self.path: self.original}, {},
                           {self.path: record}, uninstall=True)

    def test_invalid_adoption_and_uninstall_combinations(self):
        for options in ({"adopt": "rules/managed.md"},
                        {"adopt": {"unknown.md"}}, {"uninstall": True}):
            with self.subTest(options=options), self.assertRaises(AssetError):
                plan_files({self.path: self.missing}, {self.path: self.updated},
                           {}, **options)
        with self.assertRaises(AssetError):
            plan_files({}, {}, {}, uninstall=True, adopt={"unknown.md"})

    def test_changes_have_deterministic_order(self):
        desired = {"z.md": self.updated, "a.md": self.updated}
        result = plan_files({path: self.missing for path in desired}, desired, {})
        self.assertEqual([change.relative_path for change in result.changes],
                         ["a.md", "z.md"])


if __name__ == "__main__":
    unittest.main()
