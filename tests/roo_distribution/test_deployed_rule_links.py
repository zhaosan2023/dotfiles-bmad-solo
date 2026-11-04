"""独立规则副本的可定位链接回归；不启动真实宿主或模型任务。

夹具位于项目内，只验证来源映射、字节溯源和缺失引用的失败关闭。
"""
import json
from pathlib import Path
import posixpath
import re
import unittest

import test_asset_safety_source as fixtures
import test_asset_safety_cli as cli_fixtures
from asset_safety import AssetError, Snapshot
from deployment_source import collect_source, standalone_rule, verify_source


ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ".gemini/config/plugins/bmad-suite/"
RULE = ".gemini/config/rules/bmad-core.md"


class StandaloneRuleLinks(unittest.TestCase):
    setUp = fixtures.SourceSafety.setUp

    def add_linked_rule(self):
        relative = "skills/bmad/references/procedures/example.md"
        path = self.source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"# Isolated procedure\n")
        content = (
            b"# Rule\n\n"
            b"[Procedure](../skills/bmad/references/procedures/example.md)\n"
            b"Literal ../skills/ is not a link.\n"
        )
        (self.source / "rules/bmad-core.md").write_bytes(content)
        return relative, content

    def test_shared_rule_links_resolve_to_same_batch_plugin_assets(self):
        relative, original = self.add_linked_rule()
        before = (self.source / "rules/bmad-core.md").read_bytes()
        files, _, sources = collect_source(self.source, ())
        copied = files[RULE]
        self.assertIn(b"](../plugins/bmad-suite/" + relative.encode() + b")", copied.content)
        self.assertIn(b"Literal ../skills/ is not a link.", copied.content)
        self.assertEqual(files[PLUGIN + "rules/bmad-core.md"].content, original)
        self.assertEqual(sources["rules/bmad-core.md"].content, original)
        self.assertEqual(copied.mode, sources["rules/bmad-core.md"].mode)
        destination = posixpath.normpath(posixpath.join(
            posixpath.dirname(RULE), "../plugins/bmad-suite/" + relative,
        ))
        self.assertIn(destination, files)
        verify_source(self.source, sources)
        self.assertEqual((self.source / "rules/bmad-core.md").read_bytes(), before)
        self.assertFalse((self.root / ".gemini").exists())

    def test_missing_linked_skill_blocks_source_collection_without_writes(self):
        relative, original = self.add_linked_rule()
        (self.source / relative).unlink()
        with self.assertRaisesRegex(AssetError, "技能资产缺失"):
            collect_source(self.source, ())
        self.assertEqual((self.source / "rules/bmad-core.md").read_bytes(), original)
        self.assertFalse((self.root / ".gemini").exists())

    def test_missing_link_with_line_or_fragment_cannot_bypass_check(self):
        for suffix in (":12", "#section", ":12#section"):
            with self.subTest(suffix=suffix):
                value = Snapshot(("[Missing](../skills/missing.md" + suffix + ")\n").encode(), 0o600)
                with self.assertRaisesRegex(AssetError, "技能资产缺失"):
                    standalone_rule(value, {})

    def test_line_and_fragment_locators_are_preserved(self):
        linked = Snapshot(b"# Existing\n", 0o600)
        for suffix in (":12", "#section", ":12#section"):
            with self.subTest(suffix=suffix):
                value = Snapshot(("[Existing](../skills/existing.md" + suffix + ")\n").encode(), 0o640)
                rendered = standalone_rule(value, {"skills/existing.md": linked})
                self.assertEqual(rendered.content, (
                    "[Existing](../plugins/bmad-suite/skills/existing.md" + suffix + ")\n"
                ).encode())
                self.assertEqual(rendered.mode, 0o640)

    def test_traversal_and_invalid_encoding_fail_closed(self):
        for content in (
            b"[Escape](../skills/../../outside.md)\n",
            b"[Invalid](../skills/\xff.md)\n",
        ):
            with self.subTest(content=content), self.assertRaises(AssetError):
                standalone_rule(Snapshot(content, 0o600), {})

    def test_unrelated_links_and_rules_without_skill_links_are_unchanged(self):
        value = Snapshot(
            b"[External](https://example.invalid/skills/)\n"
            b"[Project](docs/project-context.md:1)\n"
            b"[Other](../rules/other.md)\n"
            b"`../skills/example.md`\n",
            0o600,
        )
        self.assertEqual(standalone_rule(value, {}), value)

    def test_current_suite_shared_rule_links_resolve_after_mapping(self):
        files, _, sources = collect_source(ROOT / "bmad-suite-v4", ())
        links = re.findall(rb"\]\((\.\./plugins/bmad-suite/[^)\s]+)\)", files[RULE].content)
        self.assertTrue(links, "当前独立规则必须实际导航到套件技能")
        for destination in links:
            target = posixpath.normpath(posixpath.join(
                posixpath.dirname(RULE), destination.decode("utf-8"),
            ))
            with self.subTest(target=target):
                self.assertIn(target, files)
                self.assertTrue(target.startswith(PLUGIN))
        self.assertNotIn(b"](../skills/", files[RULE].content)
        self.assertEqual(files[PLUGIN + "rules/bmad-core.md"], sources["rules/bmad-core.md"])
        verify_source(ROOT / "bmad-suite-v4", sources)


class DeployedRuleLinkDistribution(unittest.TestCase):
    setUp = cli_fixtures.CliSafety.setUp
    run_cli = cli_fixtures.CliSafety.run_cli
    install = cli_fixtures.CliSafety.install
    tree = cli_fixtures.CliSafety.tree

    def test_transformed_rule_is_installed_and_traced_without_mutating_source(self):
        relative = "skills/bmad/references/procedures/example.md"
        linked = self.source / relative
        linked.parent.mkdir(parents=True)
        linked.write_bytes(b"# Isolated procedure\n")
        original = b"[Procedure](../skills/bmad/references/procedures/example.md)\n"
        source_rule = self.source / "rules/bmad-core.md"
        source_rule.write_bytes(original)
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        installed = self.target / RULE
        destination = "../plugins/bmad-suite/" + relative
        self.assertEqual(installed.read_bytes(), (
            "[Procedure](" + destination + ")\n"
        ).encode())
        resolved = (installed.parent / destination).resolve(strict=True)
        self.assertTrue(resolved.is_relative_to(self.target.resolve()))
        self.assertEqual(resolved.read_bytes(), linked.read_bytes())
        self.assertEqual((self.target / PLUGIN / "rules/bmad-core.md").read_bytes(), original)
        self.assertEqual(source_rule.read_bytes(), original)
        provenance = json.loads((self.target / PLUGIN / ".manifest.json").read_bytes())
        ownership = json.loads((self.target / ".bmad-solo-deployment/ownership.json").read_bytes())
        self.assertEqual(provenance["managed_files"][RULE], ownership["files"][RULE])
        self.assertEqual(provenance["source_files"]["rules/bmad-core.md"],
                         provenance["managed_files"][PLUGIN + "rules/bmad-core.md"])
        self.assertNotEqual(provenance["source_files"]["rules/bmad-core.md"],
                            provenance["managed_files"][RULE])
        before = self.tree()
        repeated = self.install()
        self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
        self.assertEqual(self.tree(), before)
        installed.write_bytes(installed.read_bytes() + b"personal edit\n")
        protected = self.tree()
        rejected = self.install()
        self.assertNotEqual(rejected.returncode, 0)
        self.assertEqual(self.tree(), protected)
        self.assertEqual(source_rule.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
