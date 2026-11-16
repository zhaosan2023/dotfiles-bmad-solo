---
schema_version: "1.0-draft"
task_id: "TU-20261116-V5-DYNAMIC-ASSEMBLER"
instance_id: "inst-20261116-v5-dynamic-assembler-01"
contract_version: "1"
candidate_version: "1.0"
status: COMPLETED
session_id: "dcafc95e-1444-4582-8ca2-3b69a0cf8a2c"
scenario: structural
impact_tier: M
parent_objective:
  objective_id: "OBJ-20261116-BMAD-V5-DYNAMIC-PUSH"
  expected_result: "完成 BMAD-Solo V5 Phase 2 动态任务上下文装配器与工作区自动化注入管线，实现项目基线与单焦点任务契约的自动化组合与 Token 软背压控制"
  source_ref: "docs/adrs/ADR-20261116-bmad-v5-in-context-push-architecture.md"
inputs:
  - "specs/governance/v5-context-manifest.yaml"
  - "docs/adrs/ADR-20261116-bmad-v5-in-context-push-architecture.md"
  - "docs/project-context.md"
  - "specs/tasks/_active.md"
cs_specification:
  scope: "开发动态任务上下文装配器 scripts/assemble_v5_context.py 与单元测试 tests/test_assemble_v5_context.py，实现基于清单驱动的工作区基线提取、单焦点任务计划绑定、敏感信息过滤与工作区级注入 (.cline/rules/active-context.md)"
  excludes:
    - "直接修改其他项目的业务生产代码"
    - "未获授权的 Git 自动提交或推送"
    - "覆盖全局 ~/.cline/rules/bmad-core.md"
  outputs:
    - "scripts/assemble_v5_context.py"
    - "tests/test_assemble_v5_context.py"
    - ".cline/rules/active-context.md"
  acceptance_criteria:
    - "CRIT-01: 严格依据 specs/governance/v5-context-manifest.yaml 解析来源、规则与门禁。"
    - "CRIT-02: 准确读取 docs/project-context.md 提取架构基线；若缺失则报告降级警告（SUSPEND_AND_WARN_DEGRADED）。"
    - "CRIT-03: 严格通过 specs/tasks/_active.md 唯一锁定活动任务，校验 TU-*.md 存在性与 APPROVED/READY/IN_PROGRESS 状态；空闲时输出明确空闲标识，冲突时硬阻断。"
    - "CRIT-04: 执行 Token 软背压规划评估（动态上下文目标 800 ~ 1,200 Tokens，超限告警不截断）。"
    - "CRIT-05: 支持 --inject-workspace 模式，通过原子写方式安全注入到当前工作区 .cline/rules/active-context.md，供 Cline 热加载。"
  supporting_evidence: [mechanical_verdict, supervisory_review]
  assumptions:
    - "Cline 宿主支持叠加读取工作区级别的 .cline/rules/*.md 作为上下文规则。"
  limitations:
    - "动态上下文装配器专注于当前工作区上下文组装，不越权访问其他隔离项目。"
  downstream_use: "供 Cline 在打开具体项目时自动获得活动任务与基线上下文"
kcp_verification:
  environment_ref: "Linux bash / Python 3.10+"
  checks:
    - check_id: KCP-01
      criterion_refs: [CRIT-01, CRIT-02, CRIT-03, CRIT-04]
      required: true
      verification_type: unit_test
      command: "python3 -m unittest tests/test_assemble_v5_context.py"
      command_status: AVAILABLE
      cwd: "."
      timeout_seconds: 30
      required_observations: [actual_exit, applicable_result]
      actual_receipt: "PASS (Ran 9 tests in 0.057s, OK)"
    - check_id: KCP-02
      criterion_refs: [CRIT-05]
      required: true
      verification_type: config_syntax
      command: "python3 scripts/assemble_v5_context.py --inject-workspace --dry-run"
      command_status: AVAILABLE
      cwd: "."
      timeout_seconds: 30
      required_observations: [actual_exit, applicable_result]
      actual_receipt: "PASS (exit_code=0, injection_pass, target .cline/rules/active-context.md, estimated_tokens=1182)"
sod_review:
  responsible_actor: "bmad-solo"
  supervisor_actor: "user"
  review_required: true
  minimum_independence: separate_actor
  review_ref: null
  authority_source_ref: "用户指令：/bmad-solo 开始phase2,做好 背压测试+软门禁验收"
  approval_scope: contribution_acceptance_only
gate_status:
  authority_kind: platform
  authority_ref: null
  snapshot_contract_version: "1"
  snapshot_candidate_version: "1.0"
  cs: PASS
  sr: PASS
  accepted: true
  observed_at: "2026-11-16T08:03:59Z"
authorization:
  source_ref: "2026-11-16 用户指令：'/bmad-solo 开始phase2,做好 背压测试+软门禁验收'"
  allowed_paths:
    - "scripts/assemble_v5_context.py"
    - "tests/test_assemble_v5_context.py"
    - ".cline/rules/active-context.md"
    - "specs/tasks/"
  allowed_operations: [read, write, execute_local_test]
  phase: "implementation_active"
  promotion_allowed: false
