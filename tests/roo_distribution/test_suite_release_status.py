"""发布快照解析、直接部署预检和只读诊断；仅项目内隔离夹具。"""
from pathlib import Path
import shutil
import unittest

import test_asset_safety_source as source_fixtures
import test_suite_status as status_fixtures

from asset_safety import AssetError, Snapshot
from deployment_identity import PLUGIN_PREFIX, manifest_release
from deployment_source import collect_source
from managed_files import ownership_record
from release_version import parse_release


class ReleaseSnapshotContracts(unittest.TestCase):
    def test_parser_accepts_two_segments_and_rejects_corrupt_bytes(self):
        for content in (b"v4.0\n", b"v4.3\n", b"v4.10\n"):
            with self.subTest(content=content):
                self.assertEqual(parse_release(content), content.decode("ascii").strip())
        for content in (None, "v4.3\n", b"", b"v4.3", b"v4.3\n\n",
                        b"v4.3\r\n", b"v4.3.0\n", b"v4.03\n", b"\xff\n"):
            with self.subTest(content=content), self.assertRaises(AssetError):
                parse_release(content)

    def test_snapshot_presence_must_match_all_three_inputs(self):
        target = PLUGIN_PREFIX + "VERSION"
        value = Snapshot(b"v4.3\n", 0o644)
        record = ownership_record(value)
        for source_present in (False, True):
            for managed_present in (False, True):
                for observed_present in (False, True):
                    provenance = {
                        "source_files": {"VERSION": record} if source_present else {},
                        "managed_files": {target: record} if managed_present else {},
                    }
                    observed = {target: value} if observed_present else {}
                    with self.subTest(source=source_present, managed=managed_present,
                                      observed=observed_present):
                        if source_present == managed_present == observed_present:
                            self.assertEqual(manifest_release(provenance, observed),
                                             "v4.3" if source_present else None)
                        else:
                            with self.assertRaises(AssetError):
                                manifest_release(provenance, observed)

    def test_matching_records_cannot_hide_invalid_version_bytes(self):
        target = PLUGIN_PREFIX + "VERSION"
        value = Snapshot(b"v4.3.0\n", 0o644)
        record = ownership_record(value)
        provenance = {"source_files": {"VERSION": record},
                      "managed_files": {target: record}}
        with self.assertRaises(AssetError):
            manifest_release(provenance, {target: value})


class ReleaseSourcePreflight(unittest.TestCase):
    setUp = source_fixtures.SourceSafety.setUp

    def test_optional_legacy_declaration_remains_supported(self):
        _, _, sources = collect_source(self.source, self.targets)
        self.assertNotIn("VERSION", sources)
        # 声明当前发布时补齐真实双技能资产，不用空夹具绕过安装门禁。
        shutil.copytree(
            Path(__file__).resolve().parents[2] / "bmad-suite-v4/skills",
            self.source / "skills",
        )
        (self.source / "VERSION").write_bytes(b"v4.3\n")
        _, _, sources = collect_source(self.source, self.targets)
        self.assertEqual(sources["VERSION"].content, b"v4.3\n")
        self.assertFalse((self.root / "ide").exists())

    def test_current_release_declaration_requires_complete_skills(self):
        (self.source / "VERSION").write_bytes(b"v4.3\n")
        with self.assertRaisesRegex(AssetError, "技能完整性预检失败"):
            collect_source(self.source, self.targets)
        self.assertFalse((self.root / "ide").exists())

    def test_corrupt_declaration_is_rejected_by_source_collector(self):
        version = self.source / "VERSION"
        for content in (b"", b"v4.3", b"v4.3.0\n", b"\xff\n"):
            version.write_bytes(content)
            with self.subTest(content=content), self.assertRaises(AssetError):
                collect_source(self.source, self.targets)
            self.assertEqual(version.read_bytes(), content)
            self.assertFalse((self.root / "ide").exists())


class ReleaseStatus(unittest.TestCase):
    setUp = status_fixtures.SuiteStatus.setUp
    run_command = status_fixtures.SuiteStatus.run_command
    git = status_fixtures.SuiteStatus.git
    tree = status_fixtures.SuiteStatus.tree
    deploy = status_fixtures.SuiteStatus.deploy
    status = status_fixtures.SuiteStatus.status
    revise_provenance_fixture = status_fixtures.SuiteStatus.revise_provenance_fixture
    RELATIVE = status_fixtures.SuiteStatus.RELATIVE

    def test_status_uses_deployed_release_not_changed_or_missing_source(self):
        source = self.repo / "bmad-suite-v4"
        declared = (source / "VERSION").read_text(encoding="ascii").strip()
        self.deploy()
        (source / "VERSION").write_bytes(b"invalid current worktree version\n")
        source.rename(self.repo / "moved-suite")
        before_repo = self.tree(self.repo)
        result = self.status()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"记录的发布版本：{declared}", result.stdout)
        self.assertIn("未核验来源仓库当前状态", result.stdout)
        machine = self.status(machine=True)
        self.assertEqual(machine.returncode, 0, machine.stderr)
        self.assertEqual(machine.stdout, "v4\n")
        self.assertEqual(self.tree(self.repo), before_repo)

    def test_legacy_deployment_reports_unknown_minor_without_writes(self):
        (self.repo / "bmad-suite-v4/VERSION").unlink()
        self.deploy()
        result = self.status()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("记录的发布版本：未知", result.stdout)
        self.assertNotIn("记录的发布版本：v4.3", result.stdout)
        machine = self.status(machine=True)
        self.assertEqual(machine.returncode, 0, machine.stderr)
        self.assertEqual(machine.stdout, "v4\n")

    def test_partial_version_record_is_not_treated_as_legacy(self):
        self.deploy()
        self.revise_provenance_fixture(lambda data: data["source_files"].pop("VERSION"))
        result = self.status(machine=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("存在性不一致", result.stderr)

    def test_version_source_digest_mismatch_is_rejected(self):
        self.deploy()
        self.revise_provenance_fixture(lambda data: data["source_files"]["VERSION"].update(
            sha256="0" * 64,
        ))
        result = self.status(machine=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("发布版本资产与来源摘要不一致", result.stderr)

    def test_direct_deployment_cannot_bypass_corrupt_version_preflight(self):
        version = self.repo / "bmad-suite-v4/VERSION"
        for content in (b"v4.3.0\n", b"v4.3", b""):
            version.write_bytes(content)
            before_repo, before_target = self.tree(self.repo), self.tree(self.target)
            result = self.run_command([
                "python3", "-B", "scripts/deploy-managed-cli.py",
                "--root", str(self.target), "--repository", str(self.repo),
                "--source", str(self.repo / "bmad-suite-v4"),
            ])
            with self.subTest(content=content):
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(self.tree(self.repo), before_repo)
                self.assertEqual(self.tree(self.target), before_target)
                self.assertNotIn("受管文件分发完成", result.stdout)


if __name__ == "__main__":
    unittest.main()
