#!/usr/bin/env python3
"""任务期循环的启动、只读查询和同步安全停止；无后台调度器。"""
import argparse
import json
from pathlib import Path

import bmad_context as context
import bmad_loop as loop
from bmad_supervisor import SupervisorError


def parser():
    root = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = root.add_subparsers(dest="operation", required=True)
    start = commands.add_parser("start", allow_abbrev=False)
    start.add_argument("--workspace", required=True, type=Path)
    start.add_argument("--plan-file", required=True)
    start.add_argument("--request-file", required=True)
    start.add_argument("--backend", required=True, choices=("local-verification",))
    start.add_argument("--maximum-rounds", required=True, type=int)
    start.add_argument("--timeout-seconds", required=True, type=float)
    start.add_argument("--no-progress-rounds", required=True, type=int)
    start.add_argument("--retry-delay", type=float, default=0.1)
    start.add_argument("--startup-bytes", type=int, default=context.DEFAULT_STARTUP_BYTES)
    start.add_argument("--output-bytes", type=int, default=context.MAX_CUMULATIVE_TOOL_BYTES)
    start.add_argument("--runtime-directory", default=".bmad-runtime")
    for name in ("status", "stop"):
        command = commands.add_parser(name, allow_abbrev=False)
        command.add_argument("--workspace", required=True, type=Path)
        if name == "stop":
            command.add_argument("--wait-seconds", type=float, default=15)
    return root


def emit(record):
    payload = context.encode_object(record)
    if len(payload.encode("utf-8")) > 16384:
        payload = json.dumps({"status": "BLOCKED", "reason": "循环查询结果超过输出预算；完整回执保留"}) + "\n"
    print(payload, end="", flush=True)


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.operation == "start":
            record = loop.start(loop.LoopSpec(**{key: value for key, value in vars(args).items() if key != "operation"}))
            code = 0 if record["status"] == "COMPLETED" else 1
        elif args.operation == "stop":
            record = loop.stop(args.workspace, args.wait_seconds)
            code = 0
        else:
            record = loop.status(args.workspace)
            code = 1 if record["status"] == "BLOCKED" else 0
        emit(record)
        return code
    except (OSError, ValueError, ImportError, KeyError, TypeError) as exc:
        emit({"operation": args.operation, "status": "BLOCKED", "reason": str(exc)[:512],
              "evidence_boundary": loop.BOUNDARY})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
