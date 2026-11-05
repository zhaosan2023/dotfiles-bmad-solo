````markdown
建议采用“冻结编码内环 + 失败证据驱动的离线治理外环”，但生产部署目前只能判定为有条件可行：Tmux 分窗不能代替权限隔离，稳定前缀也不能保证商业 API 100% 缓存命中。[3] 下文交付研究蓝图与代码草案；本轮没有修改文件、运行测试或启动服务。

# dotfiles-bmad-solo + solo-distill-mcp 集成部署深度研究方案

## 一、结论与需要修正的前提

- 将 `solo-distill-mcp` 留在短生命周期治理外环，日常 Coder 不挂载。
- Coder、Reflector、Curator 分离执行；评估器、测试准入与权限策略不属于任何模型的可变表面。
- 当前 Schema 3.0 的报文改造必须同时覆盖选择器、任务构造、冻结报文认证和独立 Oracle，不能只调整 `task_v3.py`。
- 新规则只从真实失败及已验证修复中产生；命令维护、路由维护和初始安全约束不伪装成“失败学习”。
- 根级文档实施 12,000 字符硬上限，但同时约束实际加载的根文件与子目录文件总量。
- 缓存收益、规则收益及隔离效果分别验收，不能用静态配置替代运行时证据。

### 1.1 已检查的本地边界

本地参考资产已读取，包括：

- `/home/veryfd/project/solo-distill-mcp/docs/references/astra-weight.md`
- `/home/veryfd/project/solo-distill-mcp/docs/references/RSIhub-agent-paper.md`

源码回执显示，V3 选择链调用本地语法提取、关系构建和确定性选择；其源码同时明确声明：语法充分性不等于独立语义验收。[23]

因此，“没有多轮模型侦察”可以成立，但不能进一步推出“免疫幻觉”。最终蒸馏仍包含模型推断，当前任务证据也明确保留 `requires_independent_review` 边界。[23]

另有四项部署缺口：

- 当前项目声明 Python ≥3.12、运行依赖为空；不能把 Hypothesis、mypy、Ruff 或 pytest 当作已安装能力。[24]
- 当前来源配置指向历史 `fastcode-sample`，不是本工具工程的通用扫描授权；不能直接复用于新集成。[24]
- `/home/veryfd/project/solo-distill-mcp/docs/project-context.md` 的读取返回不存在。
- 已检查的方法论规则文件不证明目标宿主实际加载，也不能证明当前安装的完整 `Solo-Engine v4.1` 与本方案兼容。[25]

部分重复文件读取返回了“outdated”提示。下面的接口分析依据实际返回的源码片段和搜索回执，不声称已经完成当前安装版本的逐字节兼容认证。

## 二、六篇论文的一对一工程映射

本地解构文献有启发价值，但论文原文与工程推导必须分开。

### 2.1 ACE：角色分离、增量更新，而不是权限隔离证明

ACE 的核心是 Generator、Reflector、Curator 的模块化分工，以及增量更新与 grow-and-refine；它还明确讨论过度简化造成的 brevity bias 和整体重写造成的 context collapse。[5]

工程映射：

1. Generator 对应 Coder，只生成业务补丁。
2. Reflector 从可信执行轨迹提炼候选经验，不写规则。
3. Curator 对候选执行去重、冲突检查、作用域分配及准入，只发布增量。
4. 稳定规则使用永久 ID；更新既有规则，而不是反复重写整份文档。
5. 完整证据留在冷存储，不因根文件压缩而删除。

“Coder 不得修改 `AGENTS.md`”是本方案的安全不变量，不是 ACE 已经证明的操作系统属性。

其必要性可以形式化说明：

- 若 Coder 同时控制代码候选 C 和约束 G，则验收关系 `Accept(C, G)` 的两个输入都可被同一主体修改。
- 仅限制修改顺序，不能排除它把 G 放宽到接受错误 C。
- 因此，必须冻结本轮 G，并让 Coder 无法修改 G、评估器及其执行入口。

验收：

- Coder 尝试修改任意层级规则文件时，操作被拒绝。
- 同样的补丁经其他写入工具、Shell、符号链接路径或覆盖文件入口也被拒绝。
- 权限拒绝发生在执行前；事后发现越界只能作为第二层防线。

### 2.2 Configuration Smells：消除规则重复，不承诺“根治百分比”

原文对 100 个仓库的分析报告 Lint Leakage 62%、Context Bloat 42%、Skill Leakage 35%；这些是样本文件中的出现比例，不是三个独立的性能损失比例。[9]

工程映射：

- Lint Leakage：由工具负责的检查，不重复转写成自然语言规则。
- Context Bloat：根文件只保留公共承重约束及定位信息。
- Skill Leakage：多步骤操作流程进入按需读取的技能或操作规程，根文件只保留触发条件与指针。
- Blind References：链接目标和路由命令必须真实存在。
- 冲突：按规则 ID、作用域及动作对象检测，冲突候选不自动合并。

需要区分：

- “使用四空格缩进”属于格式规则，应进入格式化配置。
- “执行哪个命令能检查格式”属于工具定位信息，可以留在 Commands。
- “不要从未经认证的包字段恢复可信来源分母”属于架构边界，不是 Linter 的职责。

验收不写“62% 已根治”，而写：

- 受管动作目录中，工具拥有的规则不能进入文档。
- 流程类候选不能进入根文件。
- 未分类自由文本保持待审，不靠正则匹配宣称语义过滤完整。

### 2.3 Evaluating AGENTS.md：控制非必要指令，但不能声称长度决定成功率

最新原文发现上下文文件一般没有改善任务成功率，并增加推理成本；其消融也明确指出，文件长度和具体指令类别没有表现出强性能影响。[7]

因此，不宜将它概括成“越长，任务完成率越低”。

工程映射：

- 极简是预算与维护策略，不是未经测量的成功率保证。
- 每条学习规则必须回答：
  - 它阻止了什么已经发生的错误？
  - 为什么现有工具或代码契约不能覆盖？
  - 为什么要跨任务持久化？
  - 为什么需要放在根文件，而不是局部文件？
- 对新增规则做删除消融：去掉该规则，是否出现可重复退化？
- 没有证据的规则可以保持候选，不为了填满模板而准入。

“Minimal Load-Bearing”定义为：

> 删除后会损害已验证的安全边界、任务定位或行为约束，并且不能由更便宜的工具或局部路由替代。

### 2.4 AGIT-Template：四板块是本项目投影，不是论文原定模板

2026 年 11 月原文实际提出 16 个类别、三个层级：10 个 Required、4 个 Gap、2 个 Recommended，并明确说明这不是普遍最优结构，也不是各类别改善任务表现的证明。[20]

因此，本方案采用以下四板块，但标注为“项目工程投影”：

| 项目板块 | 内容 | 排除内容 |
|---|---|---|
| Commands | 已验证命令、作用域、执行环境 | 编造命令、自动安装步骤 |
| Architecture Invariants | 所有权、认证、副作用、版本边界 | 符号全集、实现逐行总结 |
| Anti-Overdesign | 有失败证据的具体禁止动作 | 空泛“保持简单”、绝对禁止 helper |
| Routing Table | 改动路径 → 定义/调用方/验证入口 | 完整目录树、任务进度 |

根文件不必填满所有内容类别；安全和性能等低频但关键的信息，依风险保留或路由。

验收：结构完整性、信息正确性、宿主加载和任务效果分别检查，不能以“四标题都存在”作为治理成功。

### 2.5 AHE：真实轨迹驱动，但不把所有经验写成 Never

AHE 研究可观测性驱动的 harness 演化，覆盖提示词、工具及运行机制等不同失败表面；其原文也讨论回归盲点和自修改治理边界。[17]

PBT、Hypothesis 与最小反例是本方案的工程扩展，不冒充 AHE 已验证的具体实现。

工程映射：

1. 从实际执行取得错误栈、超时、退出状态、工具拒绝和资源观测。
2. 将故障归属到正确表面：
   - 业务逻辑错误 → 修代码和回归测试。
   - 超时工具没有执行硬截止 → 修执行器。
   - 可重复的错误操作选择 → 候选上下文规则。
3. 只有最后一类，才可能进入 `AGENTS.md`。
4. 规则写成“禁止动作 + 必要条件或替代动作”，而不是无限积累 Never。

例如：

> 禁止把传输写入完成登记为语义验收通过；等待独立消费及所需语义审核回执。

而不是：

> 永远要小心，避免潜在的问题。

### 2.6 效率论文：先纠正引用与 Token 口径

`arXiv:2511.12884` 对应的是 *Agent READMEs: An Empirical Study of Context Files for Agentic Coding*，不是所述效率论文。[19]

28.64% 中位耗时下降和 16.58% 输出 Token 减少，来自 *On the Impact of AGENTS.md Files on the Efficiency of AI Coding Agents*，正确编号为 `arXiv:2601.20404`；其研究涉及 10 个仓库、124 个 PR。[18]

这些结果：

- 不等于总输入输出 Token 下降。
- 不证明 Routing Table 单独造成该效果。
- 不能直接外推为本集成的生产指标。[18]

工程映射：

- 用路由表减少无目标搜索。
- 用明确测试作用域减少盲跑。
- 同时保留调用方、跨模块边界和相关集成验证。
- 通过本项目配对实验测量效果，不把论文数字写成上线 SLA。

## 三、方法论总架构

Astra 一手研究支持从可计算表征定位问题、实施局部干预并进行实际评测；将其映射为 AST 侦察属于工程类比，不证明 AST 关系具有完整业务语义。[15]

RSIHub 将演化策略与执行、评估及谱系记录分离，并把评估置于可变表面之外；其结果也显示优化收益不总能迁移到保留任务。[16]

本方案据此采用：

```text
固定安全策略、评估器、授权契约
                │
                ▼
Scout ── Interface Snapshot ──► Coder
                                  │
                              业务补丁
                                  ▼
                               Breaker
                                  │
                       可信执行回执与反例
                                  ▼
                         独立 Reflector
                                  │
                         结构化候选经验
                                  ▼
                              Curator
                                  │
                      确定性过滤、局部增量
                                  ▼
                      下一会话规则版本 G(n+1)
```

关键时间不变量：

- 本轮 Coder 始终使用 G(n)。
- Curator 不能把 G(n+1) 注入仍在运行的 Coder。
- 熔断后可以生成候选，但不能通过改规则直接重开原失败轮次。
- 新规则生效需要下一会话或明确的新执行实例。

# 模块 1：Tmux 4+1 拓扑、状态总线与背压

## 1.1 五个 Pane 的责任与权限

Tmux 在此是操作界面。下面的权限是必须另行实现和验收的沙箱契约，不由分窗自动提供。

| Pane | 职责 | 可写表面 | 禁止表面 |
|---|---|---|---|
| 0 Orchestrator | 调度、状态迁移、预算与熔断 | 单一状态投影、调度事件 | 业务代码、规则、评估器 |
| 1 Scout | AST、受限历史考古 | 独立接口快照输出区 | 来源代码、规则、测试 |
| 2 Coder | 业务补丁 | 本轮授权源码集合 | 所有规则、测试准入、状态与回执 |
| 3 Breaker | 执行门禁、保存反例 | 独立测试提案与执行输出区 | 规则、放宽评估配置 |
| 4 Curator | 按事件唤醒治理外环 | 规则候选；获准后发布规则 | 业务源码、评估器、授权策略 |

Reflector 不增加常驻 Pane：由 Pane 4 的可信协调器启动独立短生命周期进程。它与 Curator 不共享可变对话历史，只交换结构化工件。

Breaker 可以提议新增测试，但提议测试不能自行成为权威判据。测试准入由固定契约和可信执行层控制，避免“测试生成者兼任验收标准制定者”。

## 1.2 必须实现的安全边界

- Coder 使用独立身份或等价的真实沙箱边界。
- 冻结规则挂载只读，包括子目录规则和宿主支持的覆盖文件。
- Coder 不可访问宿主 Tmux 控制 socket、控制器进程、发布凭据或评估密钥。
- 不向 Coder 暴露可任意执行宿主 Shell 的代理入口。
- 业务写入必须经过路径白名单；写入工具、Shell 和其他可达入口适用同一策略。
- 权限配置及受管启动器由模型不可写的可信主体拥有。
- 事后差异检查覆盖新增文件、删除、重命名、未跟踪文件和符号链接，不只检查普通 `git diff`。

同一 UID 的不同进程、Git worktree、`chmod` 和提示词禁止条款，都不能单独作为生产级防篡改证明。

## 1.3 状态总线

拟定状态根：

`/home/veryfd/project/solo-distill-mcp/.solo/state/`

拟定数据布局：

```text
.solo/state/
  current.json
  events/
  proposals/
  refs/
```

规则：

- `current.json` 是程序生成投影，不允许模型直接改写。
- 事件由可信控制器串行接纳；工件通过哈希引用。
- 原始测试和模型回执留在批准的验证区，不复制成第二套账本。
- 接纳时核对 `run_id`、候选摘要、规则摘要、评估器摘要、事件序号和阶段。
- 发布采用临时文件、同步、原子替换，并使用独占锁。
- 哈希证明绑定，不证明来源可信；可信来源必须由权限和发布者身份保证。
- 在控制器覆盖未经实际证明前，当前平台任务记录仍是权威入口，不能仅创建该目录就宣称完成切换。

状态流：

```text
SCOUTING → CODING → CHECKING
                    ├─ PASS → RECONCILING → CLOSED
                    ├─ EXECUTED_FAIL → 下一次 CODING
                    └─ BLOCKED / 第三次失败 → CIRCUIT_OPEN
```

建议将“3 轮”定义为最多三个代码候选检查轮次，不是“初次提交外再重试三次”。

- 同一失败签名连续出现两次：强制定向重审，不继续机械补丁。
- 第三次失败：熔断。
- 缺依赖、超时后清理未知、零收集、必要跳过：直接 BLOCKED。
- 规则修改不能重置轮次计数。
- Coder 和 Breaker 对同一候选串行；模型间并发不得绕开方法论现有单飞纪律。

### 状态核的代码草案

这是可独立实现的纯函数核心，不包含尚未实现的身份认证和持久化层：

```python
from dataclasses import dataclass
from typing import Literal

Verdict = Literal["PASS", "EXECUTED_FAIL", "BLOCKED"]

@dataclass(frozen=True)
class CheckState:
    phase: Literal[
        "CHECKING", "CODING", "RECONCILING", "CIRCUIT_OPEN", "BLOCKED"
    ] = "CHECKING"
    attempts: int = 0
    last_failure: str | None = None
    repeated: int = 0
    directional_review_required: bool = False

def consume_verdict(
    state: CheckState,
    verdict: Verdict,
    failure_signature: str | None = None,
) -> CheckState:
    if state.phase != "CHECKING":
        raise ValueError("只能消费当前检查阶段的回执")
    if state.attempts >= 3:
        raise ValueError("检查轮次已耗尽")
    if verdict not in {"PASS", "EXECUTED_FAIL", "BLOCKED"}:
        raise ValueError("未知检查结果")

    attempts = state.attempts + 1
    if verdict == "BLOCKED":
        return CheckState(phase="BLOCKED", attempts=attempts)
    if verdict == "PASS":
        return CheckState(phase="RECONCILING", attempts=attempts)
    if not failure_signature:
        raise ValueError("执行失败必须具有失败签名")

    repeated = (
        state.repeated + 1
        if state.last_failure == failure_signature
        else 1
    )
    return CheckState(
        phase="CIRCUIT_OPEN" if attempts == 3 else "CODING",
        attempts=attempts,
        last_failure=failure_signature,
        repeated=repeated,
        directional_review_required=repeated >= 2,
    )
```

生产消费之前，可信层还必须证明回执对应当前候选；这个函数不能接纳模型自报的 PASS。

## 1.4 Tmux 启动脚本草案

拟定工件：

`/home/veryfd/project/solo-distill-mcp/scripts/tmux_solo_loop.sh`

以下脚本启动五个受管执行入口，不虚构当前存在的模型 CLI 或沙箱命令：

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

root=/home/veryfd/project/solo-distill-mcp
run_id=${1:?必须提供执行实例标识}

[[ "$run_id" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$ ]] || exit 64
command -v tmux >/dev/null || exit 69

roles=(orchestrator scout coder breaker curator)
launchers=(
  "${SOLO_ORCHESTRATOR_LAUNCHER:?}"
  "${SOLO_SCOUT_LAUNCHER:?}"
  "${SOLO_CODER_LAUNCHER:?}"
  "${SOLO_BREAKER_LAUNCHER:?}"
  "${SOLO_CURATOR_LAUNCHER:?}"
)

commands=()
for i in "${!roles[@]}"; do
  launcher=${launchers[$i]}
  [[ "$launcher" = /* && -f "$launcher" && -x "$launcher" ]] || exit 66
  printf -v cmd 'exec %q %q %q' "$launcher" "$root" "$run_id"
  commands+=("$cmd")
done

socket="solo-$run_id"
session="solo-$run_id"

if tmux -L "$socket" has-session -t "$session" 2>/dev/null; then
  printf '%s\n' "拒绝覆盖已有会话" >&2
  exit 73
fi

created=0
cleanup() {
  if [[ "$created" = 1 ]]; then
    tmux -L "$socket" kill-session -t "$session" 2>/dev/null || true
  fi
}
trap cleanup ERR

tmux -L "$socket" new-session -d -s "$session" -n solo \
  -c "$root" "${commands[0]}"
created=1

tmux -L "$socket" set-option -t "$session" pane-base-index 0
tmux -L "$socket" set-window-option -t "$session:solo" remain-on-exit on

for i in 1 2 3 4; do
  tmux -L "$socket" split-window -d -t "$session:solo" \
    -c "$root" "${commands[$i]}"
done

for i in "${!roles[@]}"; do
  tmux -L "$socket" select-pane -t "$session:solo.$i" -T "${roles[$i]}"
done

tmux -L "$socket" select-layout -t "$session:solo" tiled
tmux -L "$socket" list-panes -t "$session:solo" \
  -F '#{pane_index} #{pane_title} #{pane_pid} #{pane_dead}'
trap - ERR
```

启动器契约：

- Orchestrator 运行可信状态机。
- Scout、Coder、Breaker 等待类型化任务，不把消息文本作为 Shell。
- Curator 常驻的只是轻量事件等待器；模型及 MCP 进程仅在合法触发时启动。
- 这五个启动器必须先在 Phase 1 实现和验收；脚本自身不提供沙箱。

# 模块 2：缓存保护与 Schema 3.0 报文改造

## 2.1 缓存目标必须拆成三层

1. 应用层：冻结前缀字节保持一致。
2. 网关层：上游实际渲染后的缓存前缀、工具定义和断点保持一致。
3. 提供商层：取得真实缓存读取及费用回执。

只有第一层能够由本地确定性检查做到 100%。官方文档明确指出，会话复用不保证命中；共享前缀也不一定是已缓存前缀。[3]

Coder 的固定前缀应包含：

- 固定模型及缓存相关设置。
- 固定、窄腰工具定义。
- 冻结版根规则及本轮所需子目录规则。
- 基础接口快照。
- 本轮授权与任务契约。

新增问题、诊断、补丁和工具结果追加到尾部。

业务源码修改后，必须以“基础快照 + 有序补丁”更新事实；下一次接口冻结重新建版本。不能为了缓存保留已经失真的代码表征。

## 2.2 当前精确耦合点

当前收到的源码和搜索回执显示：

- `task_v3.py` 先序列化 `question`、`dimensions`，再序列化 `sources`。
- V3 选择器调用共享的 `scouting_v2.select_prompt()`。
- `preparation_v3.py` 比较选择器和任务构造器的消息及精确 POST。
- `_check_frozen_post()` 认证精确原字节，并仅允许特定生成控制后缀。
- 独立任务 Oracle 和选择 Oracle 也独立构造同一报文。[23]

因此，单改 `task_v3.py` 会导致选择与准备链不一致，不能声称兼容。

## 2.3 推荐分成两个独立改造

### 改造 A：显式的新报文布局

新增独立的 `prompt_layout_version`，不要借用 `selection_version` 表示报文变化。

拟定值：

- 旧默认：`legacy-question-first-v1`
- 新布局：`source-prefix-v1`

新布局：

```text
system prompt
    ↓
operation + 经认证骨架 + 完整 sources + 稳定 coverage
    ↓
question + dimensions
```

注意：

- 当前任务 Payload 没有单独的全库 AST 骨架字段；新增骨架是扩展契约，不是简单重排。
- 骨架只取认证包中的必要字段，不发送完整宏观机器资产。
- 完整来源正文、别名及允许来源集合不能因缓存而缩小。
- 时间戳、选择耗时、请求 ID 和查询派生身份不进入静态前缀。
- `coverage` 只有在确实不随问题变化时才属于静态部分。

新布局的序列化核心草案：

```python
import hashlib
import json
from dataclasses import dataclass

@dataclass(frozen=True)
class PromptBytes:
    prefix: bytes
    payload: bytes
    prefix_sha256: str

def encode_json(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")

def serialize_source_prefix(
    *,
    skeleton: dict,
    sources: list[dict],
    coverage: dict,
    question: str,
    dimensions: list[dict],
) -> PromptBytes:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("问题必须非空")
    if not sources or not dimensions:
        raise ValueError("来源与维度必须非空")

    static = {
        "operation": "compression",
        "skeleton": skeleton,
        "sources": sources,
        "coverage": coverage,
    }
    dynamic = {
        "question": question,
        "dimensions": dimensions,
    }
    prefix = encode_json(static)[:-1] + b","
    payload = prefix + encode_json(dynamic)[1:]
    return PromptBytes(
        prefix=prefix,
        payload=payload,
        prefix_sha256=hashlib.sha256(prefix).hexdigest(),
    )
```

该函数是报文序列化核心，不代替现有 `_question_identity()`、来源认证和包预算校验。

保持：

- 正文上限 98,304 字节。
- 精确 POST 上限 150,000 字节。
- 新增骨架和提供商字段也计入真实 POST 预算。
- JSON 身份规范化与传输序列化分开；不要对传输对象全局 `sort_keys=True`，否则布局意图可能失效。[23]

### 改造 B：网关提供商适配

报文字段重排只是提高前缀稳定性。当前代际 OpenAI 文档还指出：如果只缓存完整的“静态内容 + 动态内容”，下一次不同动态尾部未必能复用较短公共前缀；需要合适断点。[3]

因此：

- OpenAI：针对实际模型和 API 验证静态内容结束处的断点与缓存配置。
- Anthropic：对稳定工具、系统内容和消息块配置缓存边界，生命周期按其 API 设置。[21]
- Gemini：明确采用哪一代模型及哪种 API；当前返回的文档区分新 Interactions API 与支持显式缓存的旧接口，不可混用缓存指标。[22]

当前本地网关是固定的兼容端点，不证明它支持或透传上述配置。[23]

不能把提供商专用字段直接塞进现有冻结 POST 后宣布通过。需要：

1. 新传输契约。
2. 独立编码器。
3. 对应冻结字节认证。
4. 实际网关透传证据。
5. 实际缓存读取指标。

旧版文档中的缓存门槛也不能硬编码为所有模型通用值。

## 2.4 查询选择变化的限制

当前冻结选择包含问题身份，不能把问题 A 的 `frozen_selection` 直接用于问题 B。[23]

新布局只有在以下内容一致时复用完整来源前缀：

- 同一来源快照。
- 同一来源正文及顺序。
- 同一骨架。
- 同一稳定 coverage。

如果需要多个问题共享一个来源集合，应另立“问题无关 context set + 每问题充分性检查”契约；不能关闭当前冻结选择冲突检查来实现缓存。

## 2.5 缓存可观测性

当前网关回执只提取 `prompt_tokens`、`completion_tokens`、`total_tokens`，没有保存缓存读取的嵌套字段。[23]

拟定新增观测：

- `prefix_sha256`
- `rendered_prefix_identity`
- `cache_read_tokens`
- `cache_write_tokens`
- `uncached_input_tokens`
- `usage_present`
- `provider_api`
- `model_reported`
- `ttft_seconds`

原则：

- 缺失字段记为未知，不记为 0。
- 不根据本地前缀相同推算供应商缓存读取。
- 上游模型变换、断点丢失或工具表变化单独记录。
- 缓存预热涉及调用与费用，须单独授权。

# 模块 3：强类型、行为测试与 PBT 防过度设计

## 3.1 三层 Breaker

| 层级 | 检查对象 | 通过条件 | 失败处理 |
|---|---|---|---|
| L1 | 类型、语法、已配置静态规则 | 指定入口真实完成 | 缺工具则 BLOCKED |
| L2 | 当前行为及修复回归 | 非零收集、无必要跳过 | 返回精确失败 |
| L3 | 契约属性、生成输入、最小反例 | 有效样本执行、收缩结束 | 保存反例并独立重放 |

当前项目没有声明强类型或 PBT 依赖；标准库语法检查不能冒充类型检查。[24]

建议选择 Python 路径，Phase 1 单独批准并固定开发验证环境：

- 类型检查器：选择一个，不同时堆叠多套。
- Hypothesis：仅作为开发验证依赖，不扩大生产运行依赖。
- 不隐式安装；依赖不存在时相应门禁保持 BLOCKED。
- 不引入 TypeScript 工具链，因为当前工程不是 TypeScript 项目。[24]

## 3.2 防过度设计的判断依据

以下都不能机械地一律禁止：

- 单调用点 helper。
- `try/except`。
- 锁、超时和清理。
- 输入验证。

正确门禁是：

- helper 是否提供明确语义、独立验证或必要复用？
- 异常处理是否增加恢复能力，还是吞错并返回成功？
- 并发机制是否对应真实并发主体和可观测风险？
- 防御代码是否属于不可信边界？
- 删除它后，契约是否仍成立？

尤其本工程包含不可信来源、冻结报文和传输边界，不应把必要校验误删成“反过度设计”。

## 3.3 Hypothesis 的具体机制

建议初始参数，属于待批准实验配置：

- `max_examples = 200`
- 固定 CI 配置与版本。
- 使用可复现模式，禁用共享、不可控的例数据库。
- 进程硬期限默认 30 秒；超时不算属性通过。
- 慢集成属性另行绑定期限，不悄悄提高预算。
- 保存最终失败样本，而不是仅保存随机种子。
- “最小反例”表示相对于生成策略和收缩器的结果，不宣称全局数学最小。

优先属性：

1. 任意合法 Unicode 问题和维度，JSON 往返不改变文本。
2. 相同静态来源、不同问题，静态前缀完全一致。
3. 来源正文改变，来源身份及相关冻结认证必须改变。
4. 未发送来源引用不能通过。
5. 重签名的缩小来源集合不能冒充完整核心。
6. 第三轮失败之后不能自动恢复 CODING。
7. 缺回执、零测试和必要跳过不能进入 PASS。
8. 规则发布后，仍运行会话的冻结规则摘要不能改变。

生成策略和断言来源必须来自独立契约，不能让 Coder 从自己实现中生成“正确答案”。

## 3.4 最小反例如何返回 Coder

可信回执至少包含：

```json
{
  "status": "EXECUTED_FAIL",
  "candidate_sha256": "当前候选摘要",
  "evaluator_sha256": "固定评估器摘要",
  "property_id": "frozen_source_reference",
  "counterexample_ref": "受管反例工件标识",
  "shrink_completed": true,
  "replay_failed": true,
  "command_id": "批准的验证命令标识",
  "collected": 1,
  "required_skipped": 0
}
```

上面的中文值是字段含义说明，不是可执行回执。

Coder 只收到：

- 属性契约。
- 最小失败输入。
- 必要报错栈。
- 相关源码定位。
- 禁止改变的验证边界。

不返回完整演化历史，不让它修改测试断言或关闭错误检查。

# 模块 4：Curator 三条铁律与过滤流水线

## 4.1 外环触发与资源预算

允许触发：

- `RECONCILE_REQUESTED`
- `CIRCUIT_OPEN`

不允许触发：

- 每个编码 Turn。
- 每次工具调用。
- 每次通过测试。
- 模型主动“觉得文档需要改进”。

建议初始预算：

- 每个执行实例最多一次治理激活。
- 重复事件幂等，不重复请求模型。
- 冷预检与在线请求使用不同短生命周期 MCP 进程。
- 在线是否允许及其总调用预算，使用新集成授权；不继承历史样本授权。
- 无获准在线权限时只做离线过滤，不自动外发日志或源码。

当前 V3 stdio 入口采用单次业务调用期限，并要求在线操作独立授权及冻结选择；preflight 和 live 应使用分开的进程，不把一次进程当长期多次调用服务。[23]

## 4.2 Failure-Driven Only

新增学习规则必须绑定：

- 实际执行失败。
- 失败时的代码与规则版本。
- 固定评估器。
- 最小反例或必要错误轨迹。
- 修复 Diff。
- 修复后的真实通过回执。
- 非退化的相关回归。

不合格证据：

- 模型口述“可能会出错”。
- 没有实际执行的命令。
- 因缺依赖而未启动的测试。
- 测试超时且进程清理未知。
- 一次通过的普通实现。
- 只有失败，没有已验证修复。
- 为让测试通过而降低断言。

熔断可以唤醒 Curator，但如果修复尚未证明，它只能返回候选或 BLOCKED，不能发布新宪法。

例外必须明确区分：

- Commands 和 Routing Table 的事实更新不是学习规则。
- 初始安全约束不是从业务失败中学习的。
- 无损下沉和指针更新不算新增规则。

否则 Failure-Driven Only 会错误地禁止必要命令维护和首次治理初始化。

## 4.3 No Lint Leakage

推荐使用“工具所有权目录”，不只用关键词正则：

```text
规则语义键 → 所有者 → 实际验证入口 → 覆盖证据
```

例如：

- 格式、导入排序 → 静态工具。
- 类型注解要求 → 类型策略与类型检查配置。
- 重复流程 → 冷加载操作规程。
- 来源认证边界 → 架构规则。
- 版本入口不能静默替换 → 架构规则。

缺工具时应该补环境契约，不把检查责任永久转移给自然语言。

关键词过滤可作为预筛，但不能证明所有变体、否定句或隐含同义表达都被识别。

## 4.4 De-fluffing：从结构化动作生成命令式规则

推荐模型只输出结构化提案：

```text
action_id
scope
trigger
evidence_refs
supersedes_rule_id
```

真正文本由确定性模板渲染。新动作没有预批准模板时，进入待审，不直接采纳任意自由文本。

以下为过滤核心草案：

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class FailureEvidence:
    status: str
    failure_verified: bool
    repair_verified: bool
    regression_verified: bool
    counterexample_ref: str
    repair_diff_ref: str

@dataclass(frozen=True)
class Action:
    owner: str
    imperative: str
    allowed_scopes: frozenset[str]

CATALOG = {
    "separate_delivery_from_acceptance": Action(
        owner="architecture",
        imperative="禁止把传输完成登记为语义验收通过。",
        allowed_scopes=frozenset({"root"}),
    ),
    "preserve_versioned_entrypoints": Action(
        owner="architecture",
        imperative="保留版本化入口；禁止新版本静默替换旧入口。",
        allowed_scopes=frozenset({"root"}),
    ),
    "require_type_annotations": Action(
        owner="lint",
        imperative="",
        allowed_scopes=frozenset(),
    ),
}

def curate_rule(
    action_id: str,
    scope: str,
    evidence: FailureEvidence,
) -> str:
    if (
        evidence.status != "EXECUTED_FAIL"
        or not evidence.failure_verified
        or not evidence.repair_verified
        or not evidence.regression_verified
        or not evidence.counterexample_ref
        or not evidence.repair_diff_ref
    ):
        raise ValueError("缺少合格失败与修复证据")

    action = CATALOG.get(action_id)
    if action is None:
        raise ValueError("未知动作需要独立准入")
    if action.owner == "lint":
        raise ValueError("工具拥有的规则不能进入文档")
    if action.owner == "skill":
        raise ValueError("流程规则应进入冷加载规程")
    if scope not in action.allowed_scopes:
        raise ValueError("规则作用域不匹配")
    return action.imperative
```

`failure_verified` 等字段必须由可信证据验证器生成

[网关提示] 上游响应在约300.9秒时提前结束，全文尚未完成。已保留可安全交付的部分正文。可回复“继续”请求续写；这会发起新请求，不保证恢复原任务，也可能产生重复内容或额外费用。
````

output-token limit reached before a tool call — nudging for a more concise response (attempt 1/3)

Thinking

🔍 [网关进度] 上游有传输活动，尚无响应正文。 状态 transport_activity 耗时 10014 毫秒 发送 1 读取 263 字节 接受 0 字节 缓冲 0 字节 后台 unknown 🔍 [网关进度] 正在接收并缓冲响应，尚未完成校验。 状态 buffering 耗时 20015 毫秒 发送 1 读取 3974 字节 接受 1158 字节 缓冲 1158 字节 后台 unknown

Plan

本次只补完模块 4 的证据验证与发布边界，不重复前文。前面的过滤函数只是示意核心，不能凭几个布尔字段证明失败及修复真实发生。

## 模块 4 补充：可信证据与规则发布

- __可信输入__：Curator 只能提交证据标识；验证器从受保护回执读取状态，禁止模型自行填写 `failure_verified=true`。
- __绑定检查__：失败回执绑定失败候选、冻结规则和评估器摘要；修复回执绑定修复候选，并核对修复 Diff 确实连接两者。
- __有效执行__：检查实际退出状态、非零测试收集、必要跳过、反例重放和清理证据。缺项保持 BLOCKED。
- __数据隔离__：Reflector 只读演化用失败集；准入评估集由独立执行器掌握；盲测集不向 Reflector、Curator 或 Coder 暴露。

### 发布流水线

1. Reflector 输出结构化候选，不写规则。
2. Curator 执行工具所有权过滤、去重、冲突检查及作用域分配。
3. 在独立环境评估候选规则；机器过滤通过不等于行为效果通过。
4. 可信发布器检查授权、允许修改的路径及父版本摘要，拒绝覆盖外部新改动。
5. 保存新规则版本与真实回执，只在下一会话启用；当前 Coder 的冻结规则不变。

### MCP 挂接限制

失败日志先经过确定性截取和脱敏，再按授权范围交付分析角色。不要把新增失败轨迹字段直接塞进现有封闭 MCP 请求：应由独立适配层消费日志，需要扩展协议时另行版本化并验证调用方。

自动化验收可以证明证据绑定、过滤、权限和发布流程；不能仅靠正则或同一模型自评，证明任意新规则语义正确。

尚未交付的部分为模块 5 的字符预算与路由实现，以及模块 6 的分阶段验收矩阵。本轮仍未写文件或运行验证。
