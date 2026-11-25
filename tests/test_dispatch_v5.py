"""隔离全生命周期测试：BMAD-Solo V5.1 受管分发、四态健康检查与精确卸载 (tests/test_dispatch_v5.py)

全部测试均在 tempfile.TemporaryDirectory 模拟的独立 --home-dir 与 --workspace 中执行，
绝不触碰真实用户的 ~/.cline/、~/.local/share/bmad-solo/ 或 ~/.gemini/。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest

from scripts.distill_v5_kernel import compile_kernel


class TestDispatchV5Lifecycle(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).resolve().parent.parent
        self.dispatch_script = self.repo_root / "scripts/dispatch_v5.sh"
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_root = Path(self.tmp.name)
        self.fake_home = self.tmp_root / "home"
        self.fake_home.mkdir()
        self.fake_source = self.tmp_root / "dist_v5"
        self.fake_workspace = self.tmp_root / "biz_repo"
        self.fake_workspace.mkdir()

        # 在隔离源目录编译 V5.1 产物
        ok, msg, _ = compile_kernel(self.fake_source, dry_run=False)
        self.assertTrue(ok, msg)

        # 在隔离假家目录预先放入一个 Gemini V4 文件与一个第三方 Cline 规则，验证全程零触碰
        self.gemini_v4_file = self.fake_home / ".gemini/config/plugins/bmad-suite/v4-keep.md"
        self.gemini_v4_file.parent.mkdir(parents=True)
        self.gemini_v4_file.write_text("# Gemini V4 Production Rule\n", encoding="utf-8")

        self.third_party_rule = self.fake_home / ".cline/rules/my-custom-style.md"
        self.third_party_rule.parent.mkdir(parents=True)
        self.third_party_rule.write_text("# My Personal Coding Style\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _run_dispatch(self, *args: str, home_dir: Path | None = None) -> subprocess.CompletedProcess:
        cmd = [
            "bash",
            str(self.dispatch_script),
            "--home-dir",
            str(home_dir or self.fake_home),
            "--source-dir",
            str(self.fake_source),
            *args,
        ]
        return subprocess.run(
            cmd,
            cwd=str(self.repo_root),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

    def test_preflight_test_mode_discloses_lock_and_does_not_write_rules(self):
        res = self._run_dispatch("--test")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("deploy.lock", res.stdout)
        self.assertIn("[UNKNOWN]", res.stdout)
        # 锁文件位于 .local/share/bmad-solo/v5/deploy.lock，不在 ~/.cline/ 下
        self.assertTrue((self.fake_home / ".local/share/bmad-solo/v5/deploy.lock").exists())
        self.assertFalse((self.fake_home / ".cline/.bmad_dispatch.lock").exists())
        # 不覆写目标规则文件
        self.assertFalse((self.fake_home / ".cline/rules/bmad-v5-router.md").exists())
        self.assertFalse((self.fake_home / ".local/share/bmad-solo/v5/skills/ana-solo.md").exists())

    def test_full_lifecycle_deploy_doctor_toggle_tamper_conflict_uninstall(self):
        # 1. 未安装时 --doctor -> UNINSTALLED (exit 0)
        res = self._run_dispatch("--doctor", "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        report = json.loads(res.stdout)
        self.assertEqual(report["state"], "UNINSTALLED")

        # 2. 受管部署 -> 检查权限 (skills=0444, router=0644) 与 manifest
        res = self._run_dispatch("--deploy")
        self.assertEqual(res.returncode, 0, res.stderr)
        router_file = self.fake_home / ".cline/rules/bmad-v5-router.md"
        ana_file = self.fake_home / ".local/share/bmad-solo/v5/skills/ana-solo.md"
        bmad_file = self.fake_home / ".local/share/bmad-solo/v5/skills/bmad-solo.md"
        manifest_file = self.fake_home / ".local/share/bmad-solo/v5/manifest.json"
        self.assertTrue(router_file.is_file())
        self.assertTrue(ana_file.is_file())
        self.assertTrue(bmad_file.is_file())
        self.assertTrue(manifest_file.is_file())
        self.assertEqual(stat.S_IMODE(router_file.stat().st_mode), 0o644)
        self.assertEqual(stat.S_IMODE(ana_file.stat().st_mode), 0o444)
        self.assertEqual(stat.S_IMODE(bmad_file.stat().st_mode), 0o444)

        # 3. 干净部署后 --doctor -> HEALTHY (exit 0)
        res = self._run_dispatch("--doctor", "--workspace", str(self.fake_workspace), "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        report = json.loads(res.stdout)
        self.assertEqual(report["state"], "HEALTHY")
        self.assertTrue(report["router_enabled"])
        self.assertEqual(report["runtime_load_status"], "[UNKNOWN]")

        # 4. 模拟 Cline UI 切换开关 (头部加 disabled: true) -> DEGRADED (exit 0)，不误报 BROKEN
        original_router = router_file.read_text(encoding="utf-8")
        router_file.write_text("---\ndisabled: true\n---\n" + original_router, encoding="utf-8")
        res = self._run_dispatch("--doctor", "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        report = json.loads(res.stdout)
        self.assertEqual(report["state"], "DEGRADED")
        self.assertFalse(report["router_enabled"])
        self.assertEqual(report["broken_reasons"], [])

        # 恢复开启态
        router_file.write_text(original_router, encoding="utf-8")

        # 5. 模拟工作区历史禁用残留 (类似 aurora2api 的 disabled: true 旧规则) -> DEGRADED (exit 0)
        legacy_disabled = self.fake_workspace / ".clinerules"
        legacy_disabled.write_text("---\ndisabled: true\n---\n# BMAD V4 Charter\n", encoding="utf-8")
        res = self._run_dispatch("--doctor", "--workspace", str(self.fake_workspace), "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        report = json.loads(res.stdout)
        self.assertEqual(report["state"], "DEGRADED")
        self.assertTrue(any(".clinerules" in w for w in report["warnings"]))

        # 6. 模拟工作区启用态 V4 冲突 -> CONFLICT (exit 2)
        legacy_disabled.write_text("# BMAD V4 Active Charter\n", encoding="utf-8")
        res = self._run_dispatch("--doctor", "--workspace", str(self.fake_workspace), "--json")
        self.assertEqual(res.returncode, 2, res.stderr)
        report = json.loads(res.stdout)
        self.assertEqual(report["state"], "CONFLICT")
        self.assertTrue(any(".clinerules" in c for c in report["conflicts"]))
        legacy_disabled.unlink()

        # 7. 模拟 Cline 全局 auto-discovered skills 冲突 -> CONFLICT (exit 2)
        auto_skill = self.fake_home / ".cline/skills/ana-solo/SKILL.md"
        auto_skill.parent.mkdir(parents=True)
        auto_skill.write_text("# Auto skill conflict\n", encoding="utf-8")
        res = self._run_dispatch("--doctor", "--json")
        self.assertEqual(res.returncode, 2, res.stderr)
        report = json.loads(res.stdout)
        self.assertEqual(report["state"], "CONFLICT")
        self.assertTrue(any("auto-skill" in c for c in report["conflicts"]))
        auto_skill.unlink()

        # 8. 模拟正文篡改 -> BROKEN (exit 1)，且无 --force 时 --uninstall 拒绝静默删除
        router_file.write_text(original_router + "\n# Hallucinated line\n", encoding="utf-8")
        res = self._run_dispatch("--doctor", "--json")
        self.assertEqual(res.returncode, 1, res.stderr)
        report = json.loads(res.stdout)
        self.assertEqual(report["state"], "BROKEN")

        res = self._run_dispatch("--uninstall")
        self.assertEqual(res.returncode, 1)
        self.assertTrue(router_file.exists())

        # 9. 使用 --deploy --force 覆盖后验证 --rollback 恢复，再恢复干净并执行 --uninstall
        res = self._run_dispatch("--deploy", "--force")
        self.assertEqual(res.returncode, 0, res.stderr)
        res = self._run_dispatch("--rollback")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("Hallucinated line", router_file.read_text(encoding="utf-8"))

        # 重新干净部署后执行无 --force 精确卸载
        res = self._run_dispatch("--deploy", "--force")
        self.assertEqual(res.returncode, 0, res.stderr)
        res = self._run_dispatch("--uninstall")
        self.assertEqual(res.returncode, 0, res.stderr)

        # 核验受管资产全部清空，第三方与 Gemini V4 完好无损
        self.assertFalse(router_file.exists())
        self.assertFalse(ana_file.exists())
        self.assertFalse(bmad_file.exists())
        self.assertFalse(manifest_file.exists())
        self.assertFalse((self.fake_home / ".local/share/bmad-solo/v5").exists())
        self.assertTrue(self.third_party_rule.is_file())
        self.assertTrue(self.gemini_v4_file.is_file())
        self.assertEqual(
            self.gemini_v4_file.read_text(encoding="utf-8"),
            "# Gemini V4 Production Rule\n",
        )

        # 卸载后 --doctor -> UNINSTALLED (exit 0)
        res = self._run_dispatch("--doctor", "--json")
        self.assertEqual(res.returncode, 0, res.stderr)
        report = json.loads(res.stdout)
        self.assertEqual(report["state"], "UNINSTALLED")

    def test_gemini_isolation_hard_guard(self):
        """验证任何指向 .gemini 的部署/卸载均被硬拒绝，且 --doctor 能检出 .gemini V5 泄露。"""
        bad_home = self.fake_home / ".gemini"
        res = self._run_dispatch("--deploy", home_dir=bad_home)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("GEMINI_ISOLATION_VIOLATION", res.stderr)

        # 正常部署后若有人把 V5 文件错放进 .gemini，--doctor 必须报 CONFLICT
        res = self._run_dispatch("--deploy")
        self.assertEqual(res.returncode, 0, res.stderr)
        leak = self.fake_home / ".gemini/bmad-v5-leak.md"
        leak.write_text("# BMAD-Solo V5 leak\n", encoding="utf-8")
        res = self._run_dispatch("--doctor", "--json")
        self.assertEqual(res.returncode, 2, res.stderr)
        report = json.loads(res.stdout)
        self.assertEqual(report["state"], "CONFLICT")
        self.assertTrue(any("gemini-v5-leak" in c for c in report["conflicts"]))


if __name__ == "__main__":
    unittest.main()
