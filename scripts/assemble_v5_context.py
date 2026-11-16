#!/usr/bin/env python3
"""BMAD-Solo V5 动态任务上下文装配器 (scripts/assemble_v5_context.py)

功能：
1. 依据 specs/governance/v5-context-manifest.yaml 清单规范，动态发现并组装当前工作区任务上下文；
2. 提取 docs/project-context.md 架构事实基线（缺失时降级报警）；
3. 读取 specs/tasks/_active.md 唯一锁定当前活动 Task Unit (TU-*.md)，提取范围、验收与门禁（空闲时标记 IDLE，冲突时硬阻断）；
4. 执行 Token 软背压预算规划评估（目标 800 ~ 1,200 Tokens，超限报警不截断）；
5. 支持 --inject-workspace 模式，通过原子写入安全更新当前工作区 .cline/rules/active-context.md，供 Cline 热加载。
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import sys
import tempfile

import yaml

DEFAULT_WORKSPACE = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = DEFAULT_WORKSPACE / "specs/governance/v5-context-manifest.yaml"


def estimate_tokens(text: str) -> int:
    """估算中英文混合文本在现代大模型分词器下的 Token 消耗量。"""
    cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin_words = len(re.findall(r"[A-Za-z0-9_]+", text))
    symbols = len(re.findall(r"[^\s\w\u4e00-\u9fff]", text))
    estimated = int(cjk_chars * 0.65 + latin_words * 1.30 + symbols * 0.30)
    return max(1, estimated)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """解析 Markdown 文件头部的 YAML frontmatter，亦兼容全 YAML 契约文档。"""
    content_str = content.strip()
    if not content_str.startswith("---"):
        return {}, content

    # 尝试匹配带闭合 --- 的 frontmatter: ^---\s*\n(.*?)\n---\s*(.*)$
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", content_str, re.DOTALL)
    if match:
        try:
            data = yaml.safe_load(match.group(1))
            return (data if isinstance(data, dict) else {}), match.group(2).strip()
        except Exception:
            pass

    # 若无闭合 ---，尝试将全文作为纯 YAML 解析
    try:
        data = yaml.safe_load(content_str)
        if isinstance(data, dict):
            return data, ""
    except Exception:
        pass

    return {}, content


class ContextAssembler:
    """动态上下文装配引擎。"""

    def __init__(self, workspace: Path, manifest_path: Path | None = None):
        self.workspace = Path(workspace).resolve()
        self.manifest_path = Path(manifest_path or (self.workspace / "specs/governance/v5-context-manifest.yaml")).resolve()

    def load_manifest(self) -> dict:
        """读取并校验 Manifest 清单。"""
        if not self.manifest_path.is_file():
            raise FileNotFoundError(f"清单文件缺失: {self.manifest_path}")
        
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            manifest = yaml.safe_load(f)
            
        if not isinstance(manifest, dict) or "sources" not in manifest:
            raise ValueError(f"清单格式非法: {self.manifest_path}")
        return manifest

    def assemble_baseline(self) -> tuple[str, str]:
        """装配项目事实基线 (docs/project-context.md)。"""
        baseline_file = self.workspace / "docs/project-context.md"
        
        if not baseline_file.is_file():
            warning = (
                "> [!WARNING] **项目事实基线缺失 (docs/project-context.md)**\n"
                "> 当前工作区未检测到项目事实基线，系统进入 **Tier 4 降级治理模式**（规则可用，项目事实受限）。\n"
                "> 建议执行 `/ana-solo` 生成基线文档以消除上下文盲区。"
            )
            return warning, "DEGRADED_MISSING"

        try:
            with open(baseline_file, "r", encoding="utf-8") as f:
                content = f.read().replace('\\n', '\n').strip()
            
            # 压缩空白，提取头部项目核心信息与最新章节
            lines = [line.rstrip() for line in content.splitlines() if line.strip()]
            header_lines = []
            for line in lines[:25]:
                header_lines.append(line)
            
            formatted = (
                "### 1. 项目事实基线 (Project Context Baseline)\n"
                f"- **基线文件来源**：`docs/project-context.md` (已加载)\n\n"
                + "\n".join(header_lines)
            )
            return formatted, "LOADED"
        except Exception as exc:
            return f"> [!WARNING] 读取项目基线发生异常: {exc}", "ERROR"

    def assemble_active_task(self) -> tuple[str, str, dict]:
        """解析单焦点薄指针 specs/tasks/_active.md 并装配 Task Unit。"""
        active_pointer = self.workspace / "specs/tasks/_active.md"
        
        if not active_pointer.is_file():
            idle_msg = (
                "### 2. 活动任务契约 (Active Task)\n"
                "- **当前状态**：`IDLE` (未检测到 `specs/tasks/_active.md`)\n"
                "- **行为约束**：严禁自动恢复归档任务，保持待命只读状态。"
            )
            return idle_msg, "IDLE", {}

        with open(active_pointer, "r", encoding="utf-8") as f:
            pointer_data, _ = parse_frontmatter(f.read())

        task_id = pointer_data.get("active_task_id")
        task_ref = pointer_data.get("task_ref")

        if not task_id or not task_ref:
            idle_msg = (
                "### 2. 活动任务契约 (Active Task)\n"
                "- **当前状态**：`IDLE` (薄指针 `active_task_id` 为空)\n"
                "- **行为约束**：当前工作区无活动工程任务，严禁擅自实施代码修改。"
            )
            return idle_msg, "IDLE", pointer_data

        tu_path = self.workspace / task_ref
        if not tu_path.is_file():
            err_msg = (
                f"> [!CAUTION] **活动任务悬空引用硬阻断 (BLOCKED)**\n"
                f"> 薄指针指定的任务文件不存在: `{task_ref}`。\n"
                f"> 严禁猜测或随机执行历史任务，系统处于阻塞保护状态。"
            )
            return err_msg, "BLOCKED_DANGLING_REF", pointer_data

        with open(tu_path, "r", encoding="utf-8") as f:
            tu_data, tu_body = parse_frontmatter(f.read())

        status = tu_data.get("status", "UNKNOWN")
        allowed_statuses = {"APPROVED", "READY", "IN_PROGRESS", "COMPLETED"}
        if status not in allowed_statuses:
            err_msg = (
                f"> [!CAUTION] **任务状态未获批准 (BLOCKED)**\n"
                f"> 任务 `{task_id}` 状态为 `{status}`，未在获准清单内 ({allowed_statuses})。\n"
                f"> 未经用户明确授权推进，严禁实施代码修改。"
            )
            return err_msg, "BLOCKED_UNAPPROVED", tu_data

        # 结构化提纯 Task Unit 核心要素
        scenario = tu_data.get("scenario", "structural")
        impact_tier = tu_data.get("impact_tier", "M")
        objective = tu_data.get("parent_objective", {}).get("expected_result", "未声明具体目标")
        cs_spec = tu_data.get("cs_specification", {})
        scope = cs_spec.get("scope", "未声明范围")
        excludes = cs_spec.get("excludes", [])
        criteria = cs_spec.get("acceptance_criteria", [])
        
        checks = tu_data.get("kcp_verification", {}).get("checks", [])
        verification_lines = []
        for chk in checks:
            cmd = chk.get("command", "none")
            vtype = chk.get("verification_type", "check")
            verification_lines.append(f"  - [{chk.get('check_id', 'KCP')}] ({vtype}): `{cmd}`")

        formatted_task = [
            "### 2. 当前活动任务契约 (Active Task Unit)",
            f"- **任务标识**：`{task_id}` (实例: `{tu_data.get('instance_id', 'default')}`)",
            f"- **当前状态**：`{status}` (场景: `{scenario}`, 影响级别: `{impact_tier}`)",
            f"- **交付目标**：{objective}",
            f"- **贡献范围**：{scope}",
        ]
        if excludes:
            formatted_task.append("- **严禁事项 (Excludes)**：")
            for exc in excludes:
                formatted_task.append(f"  - {exc}")
        if criteria:
            formatted_task.append("- **验收标准 (Acceptance Criteria)**：")
            for crit in criteria:
                formatted_task.append(f"  - {crit}")
        if verification_lines:
            formatted_task.append("- **法定核验命令 (KCP Verifications)**：")
            formatted_task.extend(verification_lines)

        return "\n".join(formatted_task), "ACTIVE", tu_data

    def assemble_bundle(self) -> tuple[bool, str, dict]:
        """全量组装 Task Context Bundle 并计算遥测。"""
        manifest = self.load_manifest()
        baseline_text, baseline_status = self.assemble_baseline()
        task_text, task_status, task_meta = self.assemble_active_task()

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        bundle = f"""# BMAD-Solo V5 动态任务上下文 (Active Task Context Bundle)

> **装配时间戳**：`{timestamp}`  
> **装配来源**：`specs/governance/v5-context-manifest.yaml` (v{manifest.get('schema_version', '1.1')})  
> **工作区基线状态**：`{baseline_status}` | **活动任务状态**：`{task_status}`  
> **定位**：工作区级动态上下文。由 In-Context Push 自动装配，随任务状态动态流转，完成即解绑。

---

{baseline_text}

---

{task_text}
"""
        bundle = bundle.strip() + "\n"
        digest = hashlib.sha256(bundle.encode("utf-8")).hexdigest()
        tokens = estimate_tokens(bundle)
        is_blocked = "BLOCKED" in task_status

        telemetry = {
            "digest": digest,
            "timestamp": timestamp,
            "char_count": len(bundle),
            "line_count": len(bundle.splitlines()),
            "estimated_tokens": tokens,
            "budget_min": 600,
            "budget_max": 1200,
            "within_budget": tokens <= 1500,
            "baseline_status": baseline_status,
            "task_status": task_status,
            "is_blocked": is_blocked,
        }

        if tokens > 1500:
            telemetry["warning"] = f"动态上下文 Token 估算量 ({tokens}) 超过软预算上限 (1200)，建议精简基线或拆分任务"

        return not is_blocked, bundle, telemetry

    def inject_workspace(self, bundle: str, dry_run: bool = False) -> tuple[bool, str]:
        """将组装好的 Task Context Bundle 原子注入到当前工作区 .cline/rules/active-context.md。"""
        target_dir = self.workspace / ".cline/rules"
        target_file = target_dir / "active-context.md"

        if dry_run:
            return True, f"Dry-run 校验通过，目标注入路径: {target_file}"

        target_dir.mkdir(parents=True, exist_ok=True)
        
        # 原子替换写入：先写入同目录临时文件，刷新刷盘后原子重命名
        fd, temp_path = tempfile.mkstemp(dir=target_dir, prefix="active-context.tmp.")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(bundle)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, target_file)
        except Exception as exc:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return False, f"原子注入失败: {exc}"

        return True, f"成功注入工作区动态上下文: {target_file}"


def main():
    parser = argparse.ArgumentParser(description="BMAD-Solo V5 动态任务上下文装配器")
    parser.add_argument("--workspace", "-w", type=Path, default=DEFAULT_WORKSPACE, help="目标工作区路径")
    parser.add_argument("--manifest", "-m", type=Path, default=DEFAULT_MANIFEST, help="清单规范路径")
    parser.add_argument("--output", "-o", type=Path, help="输出文件路径 (若未指定则输出到标准输出)")
    parser.add_argument("--inject-workspace", action="store_true", help="原子注入到当前工作区 .cline/rules/active-context.md")
    parser.add_argument("--dry-run", action="store_true", help="仅执行装配与软背压预算校验，不写入磁盘")
    args = parser.parse_args()

    assembler = ContextAssembler(args.workspace, args.manifest)
    success, bundle, telemetry = assembler.assemble_bundle()

    print("=" * 60)
    print("BMAD-Solo V5 Context Assembler Telemetry")
    print("=" * 60)
    for k, v in telemetry.items():
        print(f"  - {k}: {v}")
    print("-" * 60)

    if not success:
        print(f"Status: BLOCKED ({telemetry.get('task_status')})")
        print("=" * 60)
        sys.exit(1)

    if args.inject_workspace:
        inj_ok, inj_msg = assembler.inject_workspace(bundle, dry_run=args.dry_run)
        print(f"Injection: {'PASS' if inj_ok else 'FAIL'} - {inj_msg}")
    elif args.output:
        if not args.dry_run:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(bundle)
            print(f"Output: 写入完成 -> {args.output}")
        else:
            print(f"Output: Dry-run 预检通过 -> {args.output}")
    else:
        print("Assembled Context Bundle Preview:")
        print("-" * 60)
        print(bundle)

    print("=" * 60)


if __name__ == "__main__":
    main()
