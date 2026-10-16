#!/usr/bin/env python3
"""V5 类型化入口：环境、相关单测、证据查询与任务清单只读投影。

当前验证仅覆盖 native-python；不安装依赖、不接受任意 Shell 命令。
状态投影须明确采用类型化任务契约，不自动迁移活动计划或平台进度；
不提供尚未实现的配置、竞态或容器操作。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import bmad_context as context
import bmad_context_inputs as context_inputs
import bmad_environment as environment
import bmad_execution as execution
import bmad_state as state
from bmad_supervisor import SupervisorError, bounded_log, contained_path
from bmad_test_runner import positive_integer


OUTPUT_BYTES = 16384
REASON_BYTES = 2048


def short_text(value: str, limit: int) -> str:
    encoded = value.encode("utf-8")
    if len(encoded) <= limit:
        return value
    marker = " [TRUNCATED]"
    return encoded[:limit - len(marker)].decode("utf-8", errors="ignore") + marker


def emit(data: dict) -> None:
    """输出有界摘要，完整证据保留在任务工作区；不隐藏失败状态。"""
    text = json.dumps(data, ensure_ascii=False, sort_keys=True)
    if len(text.encode("utf-8")) + 1 > OUTPUT_BYTES:
        data = {
            "operation": data.get("operation"),
            "status": data.get("status", "BLOCKED"),
            "reason": short_text(str(data.get("reason", "")), REASON_BYTES),
            "process_receipt": data.get("process_receipt"),
            "verdict_path": data.get("verdict_path"),
            "output_truncated": True,
            "evidence_boundary": "输出超限；完整证据按回执定位读取，截断不改变验证裁决",
        }
        text = json.dumps(data, ensure_ascii=False, sort_keys=True)
    if len(text.encode("utf-8")) + 1 > OUTPUT_BYTES:
        # 路径等元数据本身超限时不能继续输出无界结果。
        text = json.dumps({
            "status": "BLOCKED", "output_truncated": True,
            "reason": "必要结果元数据超过输出预算；未输出无界内容",
        }, ensure_ascii=False)
        print(text, flush=True)
        raise SupervisorError("必要结果元数据超过输出预算")
    print(text, flush=True)


def common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workspace", required=True, type=Path,
                        help="授权任务工作区，独立于套件分发源")
    parser.add_argument("--environment-file", required=True,
                        help="工作区内明确的 L0 环境登记文件")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = root.add_subparsers(dest="operation", required=True)

    registration = commands.add_parser(
        "register-env", help="显式登记已准备环境；不安装或覆盖登记",
        allow_abbrev=False,
    )
    common_arguments(registration)
    registration.add_argument("--backend", required=True,
                              choices=(environment.BACKEND,))
    registration.add_argument("--python", required=True,
                              help="明确选择现有解释器")
    registration.add_argument("--dependency", action="append", default=[])
    registration.add_argument("--executable", action="append", default=[])

    check = commands.add_parser(
        "check-env", help="只读复核登记环境；缺依赖即阻塞",
        allow_abbrev=False,
    )
    common_arguments(check)

    tests = commands.add_parser(
        "unit-test", help="运行明确选中的相关单测并生成独立验收回执",
        allow_abbrev=False,
    )
    common_arguments(tests)
    tests.add_argument("--directory", required=True)
    tests.add_argument("--pattern", required=True)
    tests.add_argument("--minimum-tests", type=positive_integer, default=1)
    tests.add_argument("--required-test", action="append", default=[])
    tests.add_argument("--input", action="append", default=[],
                       help="需要覆盖的显式实现文件；未声明导入不在保证范围")
    tests.add_argument("--runtime-directory", default=".bmad-runtime",
                        help="工作区内日志和回执目录，不得位于测试目录或套件源")

    evidence = commands.add_parser(
        "check-evidence", help="查询已保存证据是否仍适用；不重跑业务或保存状态",
        allow_abbrev=False,
    )
    evidence.add_argument("--workspace", required=True, type=Path,
                          help="原验证对应的授权任务工作区")
    evidence.add_argument("--verdict-file", required=True,
                          help="工作区内已有单测验收回执；环境定位从回执核验")

    projection = commands.add_parser(
        "render-state", help="类型化计划任务的只读有界投影；不迁移或保存进度",
        allow_abbrev=False,
    )
    projection.add_argument("--workspace", required=True, type=Path)
    projection.add_argument("--plan-file", required=True,
                            help="明确采用类型化任务清单的计划相对路径")
    projection.add_argument("--maximum-lines", type=positive_integer,
                            default=state.MAX_VIEW_LINES)
    projection.add_argument("--maximum-bytes", type=positive_integer,
                            default=state.MAX_VIEW_BYTES)
    assembly = commands.add_parser(
        "assemble-input", help="只读组装当前就绪任务与明确源码；不启动 Agent",
        allow_abbrev=False,
    )
    assembly.add_argument("--workspace", required=True, type=Path)
    assembly.add_argument("--plan-file", required=True)
    assembly.add_argument("--request-file", required=True,
                          help="工作区内明确输入请求；不接受请求伪造状态或验证契约")
    assembly.add_argument("--maximum-bytes", type=positive_integer,
                          default=context.DEFAULT_STARTUP_BYTES)
    return root


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.operation == "assemble-input":
            assembled = context_inputs.assemble_plan_input(
                workspace=args.workspace, plan_file=args.plan_file,
                request_file=args.request_file,
                maximum_bytes=args.maximum_bytes,
            )
            # CLI 的 JSON 外层和转义也受输出预算约束；不得裁掉必要输入。
            encoded = context.encode_object(assembled)
            if len(encoded.encode("utf-8")) > OUTPUT_BYTES:
                emit({
                    "operation": args.operation, "status": "BLOCKED",
                    "reason": "完整启动输入及 CLI 转义元数据超过输出预算；未截断必要输入",
                    "plan_file": args.plan_file, "request_file": args.request_file,
                    "business_reexecuted": False, "state_saved": False,
                    "evidence_boundary": "未输出部分启动输入，不启动 Agent；模块预算不替代 CLI 输出预算",
                })
                return 1
            print(encoded, end="", flush=True)
            return 0
        if args.operation == "register-env":
            registered = environment.register(
                args.workspace, args.environment_file, args.python,
                tuple(args.dependency), tuple(args.executable),
            )
            emit({
                "operation": args.operation, "status": "PASS",
                "environment_file": args.environment_file,
                "backend": registered["backend"],
                "installation_count": 0,
                "evidence_boundary": registered["evidence_boundary"],
            })
            return 0
        if args.operation == "check-env":
            checked = environment.check(args.workspace, args.environment_file)
            emit({
                "operation": args.operation, "status": checked["status"],
                "environment_file": args.environment_file,
                "backend": checked["backend"],
                "installation_count": checked["installation_count"],
                "evidence_boundary": checked["evidence_boundary"],
            })
            return 0
        if args.operation == "render-state":
            projected = state.render_state(
                workspace=args.workspace, plan_file=args.plan_file,
                maximum_lines=args.maximum_lines,
                maximum_bytes=args.maximum_bytes,
            )
            if "reason" in projected:
                projected["reason"] = short_text(projected["reason"], REASON_BYTES)
            # JSON 转义与元数据也占输出预算；不能静默截掉任务视图。
            encoded = json.dumps(projected, ensure_ascii=False, sort_keys=True)
            if len(encoded.encode("utf-8")) + 1 > OUTPUT_BYTES:
                emit({
                    "operation": args.operation, "status": "BLOCKED",
                    "reason": "完整状态及必要元数据超过输出预算；未截断或丢弃未完成事项",
                    "business_reexecuted": False, "state_saved": False,
                })
                return 1
            emit(projected)
            return 1 if projected["status"] == "BLOCKED" else 0
        if args.operation == "check-evidence":
            checked = execution.check_evidence(
                workspace=args.workspace, verdict_file=args.verdict_file,
            )
            checked["reason"] = short_text(checked["reason"], REASON_BYTES)
            emit(checked)
            return 0 if checked["status"] == "PASS" else 1
        verdict = execution.unit_test(
            workspace=args.workspace, environment_file=args.environment_file,
            directory=args.directory, pattern=args.pattern,
            minimum_tests=args.minimum_tests,
            required_tests=tuple(args.required_test), inputs=tuple(args.input),
            runtime_directory=args.runtime_directory,
        )
        result = verdict["result"]
        output = {
            "operation": args.operation, "status": verdict["status"],
            "reason": short_text(verdict["reason"], REASON_BYTES),
            "process_receipt": verdict["process_receipt"],
            "verdict_path": verdict["verdict_path"],
            "tests_run": result["tests_run"] if result is not None else None,
            "evidence_boundary": verdict["evidence_boundary"],
        }
        # 直接从保留日志提取摘要，不把日志读取成功当成验证通过。
        receipt = contained_path(args.workspace, verdict["process_receipt"])
        summary = bounded_log(receipt.with_suffix(".log"), maximum_bytes=4096)
        output["log_summary"] = summary
        emit(output)
        return 0 if verdict["status"] == "PASS" else 1
    except (OSError, ValueError, ImportError) as exc:
        emit({
            "operation": args.operation, "status": "BLOCKED",
            "reason": short_text(str(exc), REASON_BYTES),
            "evidence_boundary": "操作未获完整必需证据；不推进任务，不隐式安装或回退",
        })
        return 1
    except KeyboardInterrupt:
        emit({"operation": args.operation, "status": "BLOCKED",
              "reason": "操作被中断；不得推进任务"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
