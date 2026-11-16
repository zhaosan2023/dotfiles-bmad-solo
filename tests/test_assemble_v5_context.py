"""单元测试：BMAD-Solo V5 动态任务上下文装配器 (tests/test_assemble_v5_context.py)

覆盖领域：
1. 清单校验与解析 (specs/governance/v5-context-manifest.yaml)；
2. 项目基线提取与缺失降级报警 (docs/project-context.md)；
3. 单焦点任务薄指针与 Task Unit 绑定校验 (空闲、激活、悬空阻断、未批准阻断)；
4. Token 软背压预算规划与遥测生成；
5. 工作区原子注入 (.cline/rules/active-context.md)。
"""

from pathlib import Path
import tempfile
import unittest

import yaml

from scripts.assemble_v5_context import ContextAssembler, estimate_tokens, parse_frontmatter


class TestAssembleV5Context(unittest.TestCase):
    """装配器核心功能与软门禁单元测试套件。"""

    def setUp(self):
        self.workspace = Path(__file__).resolve().parent.parent
        self.assembler = ContextAssembler(self.workspace)

    def test_manifest_loading(self):
        """验证真实工作区中的清单规范加载。"""
        manifest = self.assembler.load_manifest()
        self.assertIsInstance(manifest, dict)
        self.assertIn("sources", manifest)
        self.assertIn("tools_registry", manifest)
        self.assertIn("flows", manifest)

    def test_assemble_baseline_loaded(self):
        """验证真实工作区基线提取。"""
        text, status = self.assembler.assemble_baseline()
        self.assertEqual(status, "LOADED")
        self.assertIn("项目事实基线", text)
        self.assertIn("dotfiles-bmad-solo", text)

    def test_assemble_baseline_missing_degraded(self):
        """验证基线缺失时触发 Tier 4 降级警告 (DEGRADED_MISSING)。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_ws = Path(tmpdir)
            temp_assembler = ContextAssembler(temp_ws, self.assembler.manifest_path)
            text, status = temp_assembler.assemble_baseline()
            self.assertEqual(status, "DEGRADED_MISSING")
            self.assertIn("Tier 4 降级治理模式", text)

    def test_assemble_active_task_active(self):
        """验证活动任务解析（使用隔离测试固件）。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_ws = Path(tmpdir)
            tasks_dir = temp_ws / "specs/tasks"
            tasks_dir.mkdir(parents=True)
            tu_file = tasks_dir / "TU-TEST.md"
            tu_file.write_text(
                "---\n"
                "task_id: TU-TEST\n"
                "instance_id: inst-01\n"
                "status: READY\n"
                "parent_objective:\n"
                "  expected_result: 单元测试目标\n"
                "cs_specification:\n"
                "  scope: 单元测试范围\n"
                "  acceptance_criteria:\n"
                "    - CRIT-01: 测试验收准则\n"
                "---\n",
                encoding="utf-8",
            )
            active_file = tasks_dir / "_active.md"
            active_file.write_text(
                "---\n"
                "active_task_id: TU-TEST\n"
                "task_ref: specs/tasks/TU-TEST.md\n"
                "---\n",
                encoding="utf-8",
            )
            temp_assembler = ContextAssembler(temp_ws, self.assembler.manifest_path)
            text, status, meta = temp_assembler.assemble_active_task()
            self.assertEqual(status, "ACTIVE")
            self.assertEqual(meta.get("task_id"), "TU-TEST")
            self.assertIn("TU-TEST", text)
            self.assertIn("验收标准", text)

    def test_assemble_active_task_idle(self):
        """验证空闲薄指针时输出 IDLE 且不恢复归档任务。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_ws = Path(tmpdir)
            tasks_dir = temp_ws / "specs/tasks"
            tasks_dir.mkdir(parents=True)
            active_file = tasks_dir / "_active.md"
            active_file.write_text("---\nactive_task_id: null\ntask_ref: null\n---\n# Idle\n", encoding="utf-8")

            temp_assembler = ContextAssembler(temp_ws, self.assembler.manifest_path)
            text, status, meta = temp_assembler.assemble_active_task()
            self.assertEqual(status, "IDLE")
            self.assertIn("当前状态**：`IDLE`", text)

    def test_assemble_active_task_dangling_blocked(self):
        """验证薄指针引用不存在的 Task Unit 时硬阻断。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_ws = Path(tmpdir)
            tasks_dir = temp_ws / "specs/tasks"
            tasks_dir.mkdir(parents=True)
            active_file = tasks_dir / "_active.md"
            active_file.write_text("---\nactive_task_id: TU-NON-EXISTENT\ntask_ref: specs/tasks/TU-NON-EXISTENT.md\n---\n", encoding="utf-8")

            temp_assembler = ContextAssembler(temp_ws, self.assembler.manifest_path)
            text, status, meta = temp_assembler.assemble_active_task()
            self.assertEqual(status, "BLOCKED_DANGLING_REF")
            self.assertIn("悬空引用硬阻断", text)

    def test_assemble_active_task_unapproved_blocked(self):
        """验证任务状态非获准状态时硬阻断。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_ws = Path(tmpdir)
            tasks_dir = temp_ws / "specs/tasks"
            tasks_dir.mkdir(parents=True)
            tu_file = tasks_dir / "TU-DRAFT.md"
            tu_file.write_text("---\ntask_id: TU-DRAFT\nstatus: DRAFT\n---\n", encoding="utf-8")
            active_file = tasks_dir / "_active.md"
            active_file.write_text("---\nactive_task_id: TU-DRAFT\ntask_ref: specs/tasks/TU-DRAFT.md\n---\n", encoding="utf-8")

            temp_assembler = ContextAssembler(temp_ws, self.assembler.manifest_path)
            text, status, meta = temp_assembler.assemble_active_task()
            self.assertEqual(status, "BLOCKED_UNAPPROVED")
            self.assertIn("任务状态未获批准", text)

    def test_bundle_token_budget(self):
        """验证全量组装包的 Token 软背压预算。"""
        success, bundle, telemetry = self.assembler.assemble_bundle()
        self.assertTrue(success)
        self.assertTrue(telemetry["within_budget"])
        self.assertLessEqual(telemetry["estimated_tokens"], 1500)
        self.assertEqual(telemetry["baseline_status"], "LOADED")
        self.assertIn(telemetry["task_status"], {"ACTIVE", "IDLE"})

    def test_inject_workspace_dry_run_and_actual(self):
        """验证工作区注入机制（Dry-run 与实际原子替换）。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_ws = Path(tmpdir)
            temp_assembler = ContextAssembler(temp_ws, self.assembler.manifest_path)
            bundle = "# Test Bundle Content"
            
            # Dry-run
            ok, msg = temp_assembler.inject_workspace(bundle, dry_run=True)
            self.assertTrue(ok)
            self.assertIn("Dry-run", msg)
            self.assertFalse((temp_ws / ".cline/rules/active-context.md").exists())

            # 真实原子注入
            ok, msg = temp_assembler.inject_workspace(bundle, dry_run=False)
            self.assertTrue(ok)
            injected_file = temp_ws / ".cline/rules/active-context.md"
            self.assertTrue(injected_file.exists())
            self.assertEqual(injected_file.read_text(encoding="utf-8"), bundle)


if __name__ == "__main__":
    unittest.main()
