#!/bin/bash
set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

REPO_URL="https://github.com/zhaosan2023/dotfiles-bmad-solo.git"
TARGET_DIR="${BMAD_SOLO_DIR:-$HOME/.dotfiles/dotfiles-bmad-solo}"

# 唯一 V4；兼容已有 V4 参数，其他参数在克隆、更新或部署之前拒绝。
while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h)
            printf '%s\n' '用法：bash install.sh；兼容 v4 或 --suite v4。'
            printf '%s\n' '仅安装人-AI 值守 V4；已有退役或未知部署身份停止，不自动覆盖。'
            printf '%s\n' '安装仅物化受管资产，不启动 Ralph、不准备模型认证或部署业务服务。'
            exit 0
            ;;
        --suite)
            if [[ $# -lt 2 ]] || [[ "$2" != v4 ]]; then
                printf '%s\n' '错误：仅支持 --suite v4；未克隆、更新或部署。' >&2
                exit 1
            fi
            shift 2
            ;;
        v4|4|--v4|--version-4|-4)
            shift
            ;;
        *)
            printf '错误：未知安装参数 %s；未克隆、更新或部署。\n' "$1" >&2
            exit 1
            ;;
    esac
done
# 受管入口唯一分发 V4，并在更新前核验已有部署身份。
echo -e "${YELLOW}======================================================${NC}"
echo -e "${YELLOW} BMAD-Solo Remote One-Line Installer                  ${NC}"
echo -e "${YELLOW}======================================================${NC}"

BOOTSTRAP_ACTION=--latest
if [ ! -d "$TARGET_DIR/.git" ]; then
    echo -e "  [i] Cloning repository to: ${GREEN}$TARGET_DIR${NC}..."
    timeout 15s mkdir -p "$(dirname "$TARGET_DIR")" < /dev/null
    timeout 30s env GIT_TERMINAL_PROMPT=0 GIT_SSH_COMMAND='ssh -oBatchMode=yes -oConnectTimeout=10' git -c core.hooksPath=/dev/null clone --no-recurse-submodules --branch main "$REPO_URL" "$TARGET_DIR" < /dev/null
else
    echo -e "  [i] Existing repository detected at: ${GREEN}$TARGET_DIR${NC}."
    # 网络访问前保护现有工作树；状态检查不得刷新索引。
    WORKTREE_STATUS=$(timeout 15s git --no-pager --no-optional-locks -C "$TARGET_DIR" status --porcelain=v1 --untracked-files=all < /dev/null)
    if [ -n "$WORKTREE_STATUS" ]; then
        printf '%s\n' '错误：安装仓库存在未提交或未跟踪改动，未获取远端或执行部署。' >&2
        exit 1
    fi
    timeout 15s git --no-pager -C "$TARGET_DIR" rev-parse --verify --end-of-options 'refs/heads/main^{commit}' < /dev/null > /dev/null
    # 复用部署入口的更新、快进校验及失败关闭逻辑，不忽略任何失败。
    BOOTSTRAP_ACTION=--update
fi

echo -e "\n  [i] Bootstrapping Physical Mirror via bs.sh..."
timeout --kill-after=5s 30s bash "$TARGET_DIR/bs.sh" "$BOOTSTRAP_ACTION" --suite v4 < /dev/null

echo -e "\n${GREEN}======================================================${NC}"
printf '%s\n' '受管资产处理完成；尚未验证 Roo 运行时加载或权限行为。'
echo -e "${GREEN}======================================================${NC}"
echo -e "Repository Path : ${GREEN}$TARGET_DIR${NC}"
echo -e "Global Mirror   : ${GREEN}$HOME/.gemini/config/plugins/bmad-suite${NC}"
echo -e "\nTo check status at any time:"
echo -e "  cd $TARGET_DIR && ./bs.sh --status"
echo -e "\nTo pull future updates:"
echo -e "  cd $TARGET_DIR && ./bs.sh --update"
echo -e "\nRemember to reload your Antigravity IDE (Developer: Reload Window)."
printf '%s\n' '安装、更新、分发及 IDE 重载不启动 Ralph；独立认证、远程试跑和业务部署须另行授权。'
