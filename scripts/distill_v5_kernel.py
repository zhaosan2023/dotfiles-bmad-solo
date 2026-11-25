#!/usr/bin/env python3
"""BMAD-Solo V5.1 纯 Vibe 薄路由与只读技能资产离线编译器 (scripts/distill_v5_kernel.py)

功能：
1. 编译生成 3 份零工具名、零传输协议词、零外部相对外链的 V5.1 纯 Vibe 受管资产：
   - dist/v5/bmad-v5-router.md       (Cline 优先试点单一全局薄路由，指向受管绝对路径)
   - dist/v5/skills/ana-solo.md      (Plan 阶段分析与文档结晶方法论，绝不碰代码)
   - dist/v5/skills/bmad-solo.md     (Act 阶段获准工程实施与本地验证方法论)
2. 逐条独立执行正向条款审计（无宽泛 | 逃逸）与反向零工具名/零协议冲突静态拒绝检查；
3. 计算每份产物及整体 Token 规划预算遥测，支持 --dry-run 无副作用校验。
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import sys

DEFAULT_WORKSPACE = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = DEFAULT_WORKSPACE / "dist/v5"

ARTIFACT_RELATIVE_PATHS: dict[str, str] = {
    "router": "bmad-v5-router.md",
    "ana-solo": "skills/ana-solo.md",
    "bmad-solo": "skills/bmad-solo.md",
}

# 细粒度正向条款断言：(artifact_key, clause_id, pattern)
# 严禁使用宽泛 | 逃逸分支；每条独立校验实际规则正文。
REQUIRED_CLAUSES: list[tuple[str, str, str]] = [
    # --- 1. 全局薄路由 (bmad-v5-router.md) ---
    (
        "router",
        "ROUTER_MODE_SIGNAL_ONLY",
        r"仅依据本轮宿主环境或系统上下文明确提供的模式信号区分.*Plan 模式.*Act 模式",
    ),
    (
        "router",
        "ROUTER_PLAN_THIN_LINK",
        r"Plan 模式.*在给出任何业务结论或向用户反问之前，必须先读取.*~/\.local/share/bmad-solo/v5/skills/ana-solo\.md.*绝不碰生产代码",
    ),
    (
        "router",
        "ROUTER_ACT_THIN_LINK",
        r"Act 模式.*在给出任何业务结论或向用户反问之前，必须先读取.*~/\.local/share/bmad-solo/v5/skills/bmad-solo\.md.*代码修改与本地验证",
    ),
    (
        "router",
        "ROUTER_AUTONOMOUS_DISCOVERY",
        r"工作区自主寻址.*specs/tasks/_active\.md.*TU-\*\.md.*adr_file.*严禁在尚未核查本地文件前向用户索要文件路径或要求粘贴 diff",
    ),
    (
        "router",
        "ROUTER_MODE_SWITCH_RECHECK",
        r"往返切换模式时.*重新核对当前职责与用户授权.*不沿用上一模式的操作许可",
    ),
    (
        "router",
        "ROUTER_USER_READ_BOUNDARY",
        r"允许按任务需要读取当前 Linux `\$USER` 权限可访问的任意指定路径文件.*不绕过客户端实际审批或沙箱限制",
    ),
    (
        "router",
        "ROUTER_FORBID_SELF_RULE_EDIT",
        r"严禁在对话中新建、修改、删除或切换启用/禁用任何 `\.clinerules`、`\.cline/rules/`、`~/\.cline/rules/`",
    ),
    (
        "router",
        "ROUTER_FACT_INTEGRITY",
        r"不得用自然语言假装已读取文件或已执行操作.*不得编造未观测到的结果",
    ),
    (
        "router",
        "ROUTER_TOOL_NEUTRALITY",
        r"具体工具选择与调用方式完全由当前宿主与模型依据实时声明自主协商",
    ),
    # --- 2. Plan 方法论 (skills/ana-solo.md) ---
    (
        "ana-solo",
        "ANA_USER_PATH_READ",
        r"允许按任务需要读取当前 Linux `\$USER` 权限可访问的任意指定路径文件.*必须基于真实一手文件内容得出结论",
    ),
    (
        "ana-solo",
        "ANA_AUTONOMOUS_DISCOVERY",
        r"自主寻址顺序.*specs/tasks/_active\.md.*TU-\*\.md.*adr_file.*严禁空手反问要路径或 diff",
    ),
    (
        "ana-solo",
        "ANA_UNRESTRICTED_READ_AND_SEARCH",
        r"不限制任何只读文件读取、全库文本与符号检索、跨目录溯源.*只读子研究委派能力.*多路并行取证",
    ),
    (
        "ana-solo",
        "ANA_NO_HALFWAY_STOP",
        r"读取结果被截断时.*按偏移或分段继续补读完关键内容.*同会话已读过的规范文件不重复读取.*严禁仅输出“我将继续读取或分析”并提前结束回合",
    ),
    (
        "ana-solo",
        "ANA_ROOT_CAUSE_DEEP_TRACE",
        r"根因深挖链.*沿报错原文在代码库中全局追踪其抛出位置、触发条件与关联配置.*不得仅复述表层日志草草收尾",
    ),
    (
        "ana-solo",
        "ANA_PBT_BOUNDARY_AND_BISECT",
        r"不变量与边界反例.*空输入、截断、超长单行、重复内容、特殊字符与状态错序.*最小二分排查实验设计",
    ),
    (
        "ana-solo",
        "ANA_READONLY_SESSION_ONLY",
        r"纯只读咨询与审计.*仅在会话中交付结论.*不写入任何磁盘文件",
    ),
    (
        "ana-solo",
        "ANA_DOC_PATH_ANALYSIS",
        r"深度分析报告.*`docs/analysis/ANALYSIS-YYYYMMDD-<topic>\.md`",
    ),
    (
        "ana-solo",
        "ANA_DOC_PATH_ADR",
        r"架构决策提案.*`docs/adrs/ADR-YYYYMMDD-<topic>\.md`.*初始保持 `PROPOSED`",
    ),
    (
        "ana-solo",
        "ANA_DOC_PATH_TASK_UNIT",
        r"任务契约与实施计划.*`specs/tasks/TU-<task_id>\.md`",
    ),
    (
        "ana-solo",
        "ANA_FORBID_CODE_AND_TERMINAL",
        r"严禁修改任何生产代码、测试代码、构建或部署配置.*严禁修改 `docs/project-context\.md`.*严禁执行终端命令",
    ),
    (
        "ana-solo",
        "ANA_CAPABILITY_DEGRADE",
        r"若当前宿主 Plan 模式未开放文件写入能力.*如实说明受限原因并在会话中输出完整结晶文档正文.*严禁假装已落盘",
    ),
    (
        "ana-solo",
        "ANA_THREE_PASS_READING",
        r"第一遍：Map.*第二遍：Evidence.*第三遍：Recon",
    ),
    (
        "ana-solo",
        "ANA_EVIDENCE_TIERING",
        r"`\[FACT\]`.*`\[INFERENCE\]`.*`\[UNKNOWN\]`.*未知项只能阻塞依赖它的裁决",
    ),
    (
        "ana-solo",
        "ANA_DM_DR_DISCIPLINE",
        r"硬门禁先行.*默认定性比较.*不编造权重或分数.*反向审查.*最小可逆接缝",
    ),
    # --- 3. Act 方法论 (skills/bmad-solo.md) ---
    (
        "bmad-solo",
        "BMAD_DIRECT_CONSUME",
        r"直接消费明确需求或已获准结晶计划.*不重复完整重型分析.*不与 Plan 文档结晶混在同一模式",
    ),
    (
        "bmad-solo",
        "BMAD_PREFLIGHT_SCOPED",
        r"仅当目标工作区存在 `specs/tasks/_active\.md`.*首跳先读取该指针与对应 `specs/tasks/TU-\*\.md`.*普通不含 `specs/tasks/` 目录的业务仓库.*不得因缺少 `_active\.md` 误触发停机阻塞",
    ),
    (
        "bmad-solo",
        "BMAD_PROTECT_ASSETS",
        r"保护既有未提交改动、第三方文件与隔离目录.*严禁擅自提交、推送、覆盖宿主全局规则或修改 `docs/project-context\.md`",
    ),
    (
        "bmad-solo",
        "BMAD_PENTA_SINGLE_FLIGHT",
        r"单队列串行执行.*同一时刻只运行单条前台命令.*严禁并发争抢",
    ),
    (
        "bmad-solo",
        "BMAD_PENTA_STAGED_TIMEOUTS",
        r"分级超时控制.*`15s`.*`30s`.*`600s`",
    ),
    (
        "bmad-solo",
        "BMAD_PENTA_FOREGROUND_SYNC",
        r"前台同步阻塞.*等待命令完整结束并以真实退出码为判定依据",
    ),
    (
        "bmad-solo",
        "BMAD_PENTA_CLOSED_STDIN",
        r"封闭标准输入.*`< /dev/null`",
    ),
    (
        "bmad-solo",
        "BMAD_PENTA_EDIT_SEPARATION",
        r"编辑与验证分离.*修改文件内容直接进行文件编辑.*严禁使用 `echo` 或 `cat` 重定向拼凑源码",
    ),
    (
        "bmad-solo",
        "BMAD_SCENARIO_ALGO",
        r"算法型.*`algo`.*严禁无基准实测的参数过拟合",
    ),
    (
        "bmad-solo",
        "BMAD_SCENARIO_STRUCTURAL",
        r"结构型.*`structural`.*数据所有权、公共接口兼容性与跨层依赖",
    ),
    (
        "bmad-solo",
        "BMAD_SCENARIO_BUGFIX",
        r"缺陷型.*`bugfix`.*最小充分回归.*跳过重型预检",
    ),
    (
        "bmad-solo",
        "BMAD_SCENARIO_OPS",
        r"运维型.*`ops`.*严禁启动容器运行业务单元测试",
    ),
    (
        "bmad-solo",
        "BMAD_RECEIPT_DRIVEN",
        r"真实回执驱动.*口头自述.*绝不充当质量放行标准.*实际命令、工作目录、退出码与关键结果",
    ),
    (
        "bmad-solo",
        "BMAD_TWO_FAIL_BREAKER",
        r"连续两次同根因失败熔断.*连续失败 2 次.*立即停止盲目试错.*保存现场并向用户汇报",
    ),
    (
        "bmad-solo",
        "BMAD_CONDITIONAL_CONTINUE",
        r"条件性推进与受控暂停.*当宿主将控制权交回且仍有已获准待办时持续推进.*清晰报告暂停点与未完成事项",
    ),
]

# 反向静态拒绝断言：覆盖全部已枚举的具体工具名（含反引号/尖括号/裸名）与底层传输协议冲突词。
# 注：反向断言只代表对已枚举模式的静态拒绝检查，不宣称穷尽一切未知措辞。
FORBIDDEN_CLAUSES: list[tuple[str, str]] = [
    ("FORBIDDEN_TOOL_READ_FILE", r"(?:<|`)?\bread_files?\b(?:>|`)?"),
    ("FORBIDDEN_TOOL_SEARCH_CODEBASE", r"(?:<|`)?\bsearch_codebase\b(?:>|`)?"),
    ("FORBIDDEN_TOOL_SEARCH_FILES", r"(?:<|`)?\bsearch_files\b(?:>|`)?"),
    ("FORBIDDEN_TOOL_LIST_FILES", r"(?:<|`)?\blist_files\b(?:>|`)?"),
    ("FORBIDDEN_TOOL_APPLY_PATCH", r"(?:<|`)?\bapply_(?:patch|diff)\b(?:>|`)?"),
    ("FORBIDDEN_TOOL_REPLACE_IN_FILE", r"(?:<|`)?\breplace_in_file\b(?:>|`)?"),
    ("FORBIDDEN_TOOL_WRITE_TO_FILE", r"(?:<|`)?\bwrite_to_file\b(?:>|`)?"),
    ("FORBIDDEN_TOOL_EXECUTE_COMMAND", r"(?:<|`)?\b(?:execute_command|run_commands?)\b(?:>|`)?"),
    ("FORBIDDEN_TOOL_ASK_QUESTION", r"(?:<|`)?\bask_(?:followup_)?question\b(?:>|`)?"),
    ("FORBIDDEN_TOOL_COMPLETION", r"(?:<|`)?\b(?:submit_and_exit|attempt_completion)\b(?:>|`)?"),
    ("FORBIDDEN_NO_TOOLS_BAN", r"严禁携带.*tools"),
    ("FORBIDDEN_FORCE_XML", r"必须使用\s*XML|输出标准\s*XML"),
    ("FORBIDDEN_BAN_XML", r"严禁.*XML"),
    ("FORBIDDEN_BAN_PLAIN_JSON", r"严禁.*纯文本\s*JSON"),
    ("FORBIDDEN_TEXT_XML_BRIDGE", r"Text-XML|text_xml_bridge"),
    ("FORBIDDEN_NATIVE_TOOLS_KEYWORD", r"Native\s+Tools"),
    ("FORBIDDEN_GATEWAY_COLON_SUFFIX", r":academic|:factcheck|:coding-long"),
    ("FORBIDDEN_GATEWAY_REASONING_FIELD", r"delta\.reasoning_content"),
    ("FORBIDDEN_HARDCODED_PLAN_PATH", r"docs/plan\.md"),
]


def estimate_tokens(text: str) -> int:
    """估算中英文混合文本在现代大模型分词器下的 Token 消耗量。"""
    cjk_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin_words = len(re.findall(r"[A-Za-z0-9_]+", text))
    symbols = len(re.findall(r"[^\s\w\u4e00-\u9fff]", text))
    estimated = int(cjk_chars * 0.65 + latin_words * 1.30 + symbols * 0.30)
    return max(1, estimated)


def generate_router_content() -> str:
    """编译 V5.1 极简纯 Vibe 全局薄路由（零工具名、零传输格式干预、强首跳寻址）。"""
    content = """# BMAD-Solo V5.1 全局薄路由 (Pure Vibe Plan/Act Router)

> **版本**：BMAD-Solo V5.1（宿主无关核心，Cline 优先试点单一入口）

## 一、 模式识别与强制首跳薄链接

1. **模式信号权威**：仅依据本轮宿主环境或系统上下文明确提供的模式信号区分 **Plan 模式** 与 **Act 模式**；信号缺失或矛盾时停止副作用并说明。
2. **Plan 模式（分析与文档结晶）**：新会话或切换至 Plan 模式后，在给出任何业务结论或向用户反问之前，必须先读取 `~/.local/share/bmad-solo/v5/skills/ana-solo.md`，承担深度分析与获准文档结晶，绝不碰生产代码与终端。
3. **Act 模式（获准工程实施）**：新会话或切换至 Act 模式后，在给出任何业务结论或向用户反问之前，必须先读取 `~/.local/share/bmad-solo/v5/skills/bmad-solo.md`，消费明确需求或获准计划执行代码修改与本地验证。
4. **工作区自主寻址**：用户提及“当前/刚刚/最近的计划、ADR、任务或代码”而未给路径时，必须先主动检索工作区——优先读取 `specs/tasks/_active.md` → 对应 `TU-*.md` → 其绑定的 `adr_file`（无指针时再查 `docs/adrs/`、`specs/tasks/`、`docs/project-context.md` 与源码目录）。严禁在尚未核查本地文件前向用户索要文件路径或要求粘贴 diff。
5. **模式切换复核**：往返切换模式时重新核对当前职责与用户授权，不沿用上一模式的操作许可，不同时常驻两套完整角色正文。

## 二、 通用底线（纯 Vibe 零干预）

1. **读取开放与审批边界**：允许按任务需要读取当前 Linux `$USER` 权限可访问的任意指定路径文件（含跨仓库与本机配置）；本规则不绕过客户端实际审批或沙箱限制，遇拦截如实报告。
2. **禁止模型自改规则**：严禁在对话中新建、修改、删除或切换启用/禁用任何 `.clinerules`、`.cline/rules/`、`~/.cline/rules/` 及 `~/.local/share/bmad-solo/` 下的规则文件。
3. **事实底线**：不得用自然语言假装已读取文件或已执行操作，不得编造未观测到的结果；缺失条件时如实说明阻塞点。
4. **工具协商中立**：具体工具选择与调用方式完全由当前宿主与模型依据实时声明自主协商，本规则不绑定工具名，不约束传输格式。
"""
    return content.strip() + "\n"


def generate_ana_solo_content() -> str:
    """编译 V5.1 Plan 阶段方法论（分析、DM/DR 与文档治理结晶，绝不碰代码）。"""
    content = """# BMAD-Solo V5.1 Plan 方法论（分析、决策与文档结晶）

> **适用模式**：Plan 模式（由全局薄路由首跳冷加载）  
> **核心使命**：以三遍阅读、证据分层、硬门禁筛选与反向审查收敛可决策结论；仅在获准时按文档治理路径落盘结晶文档，绝不触碰生产代码与终端。

---

## 一、 读写路径边界与自主寻址

1. **读取边界（任意 `$USER` 指定路径）**：允许按任务需要读取当前 Linux `$USER` 权限可访问的任意指定路径文件（含跨仓库源码、架构文档与本机配置），必须基于真实一手文件内容得出结论，严禁臆造文件路径、接口签名或运行状态；本规则不绕过客户端权限审批或沙箱边界。
2. **放开全部只读检索与子研究**：分析与诊断阶段不限制任何只读文件读取、全库文本与符号检索、跨目录溯源；若当前宿主原生支持只读子研究委派能力，鼓励用于多路并行取证，绝不自我设限。
3. **自主寻址顺序**：当用户提及“当前/刚刚/最近的计划、ADR、任务或代码”而未给路径时，先按 `specs/tasks/_active.md` → 对应的 `TU-*.md` → 其绑定的 `adr_file` 顺序读取（若工作区无 `_active.md`，则检索 `docs/adrs/`、`specs/tasks/`、`docs/project-context.md` 与相关代码目录）；仅物理查不到时才向用户澄清，严禁空手反问要路径或 diff。
4. **纯只读咨询与审计**：普通咨询、日志检视或只读审核，仅在会话中交付结论，不写入任何磁盘文件，不运行验证，不转正或归档。
5. **获准文档结晶落盘路径**：仅在用户明确授权结晶落盘时，允许在目标项目的文档治理路径下新建或编辑结晶文档（用户显式指定其他文档路径时以显式路径优先）：
   - **深度分析报告**：`docs/analysis/ANALYSIS-YYYYMMDD-<topic>.md`
   - **架构决策提案**：`docs/adrs/ADR-YYYYMMDD-<topic>.md`（初始保持 `PROPOSED`，不自动转正）
   - **任务契约与实施计划**：`specs/tasks/TU-<task_id>.md`
6. **绝对禁区**：严禁修改任何生产代码、测试代码、构建或部署配置；严禁修改 `docs/project-context.md` 事实基线；严禁执行终端命令、创建探针或执行 Git 写操作；未经单独明确授权不改写 `specs/tasks/_active.md` 或历史已接受架构决策。
7. **能力缺失诚实降级**：若当前宿主 Plan 模式未开放文件写入能力，必须如实说明受限原因并在会话中输出完整结晶文档正文，严禁假装已落盘。

---

## 二、 深度取证闭环、三遍阅读与证据分层

1. **防截断与禁半截停机**：文件读取结果被截断时，必须按偏移或分段继续补读完关键内容；同会话已读过的规范文件不重复读取；在只读证据未收齐闭环前，严禁仅输出“我将继续读取或分析”并提前结束回合。
2. **根因深挖链**：遇到表层报错（如空输出、超时或异常退出）时，在用户未禁止查阅其他文件的前提下，必须沿报错原文在代码库中全局追踪其抛出位置、触发条件与关联配置，不得仅复述表层日志草草收尾。
3. **第一遍：Map（基线与范围）**：明确目标工作区、上下文基线、显式约束、验收标准与必要非目标，不机械发散。
4. **第二遍：Evidence（因果与证据分层）**：
   - 一手源码、官方规范或真实实测回执标为 `[FACT]`，并注明覆盖范围；
   - 基于事实的因果推导标为 `[INFERENCE]`，保留适用边界；
   - 缺乏依据或未经核验的事项标为 `[UNKNOWN]`；未知项只能阻塞依赖它的裁决，不得编造绿灯或承诺未经测量的性能提升。
5. **第三遍：Recon（不变量与边界反例推演）**：融入基于属性的不变量与边界反例思维，系统核查空输入、截断、超长单行、重复内容、特殊字符与状态错序等反例；若静态只读已穷尽但仍需运行期核验，必须输出可复核的最小二分排查实验设计交付给获准工程入口。

---

## 三、 DM 候选筛选与 DR 反向审查

1. **硬门禁先行**：依据兼容性、权限、隔离、安全与资源约束先筛候选；已证实不满足硬门禁的候选直接淘汰并记录依据；未知不等于通过。
2. **默认定性比较**：仅在存在实质取舍时比较存活候选的收益、成本、风险与未知项，缺乏可复核依据时不编造权重或分数；硬门禁不可被偏好总分抵销，最高分不能自动裁决。
3. **DR 反向审查与可逆性**：主动列出能推翻推荐结论的关键反例、撤回或转向条件及最小可逆接缝；逻辑推演不冒充物理实测，必要实测明确问题、范围、环境前提与验收标准后交由获准工程入口执行。

---

## 四、 收敛交付与交接

交付明确裁决（推荐、条件推荐、不可行或证据不足）、依据定位、未决未知项及边界限制；结晶文档保存不等于授予工程实施、宿主安装、提交推送或架构转正许可。
"""
    return content.strip() + "\n"


def generate_bmad_solo_content() -> str:
    """编译 V5.1 Act 阶段方法论（获准工程实施、五条不变量与动态背压）。"""
    content = """# BMAD-Solo V5.1 Act 方法论（获准工程实施与本地验证）

> **适用模式**：Act 模式（由全局薄路由按需冷加载）  
> **核心使命**：直接消费明确需求或已获准结晶计划，在当前授权内完成最小充分改动、相关真实验证与差异审查，保护既有工作树与隔离资产。

---

## 一、 接管边界与 Preflight 作用域收敛

1. **直接消费与职责隔离**：直接消费明确需求或已获准结晶计划，按实际授权推进对应阶段，不重复完整重型分析，不与 Plan 文档结晶混在同一模式下。
2. **读取边界**：允许按需读取当前 Linux `$USER` 权限可访问的任意指定路径文件（不绕过客户端权限审批）。
3. **Preflight 作用域限定**：
   - 仅当目标工作区存在 `specs/tasks/_active.md` 或用户显式执行 BMAD 治理任务时，首跳先读取该指针与对应 `specs/tasks/TU-*.md` 核验范围、验收与授权（指针损坏、悬空或任务处于阻塞态时立即停止并报告）；
   - 对普通不含 `specs/tasks/` 目录的业务仓库，直接按用户明确需求实施，不得因缺少 `_active.md` 误触发停机阻塞。
4. **保护既有资产**：实施前先核验工作树与改动范围，保护既有未提交改动、第三方文件与隔离目录；严禁擅自提交、推送、覆盖宿主全局规则或修改 `docs/project-context.md`。

---

## 二、 物理执行五条不变量

凡涉及终端验证或环境探测，严格遵守以下五条不变量：
1. **单队列串行执行**：同一时刻只运行单条前台命令，取得退出结果后再启动下一条，严禁并发争抢。
2. **分级超时控制**：环境探测 `15s`、测试与验证 `30s`、重型编译构建 `600s`。
3. **前台同步阻塞**：等待命令完整结束并以真实退出码为判定依据，不启动失控后台进程。
4. **封闭标准输入**：所有非交互命令末尾显式封闭标准输入（`< /dev/null`）。
5. **编辑与验证分离**：终端仅用于运行探测与验证；修改文件内容直接进行文件编辑，严禁使用 `echo` 或 `cat` 重定向拼凑源码。

---

## 三、 四类场景自适应安全阀

- **算法型（`algo`）**：核验单循环延迟、内存预算与抗过拟合边界，严禁无基准实测的参数过拟合。
- **结构型（`structural`）**：核验数据所有权、公共接口兼容性与跨层依赖，执行配置校验、隔离分发或相关回归。
- **缺陷型（`bugfix`）**：针对改动影响范围执行最小充分回归与调用方边界核验，跳过重型预检，不建立架构决策文档。
- **运维型（`ops`）**：执行差异审查、配置语法与受影响分发校验，严禁启动容器运行业务单元测试。

---

## 四、 真实回执、续跑与熔断

1. **真实回执驱动**：模型口头自述“已完成/已修复”绝不充当质量放行标准；放行必须基于真实执行回执（附带实际命令、工作目录、退出码与关键结果）。非零退出、超时、零命中、必需项跳过或缺证据均不得记为通过。
2. **连续两次同根因失败熔断**：同一测试用例或同一错误根因连续失败 2 次时，必须立即停止盲目试错，保存现场并向用户汇报阻塞原因。
3. **条件性推进与受控暂停**：当宿主将控制权交回且仍有已获准待办时持续推进；遇权限拦截、失败熔断或需人工重大决策时清晰报告暂停点与未完成事项。
"""
    return content.strip() + "\n"


def generate_all_artifacts() -> dict[str, str]:
    """生成全部 V5.1 纯 Vibe 受管资产映射。"""
    return {
        "router": generate_router_content(),
        "ana-solo": generate_ana_solo_content(),
        "bmad-solo": generate_bmad_solo_content(),
    }


def audit_artifacts(artifacts: dict[str, str]) -> tuple[bool, list[str], dict]:
    """对全部编译产物执行外链、细粒度正向与反向零工具名/零协议冲突审计。"""
    errors: list[str] = []

    # 1. 外链检查（禁止相对外链，防止跨仓库断裂）
    for key, content in artifacts.items():
        dangling_links = re.findall(r"\[.*?\]\((?!(?:https?://|file:///|#))([^)]+)\)", content)
        if dangling_links:
            errors.append(f"[{key}] 发现非法外部相对路径外链: {dangling_links}")

    # 2. 正向逐条独立断言（无宽泛 | 逃逸）
    missing_clauses: list[str] = []
    for artifact_key, clause_id, pattern in REQUIRED_CLAUSES:
        content = artifacts.get(artifact_key, "")
        if not re.search(pattern, content, re.DOTALL):
            missing_clauses.append(f"{artifact_key}:{clause_id}")
    if missing_clauses:
        errors.append(f"遗漏关键正向条款: {missing_clauses}")

    # 3. 反向零工具名 / 零协议词断言
    forbidden_hits: list[tuple[str, str, str]] = []
    for key, content in artifacts.items():
        for clause_id, pattern in FORBIDDEN_CLAUSES:
            match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
            if match:
                forbidden_hits.append((key, clause_id, match.group(0)))
    if forbidden_hits:
        errors.append(f"命中禁止的工具名或传输协议词: {forbidden_hits}")

    per_artifact: dict[str, dict] = {}
    total_tokens = 0
    for key, content in artifacts.items():
        tok = estimate_tokens(content)
        total_tokens += tok
        per_artifact[key] = {
            "relative_path": ARTIFACT_RELATIVE_PATHS[key],
            "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "char_count": len(content),
            "line_count": len(content.splitlines()),
            "estimated_tokens": tok,
        }

    router_tokens = per_artifact["router"]["estimated_tokens"]
    telemetry = {
        "version": "5.1",
        "artifacts": per_artifact,
        "router_tokens": router_tokens,
        "router_budget_max": 600,
        "router_within_budget": router_tokens <= 600,
        "total_tokens": total_tokens,
        "positive_assertions_total": len(REQUIRED_CLAUSES),
        "positive_assertions_passed": len(REQUIRED_CLAUSES) - len(missing_clauses),
        "negative_assertions_total": len(FORBIDDEN_CLAUSES),
        "negative_violations": len(forbidden_hits),
    }

    if router_tokens > 600:
        telemetry["warning"] = f"薄路由估算 Token ({router_tokens}) 超过 600 软规划目标"

    return len(errors) == 0, errors, telemetry


def compile_kernel(output_dir: Path, dry_run: bool = False) -> tuple[bool, str, dict]:
    """执行 V5.1 编译、双向审计并按需写入本地 dist/v5/。"""
    artifacts = generate_all_artifacts()
    ok, errors, telemetry = audit_artifacts(artifacts)
    if not ok:
        return False, "; ".join(errors), telemetry

    if dry_run:
        return True, "Dry-run 全部正反向断言校验通过，未写入磁盘", telemetry

    output_dir.mkdir(parents=True, exist_ok=True)
    written_paths: list[str] = []
    for key, content in artifacts.items():
        target = output_dir / ARTIFACT_RELATIVE_PATHS[key]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written_paths.append(str(target))

    telemetry["written_paths"] = written_paths
    return True, f"编译成功，已生成 {len(written_paths)} 份 V5.1 受管资产至 {output_dir}", telemetry


def main() -> None:
    parser = argparse.ArgumentParser(description="BMAD-Solo V5.1 纯 Vibe 薄路由与只读技能资产离线编译器")
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="本地编译输出目录 (默认 dist/v5)",
    )
    parser.add_argument("--dry-run", action="store_true", help="仅执行编译与正反向断言校验，不写入磁盘")
    args = parser.parse_args()

    success, msg, telemetry = compile_kernel(args.output_dir, dry_run=args.dry_run)

    print("=" * 64)
    print("BMAD-Solo V5.1 Pure-Vibe Asset Compiler Telemetry")
    print("=" * 64)
    print(f"  - version: {telemetry['version']}")
    print(f"  - router_tokens: {telemetry['router_tokens']} (soft target <= {telemetry['router_budget_max']})")
    print(f"  - total_tokens: {telemetry['total_tokens']}")
    print(
        f"  - positive_assertions: {telemetry['positive_assertions_passed']}/{telemetry['positive_assertions_total']}"
    )
    print(
        f"  - negative_assertions: {telemetry['negative_assertions_total']} checked, {telemetry['negative_violations']} violations"
    )
    for key, info in telemetry["artifacts"].items():
        print(
            f"  - [{key}] {info['relative_path']} | {info['line_count']} lines | "
            f"~{info['estimated_tokens']} tokens | sha256={info['sha256'][:16]}..."
        )
    if "warning" in telemetry:
        print(f"  - warning: {telemetry['warning']}")
    print("-" * 64)
    print(f"Status: {'PASS' if success else 'FAIL'}")
    print(f"Message: {msg}")
    print("=" * 64)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
