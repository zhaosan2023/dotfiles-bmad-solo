---
schema_version: "1.0-draft"
task_id: "TU-20261116-V5-STATIC-KERNEL"
instance_id: "inst-20261116-v5-static-kernel-01"
contract_version: "1"
candidate_version: "1.0"
status: COMPLETED
session_id: "dcafc95e-1444-4582-8ca2-3b69a0cf8a2c"
scenario: structural
impact_tier: M
parent_objective:
  objective_id: "OBJ-20261116-BMAD-V5-FOUNDATION"
  expected_result: "完成 BMAD-Solo V5 静态治理内核的离线保真提纯编译器与安全分发器，达成 Tier 4 降级就绪资产落地"
  source_ref: "docs/adrs/ADR-20261116-bmad-v5-in-context-push-architecture.md"
inputs:
  - "specs/governance/v5-context-manifest.yaml"
  - "docs/adrs/ADR-20261116-bmad-v5-in-context-push-architecture.md"
  - "/home/veryfd/.gemini/config/plugins/bmad-suite/skills/ana-solo/SKILL.md"
  - "/home/veryfd/.gemini/config/plugins/bmad-suite/skills/bmad/SKILL.md"
cs_specification:
  scope: "开发离线 AST 提纯编译器 scripts/distill_v5_kernel.py 与带锁原子替换分发器 scripts/dispatch_v5.sh，输出可受管分发至 ~/.cline/rules/bmad-core.md 的零外部依赖内联资产"
  excludes:
    - "未获授权的生产部署与 Git 自动提交推送"
    - "直接修改 ~/.cline/rules/ 现有非受管文件"
    - "网关侧代码篡改"
  outputs:
    - "scripts/distill_v5_kernel.py"
    - "scripts/dispatch_v5.sh"
    - "dist/bmad-core.md"
  acceptance_criteria:
    - "CRIT-01: 提纯后的 bmad-core.md 具备零外部相对路径外链依赖，完整保留 ana-solo 与 bmad-solo 核心纪律、不变量及背压门禁。"
    - "CRIT-02: 提纯资产通过 Token 软背压预算规划评估（目标 1,200 ~ 1,500 Tokens，超限时报警不截断）。"
    - "CRIT-03: 分发器支持加锁、原子重命名（Atomic Rename）、指纹核验与用户手动修改防踩踏保护。"
    - "CRIT-04: 严格践行'静态层是元规则宪法，search_codebase 等是运行时探针'的正交解耦原则。"
  supporting_evidence: [mechanical_verdict, supervisory_review]
  assumptions:
    - "Cline 宿主支持自动加载 ~/.cline/rules/*.md 作为全局系统规则（Tier 4 降级标准路径）。"
  limitations:
    - "本任务仅交付静态治理内核，动态上下文 In-Context Push 在宿主适配器完成实测前保持 BLOCKED。"
  downstream_use: "作为所有业务项目启动 Cline 时的全局基础行为约束"
kcp_verification:
  environment_ref: "Linux bash / Python 3.10+"
  checks:
    - check_id: KCP-01
      criterion_refs: [CRIT-01, CRIT-02, CRIT-04]
      required: true
      verification_type: config_syntax
      command: "python3 scripts/distill_v5_kernel.py --dry-run"
      command_status: AVAILABLE
      cwd: "."
      timeout_seconds: 30
      required_observations: [actual_exit, applicable_result]
      actual_receipt: "PASS (exit_code=0, estimated_tokens=1306, within_budget=True, digest=7835ef728155a5d9b9336b0f694d4a7440dd500358908979424a4ce926c2b75a)"
    - check_id: KCP-02
      criterion_refs: [CRIT-03]
      required: true
      verification_type: config_syntax
      command: "bash scripts/dispatch_v5.sh --test"
      command_status: AVAILABLE
      cwd: "."
      timeout_seconds: 30
      required_observations: [actual_exit, applicable_result]
      actual_receipt: "PASS (exit_code=0, preflight_pass, flock_acquired, atomic_rename_ready)"
sod_review:
  responsible_actor: "bmad-solo"
  supervisor_actor: "user"
  review_required: true
  minimum_independence: separate_actor
  review_ref: null
  authority_source_ref: "用户明确授权工程实施"
  approval_scope: contribution_acceptance_only
gate_status:
  authority_kind: platform
  authority_ref: null
  snapshot_contract_version: "1"
  snapshot_candidate_version: "1.0"
  cs: PASS
  sr: PASS
  accepted: true
  observed_at: "2026-11-16T06:42:40Z"
authorization:
  source_ref: "2026-11-16 用户指令：'同意: 静态层是元规则宪法，search_codebase 是运行时探针，两者正交互补；全局治理内核是 V5 的立足基石，必须实施。先固化到本次 adr+plan中以免历史回溯'"
  allowed_paths:
    - "scripts/distill_v5_kernel.py"
    - "scripts/dispatch_v5.sh"
    - "dist/"
    - "specs/tasks/"
    - "specs/governance/"
  allowed_operations: [read, write, execute_local_test]
  phase: "implementation_ready"
  promotion_allowed: false
