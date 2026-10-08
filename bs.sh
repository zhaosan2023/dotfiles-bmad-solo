#!/bin/bash
set -euo pipefail

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GEMINI_CONFIG_DIR="$HOME/.gemini/config"
PLUGIN_DIR="$GEMINI_CONFIG_DIR/plugins"
TARGET_DIR="$PLUGIN_DIR/bmad-suite"
RULES_DIR="$GEMINI_CONFIG_DIR/rules"
ROO_GLOBAL_DIR="$HOME/.roo"
ROO_RULES_DIR="$ROO_GLOBAL_DIR/rules"
ROO_ANA_DIR="$ROO_GLOBAL_DIR/rules-ana-architect"
ROO_ENG_DIR="$ROO_GLOBAL_DIR/rules-bmad-engineer"


DRY_RUN=0
UNINSTALL=0
VERSION="v4"
SWITCH_TAG=""
SWITCH_LATEST=0
UPDATE_REMOTE=0
MODE_TARGETS=()

show_help() {
    echo -e "${YELLOW}Usage:${NC} $0 [options] [v3 | v4]"
    echo ""
    echo -e "${GREEN}Major Architecture Versions:${NC}"
    echo "  v4, 4, --v4       Install/activate BMAD-Solo V4 (Default active suite)"
    echo "  v3, 3, --v3       Install/activate BMAD-Solo V3 (Historical baseline)"
    echo ""
    echo -e "${GREEN}GitOps Version Inspection & Updates:${NC}"
    echo "  --update, -u      Fetch & pull latest from origin and deploy physical mirror"
    echo "  --status, -s      Show Git status, deployed mirror status, commit, and manifest"
    echo "  --tags, -l        List all available release tags (v4.0.0, v4.1.0, etc.)"
    echo "  --tag <tag>, -t   Checkout specific release tag and activate immediately"
    echo "  --latest          Switch back to main branch (latest V4)"
    echo ""
    echo -e "${GREEN}General Options:${NC}"
    echo "  --dry-run         Show actions without making changes"
    echo "  --mode-target <path>  显式模式配置相对路径，可重复；替代自动探测"
    echo "  --uninstall       Remove bmad-suite and global rules from Gemini config"
    echo "  --help, -h        Show this help message"
    echo ""
}

show_status() {
    # 与部署使用同一根目录；路径通过参数传递，不插值为 Python 代码。
    # 只读核验受管摘要及事务状态，非零退出直接传递给调用者。
    timeout 15s python3 -B "$SCRIPT_DIR/scripts/deployment-status.py" --root "${BMAD_DEPLOY_ROOT:-$HOME}" < /dev/null
}

list_tags() {
    echo -e "${YELLOW}======================================================${NC}"
    echo -e "${YELLOW} BMAD-Solo Available Release Tags ${NC}"
    echo -e "${YELLOW}======================================================${NC}"
    if git -C "$SCRIPT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        git -C "$SCRIPT_DIR" --no-pager tag -l -n1
        echo -e "\n${GREEN}Tip:${NC} Rollback to any tag: ./bs.sh --tag <tag>"
        echo -e "     Update from remote: ./bs.sh --update"
        echo -e "     Return to latest:   ./bs.sh --latest"
    else
        echo -e "${RED}Error: Not a git repository.${NC}"
    fi
    echo -e "${YELLOW}======================================================${NC}"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h)
            show_help
            exit 0
            ;;
        --status|-s)
            show_status
            exit 0
            ;;
        --tags|-l|--list-tags)
            list_tags
            exit 0
            ;;
        --tag|-t)
            if [[ $# -lt 2 ]] || [[ "$2" =~ ^- ]]; then
                echo -e "${RED}Error: --tag requires a tag argument (e.g. ./bs.sh --tag v4.0.0)${NC}"
                exit 1
            fi
            SWITCH_TAG="$2"
            shift 2
            ;;
        --update|-u)
            UPDATE_REMOTE=1
            shift
            ;;
        --latest)
            SWITCH_LATEST=1
            shift
            ;;
        --mode-target)
            if [[ $# -lt 2 ]] || [[ -z "$2" ]] || [[ "$2" == -* ]]; then
                printf '%s\n' '错误：--mode-target 需要部署根目录内的相对文件路径。' >&2
                exit 1
            fi
            MODE_TARGETS+=("$2")
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --uninstall)
            UNINSTALL=1
            shift
            ;;
        v3|3|--v3|--version-3|-3)
            VERSION="v3"
            shift
            ;;
        v4|4|--v4|--version-4|-4)
            VERSION="v4"
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo -e "Run '$0 --help' to see all available options."
            exit 1
            ;;
    esac
done

if [ $UNINSTALL -eq 1 ]; then
    if [ ${#MODE_TARGETS[@]} -gt 0 ]; then
        printf '%s\n' '错误：卸载按所有权清单处理，不支持同时指定模式目标。' >&2
        exit 1
    fi
    if [ $UPDATE_REMOTE -eq 1 ] || [ $SWITCH_LATEST -eq 1 ] || [ -n "$SWITCH_TAG" ]; then
        printf '%s\n' 'Error: uninstall cannot be combined with update or version switching.' >&2
        exit 1
    fi
    UNINSTALL_ARGS=(--root "${BMAD_DEPLOY_ROOT:-$HOME}" --uninstall)
    if [ $DRY_RUN -eq 1 ]; then
        UNINSTALL_ARGS+=(--dry-run)
    fi
    # 仅卸载所有权清单确认且未被用户修改的资产；未知文件及共享目录保留。
    # 前台限时执行，标准输入封闭；子进程失败直接传递，不输出虚假成功。
    timeout 30s python3 "$SCRIPT_DIR/scripts/deploy-managed-cli.py" "${UNINSTALL_ARGS[@]}" < /dev/null
    exit 0
fi

# 冲突参数必须在任何版本操作之前拒绝，真实执行与模拟执行保持一致。
if [ -n "$SWITCH_TAG" ] && { [ $UPDATE_REMOTE -eq 1 ] || [ $SWITCH_LATEST -eq 1 ]; }; then
    printf '%s\n' '错误：标签选择不能与远程更新或主分支选择组合。' >&2
    exit 1
fi

# 版本操作的模拟执行必须在网络访问、切分支和创建缓存之前结束。
# 此分支仅预览版本动作；未物化的源不能声称完成资产预检。
if [ $DRY_RUN -eq 1 ] && { [ $UPDATE_REMOTE -eq 1 ] || [ $SWITCH_LATEST -eq 1 ] || [ -n "$SWITCH_TAG" ]; }; then
    if [ -n "$SWITCH_TAG" ] && { [ $UPDATE_REMOTE -eq 1 ] || [ $SWITCH_LATEST -eq 1 ]; }; then
        printf '%s\n' '错误：标签选择不能与远程更新或主分支选择组合。' >&2
        exit 1
    fi
    if [ -n "$SWITCH_TAG" ]; then
        PREVIEW_COMMIT=$(timeout 15s git --no-pager -C "$SCRIPT_DIR" rev-parse --verify --end-of-options "refs/tags/$SWITCH_TAG^{commit}" < /dev/null)
        printf '模拟版本选择：标签 %s，提交 %s；未创建或复用缓存。\n' "$SWITCH_TAG" "$PREVIEW_COMMIT"
    elif [ $UPDATE_REMOTE -eq 1 ]; then
        printf '%s\n' '模拟远程更新：拟获取 origin 并快进 main；未访问远端，远程提交及可快进性尚未验证。'
    else
        PREVIEW_COMMIT=$(timeout 15s git --no-pager -C "$SCRIPT_DIR" rev-parse --verify --end-of-options 'refs/heads/main^{commit}' < /dev/null)
        printf '模拟主分支选择：本地 main 提交 %s；未切换工作树。\n' "$PREVIEW_COMMIT"
    fi
    printf '%s\n' '仅完成版本动作预览；未执行资产预检、部署或运行时验收。'
    exit 0
fi

# 更新或切分支前保护已跟踪及未跟踪改动；禁用可选锁，避免状态检查刷新索引。
# 模拟版本预览已在上方返回，不在此执行任何写入式检查。
if [ $UPDATE_REMOTE -eq 1 ] || [ $SWITCH_LATEST -eq 1 ]; then
    WORKTREE_STATUS=$(timeout 15s git --no-pager --no-optional-locks -C "$SCRIPT_DIR" status --porcelain=v1 --untracked-files=all < /dev/null)
    if [ -n "$WORKTREE_STATUS" ]; then
        printf '%s\n' '错误：工作树存在已跟踪或未跟踪改动；拒绝远程更新及分支切换，未执行部署。' >&2
        exit 1
    fi
fi

if [ $UPDATE_REMOTE -eq 1 ]; then
    echo -e "${YELLOW}======================================================${NC}"
    echo -e "${YELLOW} GitOps: Fetching & Pulling Latest from GitHub...     ${NC}"
    echo -e "${YELLOW}======================================================${NC}"
    # 本地主分支缺失时先失败关闭，避免网络访问或修改 FETCH_HEAD。
    timeout 15s git --no-pager -C "$SCRIPT_DIR" rev-parse --verify --end-of-options 'refs/heads/main^{commit}' < /dev/null > /dev/null
    printf '%s\n' '获取 origin/main 与标签；失败立即停止，不进入部署。'
    timeout 30s env GIT_TERMINAL_PROMPT=0 GIT_SSH_COMMAND='ssh -oBatchMode=yes -oConnectTimeout=10' git --no-pager -C "$SCRIPT_DIR" -c core.hooksPath=/dev/null fetch --no-recurse-submodules --tags origin 'refs/heads/main:refs/remotes/origin/main' < /dev/null
    UPDATE_COMMIT=$(timeout 15s git --no-pager -C "$SCRIPT_DIR" rev-parse --verify --end-of-options 'refs/remotes/origin/main^{commit}' < /dev/null)
    # 先检查可快进性，分歧时保留当前分支和工作树，不强制重置。
    timeout 15s git --no-pager -C "$SCRIPT_DIR" merge-base --is-ancestor refs/heads/main "$UPDATE_COMMIT" < /dev/null
    CURRENT_BRANCH=$(timeout 15s git --no-pager -C "$SCRIPT_DIR" branch --show-current < /dev/null)
    if [ "$CURRENT_BRANCH" != "main" ]; then
        timeout 15s env GIT_TERMINAL_PROMPT=0 git --no-pager -C "$SCRIPT_DIR" -c core.hooksPath=/dev/null switch --no-guess main < /dev/null
    fi
    CURRENT_BRANCH=$(timeout 15s git --no-pager -C "$SCRIPT_DIR" branch --show-current < /dev/null)
    if [ "$CURRENT_BRANCH" != "main" ]; then
        printf '%s\n' '错误：更新前未实际切换至 main，停止部署。' >&2
        exit 1
    fi
    timeout 30s env GIT_TERMINAL_PROMPT=0 GIT_MERGE_AUTOEDIT=no git --no-pager -C "$SCRIPT_DIR" -c core.hooksPath=/dev/null merge --ff-only --no-edit "$UPDATE_COMMIT" < /dev/null
    ACTUAL_COMMIT=$(timeout 15s git --no-pager -C "$SCRIPT_DIR" rev-parse --verify HEAD < /dev/null)
    if [ "$ACTUAL_COMMIT" != "$UPDATE_COMMIT" ]; then
        printf '%s\n' '错误：更新后提交与本次获取的目标不一致，停止部署。' >&2
        exit 1
    fi
    printf '本地 main 已核验更新至提交 %s；尚未完成部署。\n' "$ACTUAL_COMMIT"
    SWITCH_LATEST=1
fi

if [ -n "$SWITCH_TAG" ]; then
    echo -e "${YELLOW}======================================================${NC}"
    echo -e "${YELLOW} GitOps: Activating Release Tag: $SWITCH_TAG (Shadow Snapshot)... ${NC}"
    echo -e "${YELLOW}======================================================${NC}"
    # 缓存绑定解析后的实际提交；完整提取并核验后发布，拒绝复用旧标签缓存。
    # 子进程失败直接停止，不回退到当前工作树或其他版本套件。
    SOURCE_SUITE=$(timeout 30s python3 "$SCRIPT_DIR/scripts/tag-cache.py" --repo "$SCRIPT_DIR" --tag "$SWITCH_TAG" < /dev/null)
    VERSION_TITLE="BMAD-Solo Tag $SWITCH_TAG (Isolated Snapshot)"
    COMMAND_TIPS="  • /bmad-solo  : V4 Engineering Loop (Isolated Snapshot: $SWITCH_TAG)\n  • /ana-solo   : Dedicated Deep Analysis Channel"
    echo -e "${GREEN}[✔] Target suite isolated at: $SOURCE_SUITE${NC}\n"
elif [ $SWITCH_LATEST -eq 1 ]; then
    echo -e "${YELLOW}======================================================${NC}"
    echo -e "${YELLOW} GitOps: Returning to main branch (latest V4)... ${NC}"
    echo -e "${YELLOW}======================================================${NC}"
    # 先确认本地主分支存在；缺失时不尝试切换，也不进入部署。
    timeout 15s git --no-pager -C "$SCRIPT_DIR" rev-parse --verify --end-of-options 'refs/heads/main^{commit}' < /dev/null > /dev/null
    CURRENT_BRANCH=$(timeout 15s git --no-pager -C "$SCRIPT_DIR" branch --show-current < /dev/null)
    if [ "$CURRENT_BRANCH" != "main" ]; then
        # 游离 HEAD 同样需要实际切换；禁止忽略失败或自动猜测远程分支。
        timeout 15s env GIT_TERMINAL_PROMPT=0 git --no-pager -C "$SCRIPT_DIR" -c core.hooksPath=/dev/null switch --no-guess main < /dev/null
    fi
    CURRENT_BRANCH=$(timeout 15s git --no-pager -C "$SCRIPT_DIR" branch --show-current < /dev/null)
    if [ "$CURRENT_BRANCH" != "main" ]; then
        printf '%s\n' '错误：未实际切换至 main，停止部署。' >&2
        exit 1
    fi
    SOURCE_SUITE="$SCRIPT_DIR/bmad-suite-v4"
    VERSION_TITLE="BMAD-Solo V4 (Analyst Closed-Loop + /ana-solo + 4 Convergence Locks)"
    COMMAND_TIPS="  • /bmad-solo  : V4 Engineering Loop (with Analyst Gate)\n  • /ana-solo   : Dedicated Deep Analysis Channel"
    echo -e "${GREEN}[✔] Successfully selected main branch (latest V4)${NC}\n"
elif [ "$VERSION" = "v3" ]; then
    SOURCE_SUITE="$SCRIPT_DIR/bmad-suite-v3"
    VERSION_TITLE="BMAD-Solo V3 (Stable Baseline)"
    COMMAND_TIPS="  • /bmad-solo  : V3 Standard Engineering Loop"
else
    SOURCE_SUITE="$SCRIPT_DIR/bmad-suite-v4"
    VERSION_TITLE="BMAD-Solo V4 (Analyst Closed-Loop + /ana-solo + 4 Convergence Locks)"
    COMMAND_TIPS="  • /bmad-solo  : V4 Engineering Loop (with Analyst Gate)\n  • /ana-solo   : Dedicated Deep Analysis Channel"
fi

if [ ! -d "$SOURCE_SUITE" ] && [ -d "$SCRIPT_DIR/bmad-suite" ]; then
    echo -e "${YELLOW}Notice: $SOURCE_SUITE not found, falling back to $SCRIPT_DIR/bmad-suite${NC}"
    SOURCE_SUITE="$SCRIPT_DIR/bmad-suite"
fi

if [ ! -d "$SOURCE_SUITE" ]; then
    echo -e "${RED}Error: Target source directory $SOURCE_SUITE does not exist!${NC}"
    exit 1
fi

echo -e "${YELLOW}======================================================${NC}"
echo -e "${YELLOW} Bootstrapping $VERSION_TITLE... ${NC}"
echo -e "${YELLOW}======================================================${NC}"

if [ $DRY_RUN -eq 1 ]; then
    echo -e "${YELLOW}[DRY-RUN MODE] Actions will be simulated without modifications.${NC}"
fi


deploy_managed_suite() {
    local DEPLOY_ROOT="${BMAD_DEPLOY_ROOT:-$HOME}"
    local RELATIVE_SETTINGS STORAGE_PARENT
    local DEPLOY_ARGS=(--root "$DEPLOY_ROOT" --source "$SOURCE_SUITE" --repository "$SCRIPT_DIR")
    local SETTINGS_CANDIDATES=(
        '.antigravity-ide-server/data/User/globalStorage/rooveterinaryinc.roo-cline/settings'
        '.vscode-server/data/User/globalStorage/rooveterinaryinc.roo-cline/settings'
        '.config/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings'
    )
    if [ $DRY_RUN -eq 1 ]; then
        DEPLOY_ARGS+=(--dry-run)
    fi
    # 显式目标替代自动发现；这里只传递参数，不创建目录或读取未选中配置。
    # 相对路径、重复目标、链接边界及 YAML 由受管入口统一预检。
    if [ ${#MODE_TARGETS[@]} -gt 0 ]; then
        printf '%s\n' '已指定模式目标，跳过自动候选探测。'
        for RELATIVE_SETTINGS in "${MODE_TARGETS[@]}"; do
            DEPLOY_ARGS+=(--mode-target "$RELATIVE_SETTINGS")
            printf '显式模式目标待预检：%s\n' "$RELATIVE_SETTINGS"
        done
    else
        for RELATIVE_SETTINGS in "${SETTINGS_CANDIDATES[@]}"; do
            STORAGE_PARENT="$DEPLOY_ROOT/${RELATIVE_SETTINGS%/settings}"
            if [ -e "$STORAGE_PARENT" ] || [ -L "$STORAGE_PARENT" ]; then
                DEPLOY_ARGS+=(--mode-target "$RELATIVE_SETTINGS/custom_modes.yaml")
                printf '模式候选待预检：%s\n' "$RELATIVE_SETTINGS"
            else
                printf '跳过模式候选（存储目录不存在）：%s\n' "$RELATIVE_SETTINGS"
            fi
        done
    fi
    # 单一入口覆盖插件、共享规则及模式配置；禁止先写插件再发现 YAML 损坏。
    timeout 30s python3 "$SCRIPT_DIR/scripts/deploy-managed-cli.py" "${DEPLOY_ARGS[@]}" < /dev/null
}

deploy_managed_suite


echo -e "\n${GREEN}======================================================${NC}"
if [ $DRY_RUN -eq 1 ]; then
    printf '%s\n' '受管部署模拟预检结束；未执行资产写入。'
else
    printf '%s\n' '受管资产处理完成；不代表 Roo 已加载或运行时验收通过。'
fi
echo -e "${GREEN}======================================================${NC}"
echo -e "Commands available after runtime loading is verified:"
echo -e "$COMMAND_TIPS"
echo -e "\nNext steps:"
echo -e "1. Open your Antigravity IDE."
echo -e "2. Execute: 'Developer: Reload Window'."
echo -e "3. Version & Rollback management:
   • Check active version:  ./bs.sh --status
   • Pull remote updates:   ./bs.sh --update
   • View release tags:     ./bs.sh --tags
   • Rollback to tag:       ./bs.sh --tag <tag> (e.g. ./bs.sh --tag v4.1.0)
   • Return to latest:      ./bs.sh --latest
   • Switch major version:  ./bs.sh v3 | ./bs.sh v4"
echo -e ""
