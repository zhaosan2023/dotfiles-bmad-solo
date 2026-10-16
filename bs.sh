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
VERSION_EXPLICIT=0
SWITCH_TAG=""
SWITCH_LATEST=0
UPDATE_REMOTE=0
MODE_TARGETS=()
PREFLIGHT=0
RESUME_COMMIT=""

# 使用参数数组重建有效部署意图；更新/切分支参数不进入新版执行。
# 环境变量中的部署根目录由 exec 继承，不拼接为命令字符串。
handoff_main() {
    if [ "${BMAD_HANDOFF_ACTIVE:-0}" = 1 ]; then
        printf '%s\n' '错误：禁止重复执行移交，未再次更新或部署。' >&2
        exit 1
    fi
    local RESUME_ARGS=(--_resume-main "$1" "$VERSION")
    if [ $DRY_RUN -eq 1 ]; then RESUME_ARGS+=(--dry-run); fi
    if [ $PREFLIGHT -eq 1 ]; then RESUME_ARGS+=(--preflight); fi
    local TARGET
    for TARGET in "${MODE_TARGETS[@]}"; do
        RESUME_ARGS+=(--mode-target "$TARGET")
    done
    printf '显式移交磁盘新版部署入口，提交 %s；不重复更新。\n' "$1"
    exec env BMAD_HANDOFF_ACTIVE=1 bash "$SCRIPT_DIR/bs.sh" "${RESUME_ARGS[@]}" < /dev/null
}

select_version() {
    if [ "$VERSION_EXPLICIT" -eq 1 ] && [ "$VERSION" != "$1" ]; then
        printf '%s\n' '错误：不能同时选择不同套件版本；未更新或部署。' >&2
        exit 1
    fi
    VERSION="$1"
    VERSION_EXPLICIT=1
}

show_help() {
    echo -e "${YELLOW}Usage:${NC} $0 [options] [v3 | v4 | v5]"
    echo ""
    echo -e "${GREEN}Major Architecture Versions:${NC}"
    echo "  v5, 5, --v5       显式选择 BMRalph V5 独立套件"
    echo "  v4, 4, --v4       选择 V4；未指定版本的新安装兼容默认 V4"
    echo "  v3, 3, --v3       选择 V3 历史基线（源资产仍须通过预检）"
    echo "  --suite <version> 显式选择 v3、v4 或 v5；不同版本参数冲突即停止"
    echo "  已有安装省略版本：保留已核验的受管版本；身份未知时要求显式选择"
    echo ""
    echo -e "${GREEN}GitOps Version Inspection & Updates:${NC}"
    echo "  --update, -u      Fetch & pull latest from origin and deploy physical mirror"
    echo "  --status, -s      Show Git status, deployed mirror status, commit, and manifest"
    echo "  --tags, -l        List all available release tags (v4.0.0, v4.1.0, etc.)"
    echo "  --tag <tag>, -t   从标签提交核验并分发所选套件，不切换工作树"
    echo "  --latest          切回 main；仓库分支选择不改变已确定的套件版本"
    echo ""
    echo -e "${GREEN}General Options:${NC}"
    echo "  --dry-run         Show actions without making changes"
    echo "  --preflight       只读列出全部迁移范围与阻塞，不授予接管权限"
    echo "  --mode-target <path>  显式模式配置相对路径，可重复；替代自动探测"
    echo "  --uninstall       Remove bmad-suite and global rules from Gemini config"
    echo "  --help, -h        Show this help message"
    echo "  安装、更新、分发及 IDE 重载不启动 Ralph，不准备模型认证或部署业务服务"
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

# 整个入口先解析为函数，再执行版本操作；避免 Bash 在脚本被替换后
# 从旧文件偏移继续读取。成功后 exec 新版，不执行本函数的旧部署尾部。
main() {
local ORIGINAL_ARGS=("$@")
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
            if [ -n "$SWITCH_TAG" ] && [ "$SWITCH_TAG" != "$2" ]; then
                printf '%s\n' '错误：不能同时选择不同标签；未更新或部署。' >&2
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
        --preflight)
            PREFLIGHT=1
            shift
            ;;
        --_resume-main)
            if [[ $# -lt 2 ]] || [[ ! "$2" =~ ^([0-9a-f]{40}|[0-9a-f]{64})$ ]]; then
                printf '%s\n' '错误：执行移交缺少有效提交标识。' >&2
                exit 1
            fi
            RESUME_COMMIT="$2"
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
        --suite)
            if [[ $# -lt 2 ]] || [[ ! "$2" =~ ^v[345]$ ]]; then
                printf '%s\n' '错误：--suite 需要 v3、v4 或 v5。' >&2
                exit 1
            fi
            select_version "$2"
            shift 2
            ;;
        v3|3|--v3|--version-3|-3)
            select_version "v3"
            shift
            ;;
        v4|4|--v4|--version-4|-4)
            select_version "v4"
            shift
            ;;
        v5|5|--v5|--version-5|-5)
            select_version "v5"
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo -e "Run '$0 --help' to see all available options."
            exit 1
            ;;
    esac
done

# 继承编号不是持锁证据；在新版续接及任何版本动作前核验内核排他锁。
# 同一描述符穿过 exec 移交，最终部署仅借用，不释放外层锁。
if [ "${BMAD_VERSION_LOCK_FD+x}" = x ]; then
    if [[ ! "$BMAD_VERSION_LOCK_FD" =~ ^[0-9]+$ ]] || [ $DRY_RUN -eq 1 ] || [ $PREFLIGHT -eq 1 ] || [ $UNINSTALL -eq 1 ]; then
        printf '%s\n' '错误：继承版本锁参数非法或与只读操作冲突，停止执行。' >&2
        exit 1
    fi
    if [ $UPDATE_REMOTE -eq 0 ] && [ $SWITCH_LATEST -eq 0 ] && [ -z "$SWITCH_TAG" ] && [ -z "$RESUME_COMMIT" ]; then
        printf '%s\n' '错误：继承版本锁缺少版本操作或新版续接，停止执行。' >&2
        exit 1
    fi
    timeout -k 2s 15s python3 -B "$SCRIPT_DIR/scripts/deployment-version-guard.py" --root "${BMAD_DEPLOY_ROOT:-$HOME}" --check-fd "$BMAD_VERSION_LOCK_FD" < /dev/null
fi

# 内部续接只能部署已经核验的 main；禁止传回更新动作形成循环。
if [ "${BMAD_HANDOFF_ACTIVE:-0}" = 1 ] && [ -z "$RESUME_COMMIT" ]; then
    printf '%s\n' '错误：移交标记缺少续接提交，拒绝执行。' >&2
    exit 1
fi
if [ -n "$RESUME_COMMIT" ]; then
    if [ "${BMAD_HANDOFF_ACTIVE:-0}" != 1 ] || [ $UPDATE_REMOTE -eq 1 ] || [ $SWITCH_LATEST -eq 1 ] || [ -n "$SWITCH_TAG" ] || [ $UNINSTALL -eq 1 ]; then
        printf '%s\n' '错误：执行移交参数冲突，未更新或部署。' >&2
        exit 1
    fi
    RESUME_BRANCH=$(timeout 15s git --no-pager -C "$SCRIPT_DIR" branch --show-current < /dev/null)
    RESUME_ACTUAL=$(timeout 15s git --no-pager -C "$SCRIPT_DIR" rev-parse --verify HEAD < /dev/null)
    RESUME_STATUS=$(timeout 15s git --no-pager --no-optional-locks -C "$SCRIPT_DIR" status --porcelain=v1 --untracked-files=all < /dev/null)
    if [ "$RESUME_BRANCH" != main ] || [ "$RESUME_ACTUAL" != "$RESUME_COMMIT" ] || [ -n "$RESUME_STATUS" ]; then
        printf '%s\n' '错误：新版续接时分支、提交或工作树发生变化，停止部署。' >&2
        exit 1
    fi
fi
# 范围预检只针对当前已物化来源，不允许联网、切分支、缓存或卸载。
if [ $PREFLIGHT -eq 1 ] && { [ $UPDATE_REMOTE -eq 1 ] || [ $SWITCH_LATEST -eq 1 ] || [ -n "$SWITCH_TAG" ] || [ $UNINSTALL -eq 1 ]; }; then
    printf '%s\n' '错误：--preflight 不能与更新、版本切换或卸载组合。' >&2
    exit 1
fi

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
    timeout 30s python3 -B "$SCRIPT_DIR/scripts/deploy-managed-cli.py" "${UNINSTALL_ARGS[@]}" < /dev/null
    exit 0
fi

# 冲突参数必须在任何版本操作之前拒绝，真实执行与模拟执行保持一致。
if [ -n "$SWITCH_TAG" ] && { [ $UPDATE_REMOTE -eq 1 ] || [ $SWITCH_LATEST -eq 1 ]; }; then
    printf '%s\n' '错误：标签选择不能与远程更新或主分支选择组合。' >&2
    exit 1
fi

# 在网络访问、主分支切换及新版移交前确定有效套件意图。
# 旧资产或状态目录存在而身份记录缺失时，不按新安装默认回切 V4。
if [ "$VERSION_EXPLICIT" -eq 0 ]; then
    INTENT_ROOT="${BMAD_DEPLOY_ROOT:-$HOME}"
    for MARKER in ".bmad-solo-deployment" ".gemini/config/plugins/bmad-suite" ".gemini/config/rules/bmad-core.md" ".roo/rules/02-bmad-core.md"; do
        if [ -e "$INTENT_ROOT/$MARKER" ] || [ -L "$INTENT_ROOT/$MARKER" ]; then
            VERSION=$(timeout 15s python3 -B "$SCRIPT_DIR/scripts/deployment-status.py" --root "$INTENT_ROOT" --active-suite < /dev/null)
            break
        fi
    done
fi
MAPPING_ARGS=(--version "$VERSION")
if [ -n "$SWITCH_TAG" ]; then MAPPING_ARGS+=(--tag "$SWITCH_TAG"); fi
SOURCE_RELATIVE=$(timeout 15s python3 -B "$SCRIPT_DIR/scripts/suite_versions.py" "${MAPPING_ARGS[@]}" < /dev/null)

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

# 已有部署的真实版本动作须全程持有固定排他锁：先拒绝共享租约，
# 再进行 Git 写入、缓存准备、新版移交及部署。只读预览已在上方返回。
# 新安装没有部署状态时沿用首次部署预检，不为了版本动作创建锁。
if [ $UPDATE_REMOTE -eq 1 ] || [ $SWITCH_LATEST -eq 1 ] || [ -n "$SWITCH_TAG" ] || [ -n "$RESUME_COMMIT" ]; then
    VERSION_STATE="${BMAD_DEPLOY_ROOT:-$HOME}/.bmad-solo-deployment"
    if [ "${BMAD_VERSION_LOCK_FD+x}" != x ] && { [ -e "$VERSION_STATE" ] || [ -L "$VERSION_STATE" ]; }; then
        exec timeout -k 2s 30s python3 -B "$SCRIPT_DIR/scripts/deployment-version-guard.py" --root "${BMAD_DEPLOY_ROOT:-$HOME}" --repository "$SCRIPT_DIR" -- "${ORIGINAL_ARGS[@]}" < /dev/null
    fi
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
    handoff_main "$ACTUAL_COMMIT"
fi

if [ -n "$SWITCH_TAG" ]; then
    echo -e "${YELLOW}======================================================${NC}"
    echo -e "${YELLOW} GitOps: Activating Release Tag: $SWITCH_TAG (Shadow Snapshot)... ${NC}"
    echo -e "${YELLOW}======================================================${NC}"
    # 缓存绑定解析后的实际提交；完整提取并核验后发布，拒绝复用旧标签缓存。
    # 子进程失败直接停止，不回退到当前工作树或其他版本套件。
    SOURCE_SUITE=$(timeout 30s python3 -B "$SCRIPT_DIR/scripts/tag-cache.py" --repo "$SCRIPT_DIR" --tag "$SWITCH_TAG" --suite "$VERSION" < /dev/null)
    VERSION_TITLE="BMAD-Solo $VERSION Tag $SWITCH_TAG (Isolated Snapshot)"
    COMMAND_TIPS="  • /bmad-solo  : $VERSION 工程入口（标签快照：$SWITCH_TAG）\n  • /ana-solo   : 分析入口；以目标运行时实际加载为准"
    echo -e "${GREEN}[✔] Target suite isolated at: $SOURCE_SUITE${NC}\n"
elif [ $SWITCH_LATEST -eq 1 ] || [ -n "$RESUME_COMMIT" ]; then
    echo -e "${YELLOW}======================================================${NC}"
    echo -e "${YELLOW} GitOps: Returning to main branch; selected suite $VERSION... ${NC}"
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
    if [ -z "$RESUME_COMMIT" ]; then
        SELECTED_COMMIT=$(timeout 15s git --no-pager -C "$SCRIPT_DIR" rev-parse --verify HEAD < /dev/null)
        handoff_main "$SELECTED_COMMIT"
    fi
    SOURCE_SUITE="$SCRIPT_DIR/$SOURCE_RELATIVE"
    VERSION_TITLE="BMAD-Solo $VERSION（已选择 main；套件版本独立）"
    COMMAND_TIPS="  • /bmad-solo  : $VERSION 工程入口\n  • /ana-solo   : 分析入口；以目标运行时实际加载为准"
    echo -e "${GREEN}[✔] 已选择 main，保留套件 $VERSION${NC}\n"
else
    SOURCE_SUITE="$SCRIPT_DIR/$SOURCE_RELATIVE"
    VERSION_TITLE="BMAD-Solo $VERSION"
    if [ "$VERSION" = "v5" ]; then VERSION_TITLE="BMRalph V5 独立套件"; fi
    COMMAND_TIPS="  • /bmad-solo  : $VERSION 工程入口\n  • /ana-solo   : 分析入口；以目标运行时实际加载为准"
fi

if [ -z "$SWITCH_TAG" ]; then
    SOURCE_SUITE=$(timeout 15s python3 -B "$SCRIPT_DIR/scripts/suite_versions.py" --version "$VERSION" --repo "$SCRIPT_DIR" < /dev/null)
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
    local RELATIVE_SETTINGS
    local DEPLOY_ARGS=(--root "$DEPLOY_ROOT" --source "$SOURCE_SUITE" --repository "$SCRIPT_DIR")
    if [ "${BMAD_VERSION_LOCK_FD+x}" = x ]; then
        DEPLOY_ARGS+=(--deployment-lock-fd "$BMAD_VERSION_LOCK_FD")
    fi
    if [ $PREFLIGHT -eq 1 ]; then
        DEPLOY_ARGS+=(--preflight)
    fi
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
        # Python 只读发现已存在的 Roo 扩展存储，包括含空格的本机 IDE 路径。
        DEPLOY_ARGS+=(--discover-modes)
    fi
    # 单一入口覆盖插件、共享规则及模式配置；禁止先写插件再发现 YAML 损坏。
    timeout 30s python3 -B "$SCRIPT_DIR/scripts/deploy-managed-cli.py" "${DEPLOY_ARGS[@]}" < /dev/null
}

deploy_managed_suite
if [ $PREFLIGHT -eq 1 ]; then
    return 0
fi


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
   • Switch major version:  ./bs.sh v3 | ./bs.sh v4 | ./bs.sh v5"
printf '%s\n' '安装、更新、分发和 IDE 重载不启动 Ralph；远程试跑与模型认证须另行授权。'
echo -e ""
}

main "$@"
