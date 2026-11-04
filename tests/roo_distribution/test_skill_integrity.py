"""双技能入口完整性负控；仅复制项目内套件，不联网、不启动宿主。

静态检查和项目内子进程不证明模型调用技能或上游同步。
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from asset_safety import AssetError, Snapshot
from deployment_source import collect_source, verify_source
import skill_integrity as install_integrity

SUITE = ROOT / "bmad-suite-v4"
VALIDATOR = SUITE / "skills/bmad/scripts/validate-solo-package.py"
spec = importlib.util.spec_from_file_location("solo_integrity", VALIDATOR)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class SkillIntegrity(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(
            prefix="sandbox-skill-integrity-", dir=Path(__file__).parent,
        )
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.suite = self.root / "suite"
        shutil.copytree(SUITE, self.suite)

    def document(self, relative):
        return self.suite / "skills" / relative

    def rejected(self, message):
        with self.assertRaises((validator.PackageError, OSError)) as caught:
            validator.validate_suite(self.suite)
        self.assertIn(message, str(caught.exception))

    def test_current_suite_has_two_entries_and_nonempty_local_closure(self):
        report = validator.validate_suite(self.suite)
        self.assertEqual(report["entries"], 2)
        self.assertGreater(report["documents"], 0)
        self.assertGreater(report["local_references"], 0)
        self.assertGreater(report["mapped_procedures"], 0)
        self.assertIs(report["runtime_verified"], False)
        self.assertIs(report["upstream_sync_verified"], False)

    def test_required_assets_cannot_be_deleted_or_emptied(self):
        required = set(validator.ENTRY_NAMES) | set(validator.REQUIRED_REFERENCES) | {
            f"bmad/references/procedures/{name}.md"
            for name in validator.REQUIRED_PROCEDURES
        }
        for relative in sorted(required):
            path = self.document(relative)
            original = path.read_bytes()
            with self.subTest(relative=relative, fault="missing"):
                path.unlink()
                self.rejected("缺少必需技能资产")
                path.write_bytes(original)
            with self.subTest(relative=relative, fault="empty"):
                path.write_bytes(b"\n")
                self.rejected("必需技能资产为空")
                path.write_bytes(original)

    def test_both_entries_reject_invalid_or_duplicate_frontmatter(self):
        for relative, name in validator.ENTRY_NAMES.items():
            path = self.document(relative)
            original = path.read_bytes()
            cases = (
                ("# No header\n", "缺少 frontmatter"),
                (f"---\nname: {name}\n", "结束符"),
                ("---\n[]\n---\n# Body\n", "必须为映射"),
                ("---\nname: wrong\ndescription: entry\n---\n# Body\n", "身份不匹配"),
                (f"---\nname: {name}\nname: {name}\ndescription: entry\n---\n# Body\n", "重复键"),
                (f"---\nname: {name}\ndescription: ''\n---\n# Body\n", "description"),
                (f"---\nname: {name}\ndescription: entry\n---\n", "缺少正文"),
            )
            for content, diagnostic in cases:
                with self.subTest(relative=relative, diagnostic=diagnostic):
                    path.write_text(content, encoding="utf-8")
                    self.rejected(diagnostic)
            path.write_bytes(original)

    def test_missing_link_fails_even_when_all_required_assets_exist(self):
        path = self.document("ana-solo/references/decision-matrix.md")
        original = path.read_text()
        for destination in ("missing.md:1", "missing.md:1#section",
                            "missing%2Emd:1"):
            with self.subTest(destination=destination):
                path.write_text(original + f"\n[缺失]({destination})\n")
                self.rejected("技能引用资产缺失")

    def test_references_resolve_from_document_and_preserve_line_and_fragment(self):
        path = self.document("ana-solo/references/decision-matrix.md")
        path.write_text(path.read_text() + "\n[入口](../SKILL.md:10#section)\n"
                        "[同目录](convergence-locks.md:1#section)\n")
        self.assertEqual(validator.validate_suite(self.suite)["entries"], 2)
        path.write_text(path.read_text() + "\n[坏行](../SKILL.md:999999)\n")
        self.rejected("行定位无效")

    def test_external_project_slot_does_not_become_a_suite_reference(self):
        path = self.document("ana-solo/references/decision-matrix.md")
        path.write_text(path.read_text() + "\n[目标](../../../AGENTS.md)\n")
        self.rejected("越出技能包")

    def test_encoded_traversal_absolute_and_file_scheme_links_fail(self):
        path = self.document("ana-solo/references/decision-matrix.md")
        original = path.read_text()
        for destination in ("%2e%2e/%2e%2e/%2e%2e/secret.md", "/tmp/secret.md",
                            "file:///tmp/secret.md", "//host/secret.md",
                            "file:///tmp/secret.md:1", "ssh://host/secret.md:1",
                            "file:convergence-locks.md:1"):
            with self.subTest(destination=destination):
                path.write_text(original + f"\n[坏引用]({destination})\n")
                with self.assertRaises(validator.PackageError):
                    validator.validate_suite(self.suite)

    def test_upstream_paths_and_renderer_dependencies_fail(self):
        path = self.document("ana-solo/references/decision-matrix.md")
        original = path.read_text()
        for dependency in ("_bmad-solo-source/legacy-skills/entry/SKILL.md",
                           "bmad-method-source/skills/entry/SKILL.md",
                           "_bmad/scripts/run.py", "_bmad/core/workflow.md",
                           "bmm/config.yaml", "render_skill.py",
                           "resolve_customization.py", "customize.toml"):
            with self.subTest(dependency=dependency):
                path.write_text(original + "\n读取 " + dependency + "\n")
                self.rejected("旧上游依赖")

    def test_capability_map_zero_matches_or_planned_missing_asset_fails(self):
        path = self.document("bmad/references/capability-map.md")
        original = path.read_text()
        path.write_text("# 空映射\n")
        self.rejected("零命中")
        path.write_text(original + "\n## Planned\nprocedures/not-created.md\n")
        self.rejected("能力映射流程缺失")

    def test_symlinks_hardlinks_and_special_files_fail_without_reading_targets(self):
        path = self.document("untrusted")
        outside = self.root / "protected"
        outside.write_bytes(b"keep")
        path.symlink_to(outside)
        self.rejected("链接或非普通资产")
        path.unlink()
        os.link(self.document("bmad/SKILL.md"), path)
        self.rejected("链接或非普通资产")
        path.unlink()
        os.mkfifo(path)
        self.rejected("链接或非普通资产")
        path.unlink()
        self.assertEqual(outside.read_bytes(), b"keep")

    def test_symlink_root_and_parent_fail(self):
        link = self.root / "linked-suite"
        link.symlink_to(self.suite, target_is_directory=True)
        with self.assertRaisesRegex(validator.PackageError, "符号链接"):
            validator.validate_suite(link)
        parent = self.root / "linked-parent"
        parent.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(validator.PackageError, "符号链接"):
            validator.validate_suite(parent / "suite")

    def test_invalid_utf8_fails(self):
        self.document("ana-solo/references/decision-matrix.md").write_bytes(b"\xff")
        with self.assertRaises(UnicodeError):
            validator.validate_suite(self.suite)

    def test_cli_uses_own_suite_and_returns_bounded_static_report_without_writes(self):
        before = {path.relative_to(self.suite).as_posix(): path.read_bytes()
                  for path in self.suite.rglob("*") if path.is_file()}
        entry = self.suite / "skills/bmad/scripts/validate-solo-package.py"
        result = subprocess.run(
            [sys.executable, "-B", str(entry)], cwd=self.root,
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=10,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout.splitlines()[0])
        self.assertEqual(report["entries"], 2)
        self.assertIn("未验证宿主加载", result.stdout)
        self.assertEqual(before, {path.relative_to(self.suite).as_posix(): path.read_bytes()
                                 for path in self.suite.rglob("*") if path.is_file()})
        self.document("bmad/SKILL.md").unlink()
        failed = subprocess.run(
            [sys.executable, "-B", str(entry), "--suite", str(self.suite)],
            cwd=self.root, stdin=subprocess.DEVNULL, capture_output=True,
            text=True, timeout=10,
        )
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("校验失败", failed.stderr)
        self.assertNotIn("静态技能完整性通过", failed.stdout)


class SkillInstallation(unittest.TestCase):
    """来源采集与直接部署共享门禁；目标始终为项目内隔离目录。"""

    def setUp(self):
        SkillIntegrity.setUp(self)
        selected = self.root / "bmad-suite-v4"
        self.suite.rename(selected)
        self.suite = selected
        self.target = self.root / "target"
        self.target.mkdir()

    document = SkillIntegrity.document

    def tree(self, root):
        return {path.relative_to(root).as_posix():
                ("directory" if path.is_dir() else path.read_bytes(), path.stat().st_mode)
                for path in root.rglob("*")}

    def run_cli(self, *options):
        return subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts/deploy-managed-cli.py"),
             "--root", str(self.target), "--source", str(self.suite), *options],
            cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True,
            text=True, timeout=10,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

    def test_snapshot_validation_matches_disk_report_without_reading_candidate_files(self):
        assets = validator.read_assets(self.suite / "skills")
        expected = validator.validate_suite(self.suite)
        with patch.object(Path, "read_bytes", side_effect=AssertionError("disk read forbidden")), \
                patch.object(validator, "read_assets", side_effect=AssertionError("walk forbidden")):
            self.assertEqual(validator.validate_assets(self.suite / "skills", assets), expected)

    def test_snapshot_validation_rejects_empty_invalid_paths_and_nonbyte_assets(self):
        assets = validator.read_assets(self.suite / "skills")
        for mapping in ({}, None, {**assets, "../escape.md": b"text"},
                        {**assets, "/absolute.md": b"text"},
                        {**assets, "bad\\path.md": b"text"},
                        {**assets, "bad.md": "not bytes"}):
            with self.subTest(mapping_type=type(mapping).__name__), \
                    self.assertRaises(validator.PackageError):
                validator.validate_assets(self.suite / "skills", mapping)

    def test_collector_validates_same_snapshot_and_preserves_source_and_target(self):
        before_source, before_target = self.tree(self.suite), self.tree(self.target)
        files, modes, sources = collect_source(self.suite, ())
        report = install_integrity.validate_source_skills(self.suite, sources)
        self.assertEqual(report["entries"], 2)
        self.assertIs(report["runtime_verified"], False)
        self.assertEqual(modes, {})
        self.assertIn(".gemini/config/plugins/bmad-suite/skills/bmad/SKILL.md", files)
        verify_source(self.suite, sources)
        self.assertEqual(self.tree(self.suite), before_source)
        self.assertEqual(self.tree(self.target), before_target)

    def test_selected_source_validator_is_not_loaded_or_executed(self):
        candidate = self.document("bmad/scripts/validate-solo-package.py")
        candidate.write_text("raise AssertionError('candidate code must not execute')\n")
        _, _, sources = collect_source(self.suite, ())
        report = install_integrity.validate_source_skills(self.suite, sources)
        self.assertEqual(report["entries"], 2)
        self.assertEqual(candidate.read_text(),
                         "raise AssertionError('candidate code must not execute')\n")
        self.assertEqual(list(self.target.iterdir()), [])

    def test_adapter_consumes_frozen_snapshot_not_changed_candidate_disk(self):
        _, _, sources = collect_source(self.suite, ())
        self.document("bmad/SKILL.md").unlink()
        report = install_integrity.validate_source_skills(self.suite, sources)
        self.assertEqual(report["entries"], 2)
        with self.assertRaises(AssetError):
            verify_source(self.suite, sources)
        with self.assertRaisesRegex(AssetError, "技能完整性预检失败"):
            collect_source(self.suite, ())

    def test_legacy_skip_does_not_claim_integrity_and_future_release_requires_assets(self):
        for declaration in (None, b"v4.0\n", b"v4.2\n"):
            sources = {} if declaration is None else {"VERSION": Snapshot(declaration, 0o644)}
            with self.subTest(declaration=declaration):
                self.assertIsNone(install_integrity.validate_source_skills(self.suite, sources))
        for declaration in (b"v4.3\n", b"v4.4\n", b"v4.10\n"):
            with self.subTest(declaration=declaration), \
                    self.assertRaisesRegex(AssetError, "技能完整性预检失败"):
                install_integrity.validate_source_skills(
                    self.suite, {"VERSION": Snapshot(declaration, 0o644)},
                )

    def test_missing_trusted_validator_blocks_instead_of_using_candidate(self):
        with patch.object(install_integrity, "TRUSTED_VALIDATOR", self.root / "missing.py"), \
                self.assertRaisesRegex(AssetError, "缺少可信技能校验实现"):
            collect_source(self.suite, ())
        self.assertEqual(list(self.target.iterdir()), [])

    def test_direct_deployment_preflight_dry_run_and_install_reject_incomplete_skills(self):
        self.document("bmad/SKILL.md").unlink()
        before_source, before_target = self.tree(self.suite), self.tree(self.target)
        for options in ((), ("--dry-run",), ("--preflight",)):
            with self.subTest(options=options):
                result = self.run_cli(*options)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("技能完整性预检失败", result.stderr)
                self.assertNotIn("受管文件分发完成", result.stdout)
                self.assertEqual(self.tree(self.suite), before_source)
                self.assertEqual(self.tree(self.target), before_target)

    def test_direct_install_distributes_complete_skills_with_source_unchanged(self):
        before = self.tree(self.suite)
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for relative in validator.ENTRY_NAMES:
            installed = self.target / ".gemini/config/plugins/bmad-suite/skills" / relative
            self.assertEqual(installed.read_bytes(), self.document(relative).read_bytes())
        self.assertEqual(self.tree(self.suite), before)
        self.assertIn("未验证 Roo 运行时", result.stdout)


if __name__ == "__main__":
    unittest.main()
