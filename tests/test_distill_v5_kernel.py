"""单元测试与负向变异测试：BMAD-Solo V5.1 纯 Vibe 资产编译器 (tests/test_distill_v5_kernel.py)

覆盖领域：
1. 细粒度正向条款逐条通过，且正向正则不含宽泛 | 逃逸分支；
2. 删正文负向变异测试：逐条移除每个关键条款的正文片段，确认对应 clause_id 必然报失败；
3. 注毒负向变异测试：注入具体工具名（含反引号/尖括号/裸名）与底层传输协议冲突词，确认全部被 FORBIDDEN_CLAUSES 拦截；
4. 伴随资产零工具名与零旧协议回归（scripts/assemble_v5_context.py、specs/governance/v5-context-manifest.yaml）；
5. CLI 编译一致性（--dry-run 与隔离目录落盘）。
"""

from __future__ import annotations

from pathlib import Path
import re
import tempfile
import unittest

from scripts.distill_v5_kernel import (
    ARTIFACT_RELATIVE_PATHS,
    FORBIDDEN_CLAUSES,
    REQUIRED_CLAUSES,
    audit_artifacts,
    compile_kernel,
    generate_all_artifacts,
)


class TestDistillV5Kernel(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).resolve().parent.parent
        self.artifacts = generate_all_artifacts()

    def test_all_required_and_forbidden_pass_on_clean_artifacts(self):
        ok, errors, telemetry = audit_artifacts(self.artifacts)
        self.assertTrue(ok, f"Clean artifacts failed audit: {errors}")
        self.assertEqual(telemetry["positive_assertions_passed"], len(REQUIRED_CLAUSES))
        self.assertEqual(telemetry["negative_violations"], 0)
        self.assertLessEqual(telemetry["router_tokens"], 600)

    def test_required_clauses_have_no_broad_alternation_escape(self):
        """确保 REQUIRED_CLAUSES 中不包含未转义的顶层 | 分支逃逸。"""
        for artifact_key, clause_id, pattern in REQUIRED_CLAUSES:
            self.assertNotIn(
                "|",
                pattern,
                f"REQUIRED_CLAUSES[{artifact_key}:{clause_id}] 不应包含宽泛 | 逃逸分支",
            )

    def test_negative_mutation_delete_body_fails_each_required_clause(self):
        """逐条删除每个关键条款的命中正文行，断言必须触发对应 clause_id 失败。"""
        for artifact_key, clause_id, pattern in REQUIRED_CLAUSES:
            with self.subTest(artifact=artifact_key, clause=clause_id):
                mutated = dict(self.artifacts)
                original_text = mutated[artifact_key]
                match = re.search(pattern, original_text, re.DOTALL)
                self.assertIsNotNone(match, f"原始文本未命中 {artifact_key}:{clause_id}")
                # 删除匹配到的完整正文区间，验证相邻标题或其余段落不能替代通过
                mutated[artifact_key] = (
                    original_text[: match.start()] + original_text[match.end() :]
                )
                ok, errors, _ = audit_artifacts(mutated)
                self.assertFalse(ok, f"删除 {artifact_key}:{clause_id} 正文后断言居然误通过")
                self.assertTrue(
                    any(f"{artifact_key}:{clause_id}" in err for err in errors),
                    f"失败信息未精确定位 {artifact_key}:{clause_id}: {errors}",
                )

    def test_negative_mutation_poison_injection_caught(self):
        """注入各类历史毒模式、反引号/尖括号工具名与协议冲突词，断言全部被反向拦截。"""
        poison_samples = [
            ("FORBIDDEN_TOOL_READ_FILE", "请调用 `<read_file>` 读取文件"),
            ("FORBIDDEN_TOOL_READ_FILE", "优先使用 read_files 批量读取"),
            ("FORBIDDEN_TOOL_SEARCH_CODEBASE", "用 search_codebase 检索符号"),
            ("FORBIDDEN_TOOL_APPLY_PATCH", "修改时使用 `apply_patch`"),
            ("FORBIDDEN_TOOL_REPLACE_IN_FILE", "实施修改使用 replace_in_file"),
            ("FORBIDDEN_TOOL_WRITE_TO_FILE", "写文件使用 write_to_file"),
            ("FORBIDDEN_TOOL_EXECUTE_COMMAND", "运行命令调用 execute_command"),
            ("FORBIDDEN_TOOL_ASK_QUESTION", "使用 `ask_question` 澄清"),
            ("FORBIDDEN_TOOL_COMPLETION", "`submit_and_exit` 仅为退出动作"),
            ("FORBIDDEN_TOOL_COMPLETION", "最后调用 attempt_completion"),
            ("FORBIDDEN_NO_TOOLS_BAN", "客户端请求严禁携带 tools 字段"),
            ("FORBIDDEN_FORCE_XML", "必须使用 XML 标签调用工具"),
            ("FORBIDDEN_BAN_XML", "严禁使用 XML 标签包装工具"),
            ("FORBIDDEN_BAN_PLAIN_JSON", "严禁输出纯文本 JSON 伪装成工具调用"),
            ("FORBIDDEN_TEXT_XML_BRIDGE", "默认运行于 text_xml_bridge 模式"),
            ("FORBIDDEN_NATIVE_TOOLS_KEYWORD", "原生 Native Tools 直通模式"),
            ("FORBIDDEN_GATEWAY_COLON_SUFFIX", "Model ID 携带 :academic 后缀"),
            ("FORBIDDEN_GATEWAY_REASONING_FIELD", "推送至 delta.reasoning_content"),
            ("FORBIDDEN_HARDCODED_PLAN_PATH", "读取 docs/plan.md"),
        ]
        for expected_clause, poison_text in poison_samples:
            with self.subTest(expected=expected_clause, sample=poison_text):
                mutated = dict(self.artifacts)
                mutated["router"] = mutated["router"] + "\n" + poison_text + "\n"
                ok, errors, telemetry = audit_artifacts(mutated)
                self.assertFalse(ok, f"注入毒模式未被拦截: {poison_text}")
                self.assertGreaterEqual(telemetry["negative_violations"], 1)
                self.assertTrue(
                    any(expected_clause in err for err in errors),
                    f"未命中预期反向条款 {expected_clause}，实际错误: {errors}",
                )

    def test_companion_assets_free_of_forbidden_tool_names_and_protocols(self):
        """核验伴随 V5 资产同样零具体工具名与旧协议残留 (CRIT-01)。"""
        companion_files = [
            self.repo_root / "scripts/assemble_v5_context.py",
            self.repo_root / "specs/governance/v5-context-manifest.yaml",
        ]
        for path in companion_files:
            text = path.read_text(encoding="utf-8")
            for clause_id, pattern in FORBIDDEN_CLAUSES:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                self.assertIsNone(
                    match,
                    f"伴随文件 {path.name} 残留禁用词 [{clause_id}]: {match.group(0) if match else ''}",
                )

    def test_compile_kernel_dry_run_and_isolated_output(self):
        """核验 dry-run 无写副作用，以及隔离目录写入与内存生成完全一致。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "dist/v5"
            ok, _, _ = compile_kernel(out_dir, dry_run=True)
            self.assertTrue(ok)
            self.assertFalse(out_dir.exists())

            ok, _, telemetry = compile_kernel(out_dir, dry_run=False)
            self.assertTrue(ok)
            self.assertEqual(len(telemetry["written_paths"]), 3)
            for key, rel in ARTIFACT_RELATIVE_PATHS.items():
                written = (out_dir / rel).read_text(encoding="utf-8")
                self.assertEqual(written, self.artifacts[key])


if __name__ == "__main__":
    unittest.main()
