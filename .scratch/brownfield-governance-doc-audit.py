"""仅检查本任务四份文档；不执行样本、计划、业务测试或宿主操作。"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "blueprint": "docs/blueprint.md",
    "procedure": "bmad-suite-v4/skills/bmad/references/procedures/brownfield-distill-governance.md",
    "rule": "bmad-suite-v4/rules/bmad-core.md",
    "skill": "bmad-suite-v4/skills/bmad/SKILL.md",
}
errors = []
checks = 0
link_count = 0


def check(condition, label):
    global checks
    checks += 1
    if not condition:
        errors.append(label)


texts = {}
for name, relative in FILES.items():
    path = ROOT / relative
    check(path.is_file(), f"缺少文档：{relative}")
    if not path.is_file():
        continue
    text = path.read_text(encoding="utf-8")
    texts[name] = text
    lines = text.splitlines()
    check(text.endswith("\n"), f"缺少末尾换行：{relative}")
    check(all(line == line.rstrip() for line in lines), f"尾随空白：{relative}")
    check(not any(re.match(r"^(<<<<<<<|=======|>>>>>>>)", line) for line in lines),
          f"冲突标记：{relative}")
    check(sum(line.startswith("```") for line in lines) % 2 == 0,
          f"围栏不成对：{relative}")
    for destination in re.findall(r"\]\(([^)]+)\)", text):
        if "://" in destination or destination.startswith("#"):
            continue
        link_count += 1
        match = re.fullmatch(r"(.+?)(?::([1-9][0-9]*))?", destination)
        if match is None:
            check(False, f"链接格式错误：{relative}: {destination}")
            continue
        target = (path.parent / match.group(1)).resolve()
        check(target.is_relative_to(ROOT), f"链接越出工作区：{relative}: {destination}")
        check(target.exists(), f"链接目标缺失：{relative}: {destination}")
        if match.group(2):
            check(target.is_file(), f"行号目标不是文件：{destination}")
            if target.is_file():
                target_lines = target.read_text(encoding="utf-8").splitlines()
                line = int(match.group(2))
                check(line <= len(target_lines), f"行号越界：{destination}")
                if line <= len(target_lines):
                    check(bool(target_lines[line - 1].strip()), f"行号指向空行：{destination}")

blueprint = texts.get("blueprint", "")
procedure = texts.get("procedure", "")
for component in range(1, 9):
    check(len(re.findall(rf"^\| C{component} ", blueprint, re.MULTILINE)) == 1,
          f"八组件映射缺失或重复：C{component}")
for token in ("## 3. 棕地", "## 5. 宪法底座即 Base 类", "AGENTS.md", "specs/governance/",
              "specs/tasks/_active.md", "docs/adrs/", "docs/analysis/", "业务流 DAG"):
    check(token in blueprint, f"蓝图缺少要求：{token}")
check("specs/_pending_plan.md" not in blueprint, "蓝图仍使用旧棕地产物槽位")
for step in range(1, 6):
    check(len(re.findall(rf"^### Step {step}：", procedure, re.MULTILINE)) == 1,
          f"规程步骤缺失或重复：{step}")
for token in ("## 前置条件", "## 质量与安全门禁", "### CS：", "### SR：", "### 回滚与发布保护",
              "solo-distill-mcp", "少于 150 行", "三者覆盖率均为 100%", "Warning", "消费者独立核对",
              "separate_actor", "SR 保持 UNKNOWN/BLOCKED", "python-mvp-20261027T0344Z"):
    check(token in procedure, f"规程缺少要求：{token}")
check("scenario: ops\n" in procedure, "规程场景不为 ops")
check("status: PROPOSED\n" in procedure and "runtime_verified: false\n" in procedure,
      "规程缺少提案与未运行边界")
for field in ("active_task_id", "instance_id", "task_ref", "contract_version", "authority_ref"):
    check(f"{field}: null" in procedure, f"空闲模板缺少空值：{field}")
for name in ("rule", "skill"):
    text = texts.get(name, "")
    for trigger in ("初始化目录", "棕地治理", "init-governance"):
        check(trigger in text, f"触发词未注册：{name}: {trigger}")
    check("brownfield-distill-governance.md" in text, f"路由未引用规程：{name}")
    check("ops" in text and "不启动" in text, f"缺少短路场景或防误触边界：{name}")
    check("不重置既有" in text, f"缺少既有焦点保护：{name}")
for module in ("00-governance-index.md", "01-plan-act-role-embedding.md", "02-task-unit-schema.md",
               "03-dataflow-contracts.md", "04-kcp-sod-gates.md", "05-host-adaptation.md"):
    check(module in procedure, f"缺少治理模块映射：{module}")

print(f"文档结构与本地引用检查：{len(texts)} 份文档，{link_count} 个链接，{checks} 项断言。")
print("边界：不证明语义正确、独立 SR、引擎运行、宿主加载或程序防篡改。")
if errors:
    for error in errors:
        print(f"FAIL: {error}", file=sys.stderr)
    sys.exit(1)
print("PASS：全部静态断言满足；未执行任何业务测试或真实棕地样本。")
