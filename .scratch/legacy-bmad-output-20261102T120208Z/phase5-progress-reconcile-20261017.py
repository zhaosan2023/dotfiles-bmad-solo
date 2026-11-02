"""本轮一次性受限对账；唯一进度仍为绑定计划中的任务清单。

只调用既有类型化单测、精确证据核验、刷新及完成原语。
行政恢复仅获准复用内部 _save_plan；不是已有产品恢复接口。
追加不可覆盖的操作回执，不写状态账本、不启动 Pi 或历史循环。
"""
from __future__ import annotations

import argparse
import ast
import copy
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bmralph-suite-v5/scripts"))
import bmad_execution as execution
import bmad_loop as loop
import bmad_plan_adapter as adapter
import bmad_state as state
from bmad_supervisor import SupervisorError, contained_path, save_receipt

PLAN = "_bmad-output/pending_implementation_plan.md"
ADR = "_bmad-output/adrs/ADR-20261012-bmad-solo-anti-bureaucracy-and-programmatic-guards.md"
PLAN_ID = "BMAD-ANTI-BUREAUCRACY-20261012-01"
OUT = "_bmad-output/verification/phase5-20261017"
OLD = ("P3-PLAN", "P3-BACKEND", "P3-OFFLINE", "P4-BUDGET", "P4-BATCH", "P4-ISOLATION")
DRIVER = "P5-PI-DRIVER"
HEADLESS = "P5-PI-HEADLESS"
GROUPS = {
    "P3-PLAN": ("P3-PLAN",),
    "P3-BACKEND": ("P3-BACKEND", "P3-OFFLINE", "P4-BUDGET"),
    "P4-BATCH": ("P4-BATCH",),
    "P4-ISOLATION": ("P4-ISOLATION",),
    DRIVER: (DRIVER,),
}
PATTERNS = {"P3-PLAN": ("test_loop_guards.py", 18),
            "P3-BACKEND": ("test_agent_backend.py", 17),
            "P4-BATCH": ("test_batch_guards.py", 12),
            "P4-ISOLATION": ("test_batch_isolation.py", 7),
            DRIVER: ("test_pi_backend.py", 31)}
FROZEN = ["bmralph-suite-v5/tests", "bmad-suite-v4", "scripts/asset_safety.py"]
FROZEN += ["bmralph-suite-v5/scripts/" + name for name in (
    "bmad_loop.py", "bmad-loop.py", "bmad_task_run.py", "bmad_run_copy.py",
    "bmad_state.py", "bmad_plan_adapter.py", "bmad_execution.py",
    "bmad_context.py", "bmad_context_inputs.py", "bmad_environment.py",
    "bmad_supervisor.py", "bmad_test_runner.py", "bmad_suite_source.py",
    "bmad_suite_lease.py", "bmad-exec.py")]


def require(condition, message):
    if not condition:
        raise SupervisorError(message)


def git(*arguments):
    process = subprocess.run(["git", *arguments], cwd=ROOT, stdin=subprocess.DEVNULL,
                             capture_output=True, text=True, timeout=15)
    require(process.returncode == 0, "只读 Git 核验失败：" + " ".join(arguments[:2]))
    return process.stdout


def load():
    data, _, identity = state.load_plan(ROOT, PLAN)
    require(data["plan_id"] == PLAN_ID, "绑定计划身份变化")
    require(set(state.validate_contract(data)) == set(OLD + (DRIVER, HEADLESS)),
            "任务集合变化，停止对账")
    text = contained_path(ROOT, PLAN).read_text()
    require('adr_file: "' + ADR + '"' in text.split("---", 2)[1], "关联 ADR 变化")
    require("- Status: PROPOSED" in contained_path(ROOT, ADR).read_text().splitlines(),
            "ADR 不再为 PROPOSED")
    return data, state.validate_contract(data), identity


def cleanup():
    current = loop.status(ROOT)
    require(current.get("writer_active") is False and current.get("cleanup_ok") is True,
            "活动写入者或前序清理未知；不恢复旧进程")
    require(current["status"] in {"BLOCKED", "SUSPENDED", "COMPLETED"}, "前序循环未终结")
    terminal = loop.read_record(ROOT, current["final_receipt"])
    for key in ("run_id", "status", "cleanup_ok", "finished_at", "final_receipt"):
        require(terminal.get(key) == current.get(key), "前序最终回执与查询不一致")
    require(bool(terminal.get("finished_at")), "前序最终退出证据缺失")
    return {"final_receipt": current["final_receipt"], "cleanup_ok": True,
            "writer_active": False, "historical_status": current["status"]}


def contracts(tasks):
    for group, members in GROUPS.items():
        verification = tasks[group]["verification"]
        require(all(tasks[key]["verification"] == verification for key in members),
                "共享回执组的验证对象不完全一致")
        pattern, minimum = PATTERNS[group]
        require(verification["operation"] == "unit-test"
                and verification["environment_file"] == ".bmad-control/phase2-environment.json"
                and verification["directory"] == "bmralph-suite-v5/tests"
                and verification["pattern"] == pattern
                and verification["minimum_tests"] >= minimum, "验证落点或测试下限变化")
        tree = ast.parse(contained_path(ROOT, verification["directory"] + "/" + pattern).read_bytes())
        identifiers = [Path(pattern).stem + "." + node.name + "." + method.name
                       for node in tree.body if isinstance(node, ast.ClassDef)
                       for method in node.body if isinstance(method, ast.FunctionDef)
                       and method.name.startswith("test_")]
        require(len(identifiers) >= verification["minimum_tests"], "当前测试数量低于契约下限")
        require(set(verification["required_tests"]) <= set(identifiers), "必需测试标识缺失")
        if group == DRIVER:
            require(set(verification["required_tests"]) == set(identifiers),
                    "Pi 当前反例没有全部绑定为必需项")
    return {key: copy.deepcopy(tasks[key]["verification"]) for key in OLD + (DRIVER, HEADLESS)}


def snapshot(tasks):
    inputs = tuple(dict.fromkeys(item for key in OLD + (DRIVER,)
                                for item in tasks[key]["verification"]["inputs"]))
    return execution.collect_evidence(ROOT, "bmralph-suite-v5/tests", inputs)


def guard(previous, *, held=False):
    data, tasks, identity = load()
    require(previous["status"] == "PASS" and previous["plan_id"] == PLAN_ID,
            "前序行政操作没有成功回执")
    require(identity == previous["plan_identity"], "源计划并发变化，保留外部修改")
    require(execution.environment.fingerprint(contained_path(ROOT, ADR)) == previous["adr_identity"],
            "关联 ADR 并发变化")
    require(git("rev-parse", "HEAD").strip() == previous["head"], "HEAD 变化")
    git("diff", "HEAD", "--exit-code", "--", *FROZEN)
    require(contracts(tasks) == previous["contracts"], "验证契约变化")
    require(snapshot(tasks) == previous["assets"], "实现、测试集合或控制器变化；须重验受影响证据")
    if not held:
        cleanup()
    require(tasks[HEADLESS]["status"] == "SUSPENDED" and tasks[HEADLESS]["verdict_file"] is None,
            "HEADLESS 暂停边界变化")
    return data, tasks, identity


def check_completed(tasks):
    return {key: state.completed_evidence(ROOT, task)["status"]
            for key, task in tasks.items() if task["status"] == "COMPLETED"}


def unchanged(before, after, allowed):
    require(before["plan_id"] == after["plan_id"] and before["schema_version"] == after["schema_version"],
            "保存后计划身份变化")
    for first, last in zip(before["tasks"], after["tasks"]):
        expected = copy.deepcopy(first)
        expected.update(allowed.get(first["task_id"], {}))
        require(last == expected, "保存后出现未授权任务变更")
    require(len(before["tasks"]) == len(after["tasks"]), "保存后任务集合变化")


def evidence_candidate(tasks, key, relative):
    require(relative.startswith(OUT + "/") and relative.endswith(".verdict.json"),
            "只接受本轮目录中原样追加的单测回执")
    candidate = copy.deepcopy(tasks[key])
    candidate.update(status="COMPLETED", verdict_file=relative)
    return state.completed_evidence(ROOT, candidate)


def record(stage, base, extra):
    output = dict(base, stage=stage, status="PASS", plan_id=PLAN_ID,
                  plan_identity=load()[2], **extra)
    relative = OUT + "/reconcile-" + uuid.uuid4().hex + ".json"
    save_receipt(contained_path(ROOT, relative), output)
    summary = {"stage": stage, "status": "PASS", "operation_receipt": relative,
               "plan_identity": output["plan_identity"], **extra}
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True), flush=True)
    return relative


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("operation", choices=("bind", "verify", "refresh", "resume", "complete", "final"))
    parser.add_argument("--previous")
    parser.add_argument("--group", choices=tuple(GROUPS))
    parser.add_argument("--verdict", action="append", default=[])
    args = parser.parse_args()
    require(Path.cwd().resolve() == ROOT, "工作目录不是获准工作区")
    if args.operation == "bind":
        require(not args.previous and not args.group and not args.verdict, "接管参数越界")
        data, tasks, identity = load()
        require(all(tasks[key]["status"] == "COMPLETED" for key in OLD), "原完成项状态变化")
        require(all(tasks[key]["status"] == "SUSPENDED" and tasks[key]["verdict_file"] is None
                    for key in (DRIVER, HEADLESS)), "窄恢复的源状态前提变化")
        head = git("rev-parse", "HEAD").strip()
        require(head.startswith("11483cf"), "接管 HEAD 与实测断点不一致")
        git("diff", "HEAD", "--exit-code", "--", *FROZEN)
        base = {"head": head, "adr_identity": execution.environment.fingerprint(contained_path(ROOT, ADR)),
                "contracts": contracts(tasks), "assets": snapshot(tasks)}
        findings = {}
        candidates = sorted(contained_path(ROOT, OUT).glob("*.verdict.json"))
        for key in OLD + (DRIVER,):
            matches = []
            for path in candidates:
                try:
                    relative = path.relative_to(ROOT).as_posix()
                    evidence_candidate(tasks, key, relative)
                    matches.append(relative)
                except (OSError, ValueError, ImportError, KeyError, TypeError):
                    pass
            try:
                state.completed_evidence(ROOT, tasks[key])
                old_status = "PASS"
            except (OSError, ValueError, ImportError, KeyError, TypeError) as exc:
                old_status = "BLOCKED: " + str(exc)
            findings[key] = {"source_evidence": old_status, "matching_current_candidates": matches}
        require(load()[2] == identity, "接管期间计划变化")
        record("bind", base, {"cleanup": cleanup(), "candidates": findings,
                              "tests_reviewed": "仅本地协议拦截、隔离 Python 驱动及同组清理；不启动真实 Pi"})
        return
    require(bool(args.previous), "缺少当前链路的成功操作回执")
    previous, _ = execution.read_receipt(ROOT, args.previous)
    base = {key: previous[key] for key in ("head", "adr_identity", "contracts", "assets")}
    data, tasks, identity = guard(previous)
    if args.operation == "verify":
        require(args.group in GROUPS and not args.verdict, "验证组参数缺失或越界")
        if args.group == DRIVER:
            require(previous["stage"] == "resume" and tasks[DRIVER]["status"] == "PENDING"
                    and tasks[DRIVER]["verdict_file"] is None, "Pi 本地验证须先受限恢复")
            check_completed(tasks)
            projection = adapter.query(workspace=ROOT, plan_file=PLAN)
            require(projection["status"] == "READY" and DRIVER in projection["ready_tasks"],
                    "Pi 本地目标依赖未就绪")
        else:
            require(previous["stage"] == "bind", "旧任务验证必须绑定本轮稳定资产接管回执")
        verification = tasks[args.group]["verification"]
        verdict = execution.unit_test(workspace=ROOT,
            environment_file=verification["environment_file"], directory=verification["directory"],
            pattern=verification["pattern"], minimum_tests=verification["minimum_tests"],
            required_tests=tuple(verification["required_tests"]), inputs=tuple(verification["inputs"]),
            runtime_directory=OUT)
        require(verdict["status"] == "PASS", "必需单测失败：" + verdict["reason"]
                + "；保留回执 " + verdict["verdict_path"])
        guard(previous)
        for key in GROUPS[args.group]:
            evidence_candidate(tasks, key, verdict["verdict_path"])
        record("verify:" + args.group, base,
               {"verdict_file": verdict["verdict_path"], "tests_run": verdict["result"]["tests_run"],
                "exact_candidates": list(GROUPS[args.group])})
        return
    require(not args.group, "行政操作不接受验证组参数")
    if args.operation == "refresh":
        require(previous["stage"] == "bind" and len(args.verdict) == 4, "旧完成项须一次刷新四组")
        groups = tuple(key for key in GROUPS if key != DRIVER)
        files = {key: relative for group, relative in zip(groups, args.verdict) for key in GROUPS[group]}
        with loop.writer_lease(ROOT):
            data, tasks, identity = guard(previous, held=True)
            require(all(tasks[key]["status"] == "COMPLETED" for key in OLD), "刷新目标不再是原完成项")
            for key, relative in files.items():
                evidence_candidate(tasks, key, relative)
            receipt = adapter.refresh_completed(workspace=ROOT, plan_file=PLAN,
                                               verdict_files=files, expected_identity=identity)
            saved, after, _ = load()
            unchanged(data, saved, {key: {"verdict_file": relative} for key, relative in files.items()})
            checked = check_completed(after)
        record("refresh", base, {"adapter_result": receipt, "completed_evidence": checked})
    elif args.operation == "resume":
        require(previous["stage"] == "refresh" and not args.verdict, "窄恢复须紧随全量旧证据刷新")
        with loop.writer_lease(ROOT):
            data, tasks, identity = guard(previous, held=True)
            checked = check_completed(tasks)
            require(set(checked) == set(OLD), "窄恢复前全部六项完成证据尚未有效")
            require(tasks[DRIVER]["status"] == "SUSPENDED" and tasks[DRIVER]["verdict_file"] is None,
                    "窄恢复仅接受确切 SUSPENDED/空回执源状态")
            updated = copy.deepcopy(data)
            next(task for task in updated["tasks"] if task["task_id"] == DRIVER)["status"] = "PENDING"
            unchanged(data, updated, {DRIVER: {"status": "PENDING"}})
            # 内部保存接口仅承担既有版本/证据/原子保存；恢复资格由本受限例程核验。
            adapter._save_plan(ROOT, PLAN, identity, updated,
                               tuple(task for task in updated["tasks"] if task["status"] == "COMPLETED"))
            saved, _, _ = load()
            require(saved == updated, "窄恢复保存后不一致；不恢复旧文件")
            projection = adapter.query(workspace=ROOT, plan_file=PLAN)
            require(projection["status"] == "READY" and projection["ready_tasks"] == [DRIVER],
                    "窄恢复后本地任务未依赖就绪")
        record("resume", base, {"task_id": DRIVER, "source_status": "SUSPENDED",
                                "saved_status": "PENDING", "verdict_file": None,
                                "ready_tasks": projection["ready_tasks"], "real_runtime_authorized": False})
    elif args.operation == "complete":
        require(previous["stage"] in {"resume", "verify:" + DRIVER} and len(args.verdict) == 1,
                "本地完成须有窄恢复及一份精确协议证据")
        relative = args.verdict[0]
        with loop.writer_lease(ROOT):
            data, tasks, identity = guard(previous, held=True)
            check_completed(tasks)
            evidence_candidate(tasks, DRIVER, relative)
            receipt = adapter.complete(workspace=ROOT, plan_file=PLAN, task_id=DRIVER,
                                       verdict_file=relative, expected_identity=identity)
            saved, after, _ = load()
            unchanged(data, saved, {DRIVER: {"status": "COMPLETED", "verdict_file": relative}})
            checked = check_completed(after)
        record("complete", base, {"adapter_result": receipt, "completed_evidence": checked,
                                  "scope": "仅 P5-PI-DRIVER 本地协议及委托原语交付"})
    else:
        require(previous["stage"] == "complete" and not args.verdict, "最终复核缺少完成行政回执")
        checked = check_completed(tasks)
        require(set(checked) == set(OLD + (DRIVER,)), "本轮七项有效完成证据不完整")
        projection = adapter.query(workspace=ROOT, plan_file=PLAN)
        require(projection["status"] == "SUSPENDED" and projection["ready_tasks"] == []
                and projection["unfinished_count"] == 1, "最终唯一清单投影不符合阶段边界")
        guard(previous)
        record("final", base, {"completed_evidence": checked, "projection": projection,
                               "cleanup": cleanup(), "worktree": git("status", "--short"),
                               "real_pi_runs": 0, "adr_status": "PROPOSED", "plan_archived": False})


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, ImportError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc),
                          "boundary": "未推进后续登记；保留全部修改和已有回执，不回滚、不启动真实 Pi"},
                         ensure_ascii=False), flush=True)
        sys.exit(1)
