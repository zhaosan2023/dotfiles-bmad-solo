#!/usr/bin/env bash
# BMAD-Solo V5 受管分发器 (scripts/dispatch_v5.sh)
#
# 架构契约遵从：
# 1. ADR-20261116 决策五：受管分发事务、文件加锁与原子替换 (Atomic Rename)；
# 2. 用户修改防护：若目标文件已被用户手动修改，拒绝静默覆盖；
# 3. 提供 --test (预检)、--status (状态对账)、--rollback (安全回滚) 完整生命周期指令。

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_FILE="${WORKSPACE}/dist/bmad-core.md"
TARGET_DIR="${HOME}/.cline/rules"
TARGET_FILE="${TARGET_DIR}/bmad-core.md"
# 锁文件置于 rules 外部，防止被 Cline UI 误识别为全局规则
LOCK_FILE="$(dirname "${TARGET_DIR}")/.bmad_dispatch.lock"
BACKUP_DIR="${TARGET_DIR}/.backups"

FORCE=0
MODE="deploy" # deploy | test | status | rollback

usage() {
    cat <<EOF
用法: $0 [选项]

选项:
  --test         执行预检与只读模拟验证，不写入真实目标文件
  --status       检查当前分发状态、目标文件存在性与指纹匹配情况
  --rollback     安全回退至上一次受管备份
  --force        强制覆盖（忽略用户修改警告）
  --target-dir D 指定目标目录 (默认: ~/.cline/rules)
  -h, --help     显示本帮助信息
EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --test)
            MODE="test"
            shift
            ;;
        --status)
            MODE="status"
            shift
            ;;
        --rollback)
            MODE="rollback"
            shift
            ;;
        --force)
            FORCE=1
            shift
            ;;
        --target-dir)
            TARGET_DIR="$2"
            TARGET_FILE="${TARGET_DIR}/bmad-core.md"
            LOCK_FILE="$(dirname "${TARGET_DIR}")/.bmad_dispatch.lock"
            BACKUP_DIR="${TARGET_DIR}/.backups"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "错误: 未知参数 $1" >&2
            usage
            ;;
    esac
done

# 计算文件 SHA256
calc_sha256() {
    local f="$1"
    if [[ -f "$f" ]]; then
        sha256sum "$f" | awk '{print $1}'
    else
        echo "none"
    fi
}

# 状态对账模式
do_status() {
    echo "============================================================"
    echo "BMAD-Solo V5 Deployment Status Report"
    echo "============================================================"
    echo "  - Source Kernel File: ${SOURCE_FILE}"
    if [[ -f "${SOURCE_FILE}" ]]; then
        local src_hash
        src_hash=$(calc_sha256 "${SOURCE_FILE}")
        echo "    * Status: EXISTS (SHA256: ${src_hash})"
    else
        echo "    * Status: MISSING (需先运行 scripts/distill_v5_kernel.py)"
    fi

    echo "  - Target File: ${TARGET_FILE}"
    if [[ -f "${TARGET_FILE}" ]]; then
        local tgt_hash
        tgt_hash=$(calc_sha256 "${TARGET_FILE}")
        echo "    * Status: INSTALLED (SHA256: ${tgt_hash})"
        if [[ -f "${SOURCE_FILE}" && "${src_hash}" == "${tgt_hash}" ]]; then
            echo "    * Sync: IN_SYNC (完全一致)"
        else
            echo "    * Sync: DRIFT_DETECTED (指纹不一致或已被修改)"
        fi
    else
        echo "    * Status: NOT_INSTALLED"
    fi

    echo "  - Backups Available:"
    if [[ -d "${BACKUP_DIR}" ]]; then
        local backup_count
        backup_count=$(ls -1 "${BACKUP_DIR}"/bmad-core.md.* 2>/dev/null | wc -l || echo 0)
        echo "    * Count: ${backup_count} 份历史快照"
    else
        echo "    * Count: 0 份历史快照"
    fi
    echo "============================================================"
}

# 预检与锁测试模式
do_test() {
    echo "============================================================"
    echo "BMAD-Solo V5 Dispatch Preflight Verification (--test)"
    echo "============================================================"
    
    # 1. 验证源文件存在性
    if [[ ! -f "${SOURCE_FILE}" ]]; then
        echo "FAIL: 源资产缺失: ${SOURCE_FILE}。请先执行 python3 scripts/distill_v5_kernel.py" >&2
        exit 1
    fi
    echo "  [PASS] 源资产存在且可读 (${SOURCE_FILE})"

    # 2. 验证父目录可写性或创建能力
    if [[ -d "${TARGET_DIR}" ]]; then
        if [[ ! -w "${TARGET_DIR}" ]]; then
            echo "FAIL: 目标目录不可写: ${TARGET_DIR}" >&2
            exit 1
        fi
        echo "  [PASS] 目标目录存在且具备写权限 (${TARGET_DIR})"
    else
        local parent_dir
        parent_dir="$(dirname "${TARGET_DIR}")"
        if [[ -d "${parent_dir}" && ! -w "${parent_dir}" ]]; then
            echo "FAIL: 无法创建目标目录，父目录不可写: ${parent_dir}" >&2
            exit 1
        fi
        echo "  [PASS] 目标目录可正常创建 (${TARGET_DIR})"
    fi

    # 3. 验证排他锁可用性
    mkdir -p "$(dirname "${LOCK_FILE}")"
    exec 200>"${LOCK_FILE}"
    if ! flock -n 200; then
        echo "FAIL: 无法获取排他分发锁: ${LOCK_FILE} (可能存在并发写入者)" >&2
        exit 1
    fi
    echo "  [PASS] 成功获取非阻塞排他锁 (${LOCK_FILE})"
    flock -u 200

    echo "------------------------------------------------------------"
    echo "Status: PREFLIGHT_PASS (所有预检与锁契约均已满足)"
    echo "============================================================"
}

# 安全回滚模式
do_rollback() {
    echo "============================================================"
    echo "BMAD-Solo V5 Safe Rollback (--rollback)"
    echo "============================================================"
    
    if [[ ! -d "${BACKUP_DIR}" ]]; then
        echo "FAIL: 未找到备份目录: ${BACKUP_DIR}，无法执行安全回滚" >&2
        exit 1
    fi

    local latest_backup
    latest_backup=$(ls -1t "${BACKUP_DIR}"/bmad-core.md.* 2>/dev/null | head -n 1 || true)
    if [[ -z "${latest_backup}" || ! -f "${latest_backup}" ]]; then
        echo "FAIL: 未找到任何有效的备份文件，停止回退以防破坏现场" >&2
        exit 1
    fi

    mkdir -p "${TARGET_DIR}"
    exec 200>"${LOCK_FILE}"
    if ! flock -n 200; then
        echo "FAIL: 获取部署锁失败，存在并发操作，拒绝回滚" >&2
        exit 1
    fi

    echo "正在从最新备份还原: ${latest_backup} -> ${TARGET_FILE}..."
    local temp_target="${TARGET_FILE}.rollback.tmp.$$"
    cp -p "${latest_backup}" "${temp_target}"
    mv -f "${temp_target}" "${TARGET_FILE}"
    flock -u 200

    echo "SUCCESS: 已成功回退至备份: ${latest_backup}"
    echo "============================================================"
}

# 正式受管分发事务
do_deploy() {
    echo "============================================================"
    echo "BMAD-Solo V5 Managed Kernel Dispatch"
    echo "============================================================"

    if [[ ! -f "${SOURCE_FILE}" ]]; then
        echo "FAIL: 源资产缺失: ${SOURCE_FILE}。请先执行 python3 scripts/distill_v5_kernel.py" >&2
        exit 1
    fi

    mkdir -p "${TARGET_DIR}"
    mkdir -p "${BACKUP_DIR}"
    mkdir -p "$(dirname "${LOCK_FILE}")"

    # 获取排他文件锁
    exec 200>"${LOCK_FILE}"
    if ! flock -n 200; then
        echo "FAIL: 部署锁被占用，另一分发进程正在运行: ${LOCK_FILE}" >&2
        exit 1
    fi

    local src_hash
    src_hash=$(calc_sha256 "${SOURCE_FILE}")

    # 检查现有文件与用户修改防踩踏
    if [[ -f "${TARGET_FILE}" ]]; then
        local tgt_hash
        tgt_hash=$(calc_sha256 "${TARGET_FILE}")

        if [[ "${src_hash}" == "${tgt_hash}" ]]; then
            echo "INFO: 目标文件与源资产指纹完全一致 (${src_hash})，无需重复分发。"
            flock -u 200
            exit 0
        fi

        # 检查是否含受管标记
        if ! grep -q "BMAD-Solo V5" "${TARGET_FILE}" 2>/dev/null; then
            if [[ ${FORCE} -eq 0 ]]; then
                echo "WARN: 目标文件已被用户手动修改或非 BMAD-Solo V5 受管资产！" >&2
                echo "      为防止意外覆盖，分发已中止。如确认覆盖请追加 --force" >&2
                flock -u 200
                exit 1
            else
                echo "WARN: 用户指定 --force，允许覆盖现有未受管文件。"
            fi
        fi

        # 创建历史快照
        local timestamp
        timestamp=$(date +"%Y%m%d_%H%M%S")
        local backup_file="${BACKUP_DIR}/bmad-core.md.${timestamp}"
        cp -p "${TARGET_FILE}" "${backup_file}"
        echo "  - 已为现有文件创建安全快照: ${backup_file}"
    fi

    # 原子替换机制：写入临时文件后原子 rename
    local temp_file="${TARGET_FILE}.tmp.$$"
    cp -p "${SOURCE_FILE}" "${temp_file}"
    sync "${temp_file}" 2>/dev/null || true
    mv -f "${temp_file}" "${TARGET_FILE}"

    flock -u 200

    local final_hash
    final_hash=$(calc_sha256 "${TARGET_FILE}")
    echo "  - 目标路径: ${TARGET_FILE}"
    echo "  - 交付指纹: ${final_hash}"
    echo "------------------------------------------------------------"
    echo "Status: DEPLOY_SUCCESS (静态治理内核已受管分发至全局 ~/.cline/rules/)"
    echo "============================================================"
}

case "${MODE}" in
    status)
        do_status
        ;;
    test)
        do_test
        ;;
    rollback)
        do_rollback
        ;;
    deploy)
        do_deploy
        ;;
esac
