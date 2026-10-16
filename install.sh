#!/bin/bash
set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

REPO_URL="https://github.com/zhaosan2023/dotfiles-bmad-solo.git"
TARGET_DIR="${BMAD_SOLO_DIR:-$HOME/.dotfiles/dotfiles-bmad-solo}"

# 只接受套件选择；在克隆、更新或任何部署写入之前拒绝冲突参数。
INSTALL_VERSION=""
BOOTSTRAP_ARGS=()
select_install_version() {
    if [ -n "$INSTALL_VERSION" ] && [ "$INSTALL_VERSION" != "$1" ]; then
        printf '%s\n' '错误：不能同时选择不同套件版本；未克隆、更新或部署。' >&2
        exit 1
    fi
    INSTALL_VERSION="$1"
}
while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h)
            printf '%s\n' '用法：bash install.sh [v3 | v4 | v5 | --suite <version>]'
            printf '%s\n' '新安装省略版本兼容默认 V4；已有安装保留已核验的受管版本。'
            printf '%s\n' '身份未知时要求显式选择，不回退 V4；不同版本参数冲突即停止。'
            printf '%s\n' '安装仅物化受管资产，不启动 Ralph、不准备模型认证或部署业务服务。'
            exit 0
            ;;
        --suite)
            if [[ $# -lt 2 ]] || [[ ! "$2" =~ ^v[345]$ ]]; then
                printf '%s\n' '错误：--suite 需要 v3、v4 或 v5。' >&2
                exit 1
            fi
            select_install_version "$2"
            shift 2
            ;;
        v3|3|--v3|--version-3|-3)
            select_install_version v3
            shift
            ;;
        v4|4|--v4|--version-4|-4)
            select_install_version v4
            shift
            ;;
        v5|5|--v5|--version-5|-5)
            select_install_version v5
            shift
            ;;
        *)
            printf '错误：未知安装参数 %s；未克隆、更新或部署。\n' "$1" >&2
            exit 1
            ;;
    esac
done
if [ -n "$INSTALL_VERSION" ]; then
    BOOTSTRAP_ARGS+=(--suite "$INSTALL_VERSION")
fi

# 省略版本时不注入 V4；受管部署入口在更新前解析已有安装身份。
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
timeout --kill-after=5s 30s bash "$TARGET_DIR/bs.sh" "$BOOTSTRAP_ACTION" "${BOOTSTRAP_ARGS[@]}" < /dev/null

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
