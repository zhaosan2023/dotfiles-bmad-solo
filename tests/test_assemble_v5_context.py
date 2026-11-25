"""单元测试：BMAD-Solo V5.1 工作区上下文摘要装配器 (tests/test_assemble_v5_context.py)

覆盖领域：
1. 纯 Vibe 清单校验与解析 (specs/governance/v5-context-manifest.yaml)，断言零工具名与零旧桥接词；
2. 项目基线提取与缺失降级报警 (docs/project-context.md)；
3. 单焦点任务薄指针与 Task Unit 绑定校验 (空闲、激活、悬空阻断、未批准阻断)；
4. Token 软背压预算规划与遥测生成；
5. 可选工作区原子写入 (.cline/rules/active-context.md)。
"""

from pathlib import Path
import re
import tempfile
import unittest

from scripts.assemble_v5_context import ContextAssembler
from scripts.distill_v5_kernel import FORBIDDEN_CLAUSES


class TestAssembleV5Context(unittest.TestCase):
    """装配器核心功能与软门禁单元测试套件。"""

    def setUp(self):
        self.workspace = Path(__file__).resolve().parent.parent
        self.assembler = ContextAssembler(self.workspace)

    def test_manifest_loading_pure_vibe(self):
        """验证真实工作区中的 V5.1 纯 Vibe 清单规范加载且不含具体工具名。"""
        manifest = self.assembler.load_manifest()
        self.assertIsInstance(manifest, dict)
        self.assertEqual(manifest.get("schema_version"), "2.0")
        self.assertIn("sources", manifest)
        self.assertIn("path_boundaries", manifest)
        self.assertIn("flows", manifest)
        self.assertNotIn("tools_registry", manifest)
        self.assertFalse(manifest["path_boundaries"]["workspace_rule_injection_default"])

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
            text, status, _ = temp_assembler.assemble_active_task()
            self.assertEqual(status, "IDLE")
            self.assertIn("当前状态**：`IDLE`", text)

    def test_assemble_active_task_dangling_blocked(self):
        """验证薄指针引用不存在的 Task Unit 时硬阻断。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_ws = Path(tmpdir)
            tasks_dir = temp_ws / "specs/tasks"
            tasks_dir.mkdir(parents=True)
            active_file = tasks_dir / "_active.md"
            active_file.write_text(
                "---\nactive_task_id: TU-NON-EXISTENT\ntask_ref: specs/tasks/TU-NON-EXISTENT.md\n---\n",
                encoding="utf-8",
            )

            temp_assembler = ContextAssembler(temp_ws, self.assembler.manifest_path)
            text, status, _ = temp_assembler.assemble_active_task()
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
            active_file.write_text(
                "---\nactive_task_id: TU-DRAFT\ntask_ref: specs/tasks/TU-DRAFT.md\n---\n",
                encoding="utf-8",
            )

            temp_assembler = ContextAssembler(temp_ws, self.assembler.manifest_path)
            text, status, _ = temp_assembler.assemble_active_task()
            self.assertEqual(status, "BLOCKED_UNAPPROVED")
            self.assertIn("任务状态未获批准", text)

    def test_bundle_token_budget_and_pure_vibe(self):
        """验证标准工作区组装包的 Token 软背压预算与零禁用工具名。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_ws = Path(tmpdir)
            (temp_ws / "docs").mkdir(parents=True)
            (temp_ws / "docs/project-context.md").write_text("# Project Context\n- Name: demo\n", encoding="utf-8")
            (temp_ws / "specs/tasks").mkdir(parents=True)
            (temp_ws / "specs/tasks/TU-DEMO.md").write_text(
                "---\ntask_id: TU-DEMO\nstatus: READY\nparent_objective:\n  expected_result: 演示目标\n"
                "cs_specification:\n  scope: 演示范围\n---\n",
                encoding="utf-8",
            )
            (temp_ws / "specs/tasks/_active.md").write_text(
                "---\nactive_task_id: TU-DEMO\ntask_ref: specs/tasks/TU-DEMO.md\n---\n",
                encoding="utf-8",
            )
            temp_assembler = ContextAssembler(temp_ws, self.assembler.manifest_path)
            success, bundle, telemetry = temp_assembler.assemble_bundle()
            self.assertTrue(success)
            self.assertTrue(telemetry["within_budget"])
            self.assertLessEqual(telemetry["estimated_tokens"], 1500)
            self.assertEqual(telemetry["baseline_status"], "LOADED")
            self.assertEqual(telemetry["task_status"], "ACTIVE")
            for clause_id, pattern in FORBIDDEN_CLAUSES:
                self.assertIsNone(re.search(pattern, bundle, re.IGNORECASE | re.DOTALL), clause_id)

    def test_inject_workspace_dry_run_and_actual(self):
        """验证可选工作区写入机制（Dry-run 与实际原子替换）。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_ws = Path(tmpdir)
            temp_assembler = ContextAssembler(temp_ws, self.assembler.manifest_path)
            bundle = "# Test Bundle Content"

            ok, msg = temp_assembler.inject_workspace(bundle, dry_run=True)
            self.assertTrue(ok)
            self.assertIn("Dry-run", msg)
            self.assertFalse((temp_ws / ".cline/rules/active-context.md").exists())

            ok, msg = temp_assembler.inject_workspace(bundle, dry_run=False)
            self.assertTrue(ok)
            injected_file = temp_ws / ".cline/rules/active-context.md"
            self.assertTrue(injected_file.exists())
            self.assertEqual(injected_file.read_text(encoding="utf-8"), bundle)


if __name__ == "__main__":
    unittest.main()
