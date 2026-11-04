"""Cline 技能受管分发与宿主保全回归；仅使用项目内隔离夹具。

验证真实部署入口、所有权、来源记录及拒绝路径，不启动 Cline/Roo，
不证明技能自动调用、原生 Plan/Act 绑定或程序权限隔离。
"""
import json
from pathlib import Path
import subprocess
import sys
import unittest

import test_gitops_dry_run as fixtures

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from asset_safety import AssetError, Snapshot
from deploy_managed import deploy

MIRROR = ".gemini/config/plugins/bmad-suite"
CLINE_ENTRY = ".cline/skills/bmad-solo/SKILL.md"
MODE = "personal profile/settings/custom_modes.yaml"


class ClineDistribution(unittest.TestCase):
    setUp = fixtures.GitOpsDryRun.setUp
    run_command = fixtures.GitOpsDryRun.run_command
    git = fixtures.GitOpsDryRun.git
    tree = fixtures.GitOpsDryRun.tree

    def cli(self, *arguments):
        return self.run_command([
            sys.executable, "-B", "scripts/deploy-managed-cli.py",
            "--root", str(self.target), *arguments,
        ])

    def install(self, *arguments):
        result = self.cli(
            "--source", str(self.repo / "bmad-suite-v4"),
            "--repository", str(self.repo), *arguments,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def ownership(self):
        return json.loads((self.target / ".bmad-solo-deployment/ownership.json").read_bytes())

    def seed_mode(self):
        path = self.target / MODE
        path.parent.mkdir(parents=True)
        path.write_bytes(b"theme: dark\ncustomModes: [{slug: personal, name: Personal}]\n")
        return path

    def test_cli_addition_preserves_existing_roo_modes_and_gemini_assets(self):
        mode = self.seed_mode()
        self.install("--mode-target", MODE)
        before = self.ownership()
        protected = {name: (self.target / name).read_bytes() for name in before["files"]
                     if name != MIRROR + "/.manifest.json"}
        mode_before = mode.read_bytes()
        self.install("--cline-skills")
        after = self.ownership()
        self.assertTrue(set(before["files"]).issubset(after["files"]))
        self.assertEqual(after["modes"], before["modes"])
        self.assertEqual(mode.read_bytes(), mode_before)
        for name, content in protected.items():
            self.assertEqual((self.target / name).read_bytes(), content, name)
        self.assertTrue((self.target / CLINE_ENTRY).is_file())
        self.assertIn(b"name: bmad-solo\n", (self.target / CLINE_ENTRY).read_bytes())
        self.assertFalse((self.target / ".clinerules").exists())

    def test_selected_skills_persist_through_default_update_and_are_idempotent(self):
        self.install("--cline-skills", "--mode-target", MODE)
        before = self.tree(self.target)
        self.install()
        self.assertEqual(self.tree(self.target), before)
        entry = self.repo / "bmad-suite-v4/skills/bmad/SKILL.md"
        entry.write_bytes(entry.read_bytes() + b"\n<!-- approved fixture update -->\n")
        self.install()
        self.assertIn(b"approved fixture update", (self.target / CLINE_ENTRY).read_bytes())
        self.assertIn(MODE, self.ownership()["modes"])

    def test_shell_flag_reaches_cli_and_status_checks_all_managed_assets(self):
        result = self.run_command(["bash", "bs.sh", "--cline-skills"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.target / CLINE_ENTRY).is_file())
        status = self.run_command(["bash", "bs.sh", "--status"])
        self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
        self.assertIn(CLINE_ENTRY, status.stdout)
        provenance = json.loads((self.target / MIRROR / ".manifest.json").read_bytes())
        owned = self.ownership()["files"]
        self.assertIn(CLINE_ENTRY, provenance["managed_files"])
        self.assertEqual(provenance["managed_files"][CLINE_ENTRY], owned[CLINE_ENTRY])

    def test_shell_dry_run_has_no_source_git_or_target_side_effects(self):
        before_repo = self.tree(self.repo)
        before_target = self.tree(self.target)
        result = self.run_command(["bash", "bs.sh", "--dry-run", "--cline-skills"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.tree(self.repo), before_repo)
        self.assertEqual(self.tree(self.target), before_target)
        self.assertIn(CLINE_ENTRY, result.stdout)

    def test_unmanaged_cline_collision_blocks_before_any_target_write(self):
        path = self.target / CLINE_ENTRY
        path.parent.mkdir(parents=True)
        path.write_bytes(b"personal skill, not owned\n")
        before = self.tree(self.target)
        result = self.cli("--source", str(self.repo / "bmad-suite-v4"), "--cline-skills")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.tree(self.target), before)
        self.assertIn("首次同路径接管", result.stderr)

    def test_modified_owned_cline_skill_blocks_entire_default_update(self):
        self.install("--cline-skills")
        path = self.target / CLINE_ENTRY
        path.write_bytes(path.read_bytes() + b"\nuser edit\n")
        before = self.tree(self.target)
        result = self.cli("--source", str(self.repo / "bmad-suite-v4"))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.tree(self.target), before)
        self.assertIn("受管文件已被修改", result.stderr)

    def test_legacy_source_cannot_silently_retire_installed_cline_skills(self):
        self.install("--cline-skills")
        (self.repo / "bmad-suite-v4/VERSION").unlink()
        before = self.tree(self.target)
        result = self.cli("--source", str(self.repo / "bmad-suite-v4"))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.tree(self.target), before)
        self.assertIn("v4.3", result.stderr)

    def test_full_uninstall_preserves_personal_skill_and_mode_fields(self):
        mode = self.seed_mode()
        self.install("--cline-skills", "--mode-target", MODE)
        personal = self.target / ".cline/skills/personal/SKILL.md"
        personal.parent.mkdir()
        personal.write_bytes(b"personal skill\n")
        result = self.cli("--uninstall")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.target / CLINE_ENTRY).exists())
        self.assertEqual(personal.read_bytes(), b"personal skill\n")
        self.assertIn(b"theme: dark", mode.read_bytes())
        self.assertIn(b"personal", mode.read_bytes())
        self.assertEqual(self.ownership()["files"], {})
        self.assertEqual(self.ownership()["modes"], {})

    def test_uninstall_with_addition_flag_is_rejected_without_writes(self):
        self.install("--cline-skills")
        before = self.tree(self.target)
        for command in (["bash", "bs.sh", "--uninstall", "--cline-skills"],
                        [sys.executable, "-B", "scripts/deploy-managed-cli.py", "--root",
                         str(self.target), "--uninstall", "--cline-skills"]):
            with self.subTest(command=command):
                result = self.run_command(command)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.tree(self.target), before)

    def test_coordinator_rejects_implicit_cline_retirement_including_dry_run(self):
        self.install("--cline-skills")
        state = self.target / ".bmad-solo-deployment"
        before = self.tree(self.target)
        for dry_run in (True, False):
            with self.subTest(dry_run=dry_run), self.assertRaisesRegex(AssetError, "隐式退役宿主"):
                deploy(self.target, state, {}, {}, dry_run=dry_run)
            self.assertEqual(self.tree(self.target), before)

    def test_coordinator_rejects_omitted_roo_target_including_dry_run(self):
        self.install("--cline-skills", "--mode-target", MODE)
        state = self.target / ".bmad-solo-deployment"
        desired = {name: Snapshot((self.target / name).read_bytes(), record["mode"])
                   for name, record in self.ownership()["files"].items()}
        before = self.tree(self.target)
        for dry_run in (True, False):
            with self.subTest(dry_run=dry_run), self.assertRaisesRegex(AssetError, "遗漏已有受管 Roo"):
                deploy(self.target, state, desired, {}, dry_run=dry_run)
            self.assertEqual(self.tree(self.target), before)


if __name__ == "__main__":
    unittest.main()
