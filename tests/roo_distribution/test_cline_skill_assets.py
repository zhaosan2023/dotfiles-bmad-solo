"""Cline 技能副本适配回归；不启动宿主，不写全局配置或访问网络。

仅验证冻结快照、目录身份、资源保真及适配后链接闭包。
这些结果不证明宿主发现、模式绑定、自动技能调用或权限隔离。
"""
from pathlib import Path, PurePosixPath
import os
import re
import shutil
import sys
import tempfile
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from asset_safety import AssetError, Snapshot
from cline_skill_assets import (
    ENTRY_DIRECTORIES, INSTALL_ONLY, SKILL_PREFIX, cline_skill_files,
)
from deployment_source import collect_source


class ClineSkillAssets(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(
            prefix="sandbox-cline-skills-", dir=Path(__file__).parent,
        )
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "bmad-suite-v4"
        shutil.copytree(ROOT / "bmad-suite-v4", self.source)
        _, _, self.sources = collect_source(self.source, ())

    def tree(self):
        return {
            path.relative_to(self.source).as_posix():
                (path.read_bytes(), path.stat().st_mode)
            for path in self.source.rglob("*") if path.is_file()
        }

    def test_maps_only_runtime_skills_preserving_source_and_resources(self):
        before = self.tree()
        result = cline_skill_files(self.source, self.sources)
        expected = {
            SKILL_PREFIX + ENTRY_DIRECTORIES[name.split("/", 2)[1]]
            + "/" + name.split("/", 2)[2]
            for name in self.sources
            if name.startswith("skills/") and name != INSTALL_ONLY
        }
        self.assertEqual(set(result), expected)
        self.assertNotIn(SKILL_PREFIX + "bmad-solo/scripts/validate-solo-package.py", result)
        self.assertIn(INSTALL_ONLY, self.sources)
        for name, value in self.sources.items():
            if not name.startswith("skills/") or name == INSTALL_ONLY:
                continue
            _, directory, resource = name.split("/", 2)
            adapted = result[SKILL_PREFIX + ENTRY_DIRECTORIES[directory] + "/" + resource]
            self.assertEqual(adapted.mode, value.mode, name)
            if not name.endswith(".md"):
                self.assertEqual(adapted, value, name)
        self.assertEqual(self.tree(), before)

    def test_names_match_host_directories(self):
        result = cline_skill_files(self.source, self.sources)
        for directory in ENTRY_DIRECTORIES.values():
            value = result[SKILL_PREFIX + directory + "/SKILL.md"]
            self.assertIn(("name: " + directory + "\n").encode(), value.content)
        self.assertFalse(any(name.startswith(SKILL_PREFIX + "bmad/") for name in result))

    def test_all_adapted_markdown_links_remain_inside_distributed_skills(self):
        result = cline_skill_files(self.source, self.sources)
        references = 0
        for name, value in result.items():
            if not name.endswith(".md"):
                continue
            text = value.content.decode("utf-8")
            self.assertNotIn("](" + "../bmad/", text, name)
            for destination in re.findall(r"\[[^\]\n]*\]\(([^)\n]+)\)", text):
                if urlsplit(destination).scheme in {"http", "https"}:
                    continue
                physical = unquote(destination.split("#", 1)[0])
                located = re.fullmatch(r"(.+\.[A-Za-z0-9_-]+):(\d+)", physical)
                if located:
                    physical, line = located.groups()
                else:
                    line = None
                if not physical:
                    continue
                target = Path(os.path.abspath(self.root / PurePosixPath(name).parent / physical))
                self.assertTrue(target.is_relative_to(self.root / SKILL_PREFIX), destination)
                key = target.relative_to(self.root).as_posix()
                self.assertIn(key, result, name + " -> " + destination)
                if line is not None:
                    self.assertGreaterEqual(int(line), 1)
                    self.assertLessEqual(int(line), len(result[key].content.decode().splitlines()))
                references += 1
        self.assertGreater(references, 0)

    def test_rewrites_cross_skill_links_preserving_fragments_and_line_locators(self):
        relative = "skills/ana-solo/SKILL.md"
        original = self.sources[relative]
        self.sources[relative] = Snapshot(
            original.content + b"\n[A](../bmad/SKILL.md:22)\n[B](../bmad/SKILL.md#routing)\n",
            original.mode,
        )
        result = cline_skill_files(self.source, self.sources)
        value = result[SKILL_PREFIX + "ana-solo/SKILL.md"]
        self.assertIn(b"[A](../bmad-solo/SKILL.md:22)", value.content)
        self.assertIn(b"[B](../bmad-solo/SKILL.md#routing)", value.content)
        self.assertIn(b"../bmad/SKILL.md:22", self.sources[relative].content)

    def test_consumes_frozen_snapshot_without_reading_changed_source(self):
        expected = cline_skill_files(self.source, self.sources)
        (self.source / "skills/bmad/SKILL.md").unlink()
        actual = cline_skill_files(self.source, self.sources)
        self.assertEqual(actual, expected)

    def test_legacy_or_missing_release_does_not_gain_native_skill_support(self):
        for declaration in (None, b"v4.2\n"):
            sources = dict(self.sources)
            if declaration is None:
                del sources["VERSION"]
            else:
                sources["VERSION"] = Snapshot(declaration, 0o644)
            with self.subTest(declaration=declaration), self.assertRaises(AssetError):
                cline_skill_files(self.source, sources)

    def test_incomplete_skills_are_rejected(self):
        sources = dict(self.sources)
        del sources["skills/bmad/SKILL.md"]
        with self.assertRaisesRegex(AssetError, "技能完整性预检失败"):
            cline_skill_files(self.source, sources)

    def test_extra_skill_directory_is_not_silently_activated(self):
        sources = dict(self.sources)
        sources["skills/unknown/data.txt"] = Snapshot(b"extra skill resource\n", 0o600)
        with self.assertRaisesRegex(AssetError, "未支持的技能目录"):
            cline_skill_files(self.source, sources)

    def test_host_description_limit_is_enforced(self):
        sources = dict(self.sources)
        relative = "skills/bmad/SKILL.md"
        value = sources[relative]
        sources[relative] = Snapshot(
            b"---\nname: bmad-solo\ndescription: " + b"a" * 1025
            + b"\n---\n" + value.content.split(b"---", 2)[2],
            value.mode,
        )
        with self.assertRaisesRegex(AssetError, "1024"):
            cline_skill_files(self.source, sources)

    def test_invalid_snapshot_or_source_paths_are_rejected(self):
        variants = (
            None,
            {**self.sources, "../outside": Snapshot(b"outside", 0o600)},
            {**self.sources, "skills/bmad/missing": Snapshot(None, None)},
        )
        for sources in variants:
            with self.subTest(sources_type=type(sources).__name__), self.assertRaises(AssetError):
                cline_skill_files(self.source, sources)


if __name__ == "__main__":
    unittest.main()
