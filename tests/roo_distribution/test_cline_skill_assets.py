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
    ENTRY_DIRECTORIES, INSTALL_ONLY, ROUTER_SOURCE, ROUTER_TARGET,
    SKILL_PREFIX, cline_skill_files,
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

    def test_maps_runtime_skills_and_router_preserving_source_and_resources(self):
        before = self.tree()
        result = cline_skill_files(self.source, self.sources)
        expected = {
            SKILL_PREFIX + ENTRY_DIRECTORIES[name.split("/", 2)[1]]
            + "/" + name.split("/", 2)[2]
            for name in self.sources
            if name.startswith("skills/") and name != INSTALL_ONLY
        }
        self.assertEqual(set(result), expected | {ROUTER_TARGET})
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
            if not name.startswith(SKILL_PREFIX) or not name.endswith(".md"):
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

    def test_global_router_links_resolve_in_deployment_not_source_workspace(self):
        files, _, _ = collect_source(self.source, (), cline_skills=True)
        router = files[ROUTER_TARGET]
        self.assertEqual(router.mode, self.sources[ROUTER_SOURCE].mode)
        text = router.content.decode("utf-8")
        self.assertNotIn("](bmad-suite-v4/", text)
        self.assertIn("](docs/project-context.md:1)", text)
        self.assertIn("](../skills/ana-solo/SKILL.md:10)", text)
        self.assertIn("](../skills/bmad-solo/SKILL.md:21)", text)
        references = 0
        for destination in re.findall(r"\[[^\]\n]*\]\(([^)\n]+)\)", text):
            if destination.startswith("docs/"):
                continue  # 项目私有事实仍从当前工作区读取，不纳入全局分发。
            physical, line = destination.rsplit(":", 1)
            target = Path(os.path.abspath(self.root / PurePosixPath(ROUTER_TARGET).parent / physical))
            self.assertTrue(target.is_relative_to(self.root), destination)
            key = target.relative_to(self.root).as_posix()
            self.assertIn(key, files, destination)
            self.assertGreaterEqual(int(line), 1)
            self.assertLessEqual(int(line), len(files[key].content.decode().splitlines()))
            references += 1
        self.assertEqual(references, 3)
        self.assertEqual(files[".gemini/config/plugins/bmad-suite/" + ROUTER_SOURCE],
                         self.sources[ROUTER_SOURCE])

    def test_missing_router_or_missing_linked_asset_is_rejected(self):
        sources = dict(self.sources)
        del sources[ROUTER_SOURCE]
        with self.assertRaisesRegex(AssetError, "全局路由缺少来源"):
            cline_skill_files(self.source, sources)
        sources = dict(self.sources)
        original = sources[ROUTER_SOURCE]
        sources[ROUTER_SOURCE] = Snapshot(
            original.content + b"\n[missing](bmad-suite-v4/rules/missing.md:1)\n", original.mode,
        )
        with self.assertRaisesRegex(AssetError, "路由引用的套件资产缺失"):
            cline_skill_files(self.source, sources)

    def test_router_rewrites_links_preserving_fragments_and_line_locators(self):
        sources = dict(self.sources)
        original = sources[ROUTER_SOURCE]
        sources[ROUTER_SOURCE] = Snapshot(
            original.content + b"\n[A](bmad-suite-v4/skills/bmad/SKILL.md:22)\n"
            + b"[B](bmad-suite-v4/skills/ana-solo/SKILL.md#routing)\n", original.mode,
        )
        content = cline_skill_files(self.source, sources)[ROUTER_TARGET].content
        self.assertIn(b"[A](../skills/bmad-solo/SKILL.md:22)", content)
        self.assertIn(b"[B](../skills/ana-solo/SKILL.md#routing)", content)
        self.assertEqual(self.sources[ROUTER_SOURCE], original)

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
        (self.source / ROUTER_SOURCE).unlink()
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
