#!/bin/bash
# 仅由本次明确授权的 tmux 启动命令调用；创建本文件不启动任务。
set -u
set -o pipefail
umask 077
# 保留前序已隔离验证的终端脱离前缀；不忽略 TERM/INT。
trap '' HUP
if ! exec 9<> /dev/tty; then
    printf 'BLOCKED: cannot retain task pseudo-terminal\n' >&2
    exit 1
fi
exec < /dev/null

if [ "$(pwd -P)" != "/home/ecs-user/dotfiles-bmad-solo" ]; then
    printf 'BLOCKED: working directory mismatch\n' >&2
    exit 1
fi

if ! tmux set-option -p remain-on-exit on; then
    printf 'BLOCKED: cannot retain task pane\n' >&2
    exit 1
fi

LOG=".bmad-runtime/phase5-pi-detached-20261018-attempt3.log"
EXIT_RECEIPT=".bmad-runtime/phase5-pi-detached-20261018-attempt3.exit.json"
if [ ! -d .bmad-runtime ] || [ -e "$LOG" ] || [ -e "$EXIT_RECEIPT" ]; then
    printf 'BLOCKED: runtime directory missing or receipt already exists\n' >&2
    exit 1
fi
set -C
exec > "$LOG" 2>&1
printf 'Independent task wrapper started: %s\n' "$(date -u +%FT%TZ)"
printf 'Source commit: %s\n' "$(git rev-parse HEAD)"

# 控制器自身任务预算600秒；外层610秒加5秒强杀宽限只作失控兜底。
# 外层提前终止、超时或缺最终清理证据均不得报告任务通过。
timeout -k 5s 610s /usr/bin/python3.12 -B bmralph-suite-v5/scripts/bmad-loop.py start \
    --workspace . \
    --plan-file _bmad-output/pending_implementation_plan.md \
    --request-file _bmad-output/scratch/phase5-pi-headless-request-20261018.json \
    --backend pi-agent \
    --backend-config _bmad-output/scratch/phase5-pi-backend-20261018.json \
    --credential-file .bmad-private/credentials.env \
    --maximum-rounds 30 \
    --maximum-calls 30 \
    --maximum-model-requests 30 \
    --maximum-data-bytes 15000000 \
    --timeout-seconds 600 \
    --no-progress-rounds 6 \
    --startup-bytes 131072 \
    --output-bytes 131072 \
    --runtime-directory .bmad-runtime \
    --save-progress
code=$?
printf '\nIndependent task wrapper exited: %s, code=%s\n' "$(date -u +%FT%TZ)" "$code"
printf '{"operation":"detached-wrapper-exit","returncode":%s,"finished_at":"%s","evidence_boundary":"Wrapper exit only; business and cleanup verdict remain in controller receipt"}\n' \
    "$code" "$(date -u +%FT%TZ)" > "$EXIT_RECEIPT"
receipt_code=$?
if [ "$receipt_code" -ne 0 ]; then
    printf 'BLOCKED: wrapper exit receipt could not be saved\n' >&2
    exit 1
fi
exit "$code"
