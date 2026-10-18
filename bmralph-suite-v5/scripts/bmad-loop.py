#!/usr/bin/env python3
"""任务期循环的启动、只读查询和同步安全停止；无后台调度器。"""
import argparse
import json
from pathlib import Path

import bmad_context as context
import bmad_loop as loop
import bmad_private_config as private_config
from bmad_supervisor import SupervisorError


def parser():
    root = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = root.add_subparsers(dest="operation", required=True)
    start = commands.add_parser("start", allow_abbrev=False)
    start.add_argument("--workspace", required=True, type=Path)
    start.add_argument("--plan-file", required=True)
    start.add_argument("--request-file", required=True)
    start.add_argument("--backend", required=True, choices=("local-verification", "roo-cli", "headless", "pi-agent"))
    start.add_argument("--backend-config", help="明确获准的无头驱动契约；缺实证时真实 Roo 失败关闭")
    start.add_argument("--credential-file",
                       help="启动时显式加载 .bmad-private 内的 0600 凭据文件；不执行 Shell")
    start.add_argument("--maximum-rounds", required=True, type=int)
    start.add_argument("--timeout-seconds", required=True, type=float)
    start.add_argument("--no-progress-rounds", required=True, type=int)
    start.add_argument("--retry-delay", type=float, default=0.1)
    start.add_argument("--startup-bytes", type=int, default=context.DEFAULT_STARTUP_BYTES)
    start.add_argument("--output-bytes", type=int, default=context.MAX_CUMULATIVE_TOOL_BYTES)
    start.add_argument("--runtime-directory", default=".bmad-runtime")
    start.add_argument("--save-progress", action="store_true",
                       help="明确授权程序按真实证据写回唯一计划任务清单")
    start.add_argument("--batch-file", help="显式获准任务集合及独立输入；须同时授权进度写回")
    start.add_argument("--maximum-calls", type=int,
                       help="外层驱动调用预算；不宣称内部模型调用或费用计量")
    start.add_argument("--maximum-model-requests", type=int,
                       help="Pi 到获准网关的实际 HTTP 请求尝试上限，最多 30；失败不返还")
    start.add_argument("--maximum-data-bytes", type=int,
                       help="Pi 到网关的请求与响应正文累计上限，最多 15000000 字节")
    start.add_argument("--deployment-root", type=Path,
                       help="本阶段仅允许授权工作区内的合成部署根，不写真实宿主状态")
    start.add_argument("--run-copy-file",
                       help="明确的隔离运行副本绑定回执；入口必须来自该副本")
    for name in ("status", "stop"):
        command = commands.add_parser(name, allow_abbrev=False)
        command.add_argument("--workspace", required=True, type=Path)
        if name == "stop":
            command.add_argument("--wait-seconds", type=float, default=15)
        else:
            command.add_argument("--plan-file", help="只读查询显式计划就绪任务及短状态卡")
    return root


def emit(record):
    payload = context.encode_object(record)
    exceeded = len(payload.encode("utf-8")) > 16384
    if exceeded:
        locator = record.get("final_receipt")
        if not isinstance(locator, str) or len(locator.encode("utf-8")) > 2048:
            locator = None
        payload = context.encode_object({
            "status": "BLOCKED", "reason": "完整结果超过 CLI 输出预算；未输出部分状态卡，完整回执保留",
            "final_receipt": locator, "output_truncated": True,
        })
    print(payload, end="", flush=True)
    return not exceeded


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.operation == "start":
            if args.credential_file is not None and args.backend == "local-verification":
                raise SupervisorError("本地验证不加载模型凭据；请移除私有凭据参数")
            values = {key: value for key, value in vars(args).items()
                      if key not in {"operation", "credential_file"}}
            spec = loop.LoopSpec(**values)
            spec.validate()
            with private_config.credential_environment(args.workspace, args.credential_file):
                record = loop.start(spec)
            code = 0 if record["status"] == "COMPLETED" else 1
        elif args.operation == "stop":
            record = loop.stop(args.workspace, args.wait_seconds)
            code = 0
        else:
            record = loop.status(args.workspace, args.plan_file)
            code = 1 if record["status"] == "BLOCKED" else 0
        emitted = emit(record)
        return code if emitted else 1
    except (OSError, ValueError, ImportError, KeyError, TypeError) as exc:
        emit({"operation": args.operation, "status": "BLOCKED", "reason": str(exc)[:512],
              "evidence_boundary": loop.BOUNDARY})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
