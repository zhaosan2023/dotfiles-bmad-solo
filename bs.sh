#!/bin/bash
set -euo pipefail

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GEMINI_CONFIG_DIR="$HOME/.gemini/config"
TARGET_DIR="$GEMINI_CONFIG_DIR/skills/bmad-solo"

DRY_RUN=0
UNINSTALL=0
VERSION="v4"
SWITCH_TAG=""
SWITCH_LATEST=0

show_help() {
    echo -e "${YELLOW}Usage:${NC} $0 [options] [v3 | v4]"
    echo ""
    echo -e "${GREEN}Major Architecture Versions:${NC}"
    echo "  v4, 4, --v4       Install/activate BMAD-Solo V4 (Default active suite)"
    echo "  v3, 3, --v3       Install/activate BMAD-Solo V3 (Historical baseline)"
    echo ""
    echo -e "${GREEN}GitOps Version Inspection & Rollback:${NC}"
    echo "  --status, -s      Show current Git branch, commit, active tag, and symlinks"
    echo "  --tags, -l        List all available release tags (v4.0.0, v4.1.0, etc.)"
    echo "  --tag <tag>, -t   Checkout specific release tag and activate immediately"
    echo "  --latest          Switch back to main branch (latest V4)"
    echo ""
    echo -e "${GREEN}General Options:${NC}"
    echo "  --dry-run         Show actions without making changes"
    echo "  --uninstall       Remove bmad-suite and global rules from Gemini config"
    echo "  --help, -h        Show this help message"
    echo ""
}

show_status() {
    echo -e "${YELLOW}======================================================${NC}"
    echo -e "${YELLOW} BMAD-Solo Environment & Version Status ${NC}"
    echo -e "${YELLOW}======================================================${NC}"
    if git -C "$SCRIPT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        BRANCH=$(git -C "$SCRIPT_DIR" branch --show-current 2>/dev/null || echo "")
        COMMIT=$(git -C "$SCRIPT_DIR" log -1 --format="%h (%s)" 2>/dev/null || echo "Unknown")
        EXACT_TAG=$(git -C "$SCRIPT_DIR" describe --tags --exact-match 2>/dev/null || echo "")
        TAG_DESC=$(git -C "$SCRIPT_DIR" describe --tags 2>/dev/null || echo "No tag")
        
        if [ -z "$BRANCH" ]; then
            BRANCH="[HEAD detached at ${EXACT_TAG:-$TAG_DESC}]"
        fi
        
        echo -e "Git Branch / State : ${GREEN}$BRANCH${NC}"
        echo -e "Git Commit         : $COMMIT"
        if [ -n "$EXACT_TAG" ]; then
            echo -e "Active Release Tag : ${GREEN}$EXACT_TAG (Exact Match)${NC}"
        else
            echo -e "Nearest Tag        : $TAG_DESC"
        fi
    else
        echo -e "Git Repository     : ${RED}Not inside a git repository${NC}"
    fi
    
    echo -e "\nInstalled Symlinks:"
    TARGET_PLUGIN="$GEMINI_CONFIG_DIR/plugins/bmad-suite"
    if [ -L "$TARGET_PLUGIN" ]; then
        DEST=$(readlink "$TARGET_PLUGIN")
        if [[ "$DEST" == *".versions/"* ]]; then
            ACTIVE_TAG=$(echo "$DEST" | sed -E 's|.*/\.versions/([^/]+)/.*|\1|')
            echo -e "  Active Mode : ${YELLOW}Isolated Snapshot Tag: $ACTIVE_TAG${NC}"
        else
            echo -e "  Active Mode : ${GREEN}Rolling Latest (main)${NC}"
        fi
        echo -e "  Plugin      : $TARGET_PLUGIN -> ${GREEN}$DEST${NC}"
    elif [ -e "$TARGET_PLUGIN" ]; then
        echo -e "  Plugin      : $TARGET_PLUGIN (${YELLOW}Regular directory, not symlink${NC})"
    else
        echo -e "  Plugin      : ${RED}Not installed${NC}"
    fi

    for RULE in bmad-constitution.md bmad-core.md; do
        RULE_PATH="$GEMINI_CONFIG_DIR/rules/$RULE"
        if [ -L "$RULE_PATH" ]; then
            DEST=$(readlink "$RULE_PATH")
            echo -e "  Rule    : $RULE -> ${GREEN}$DEST${NC}"
        elif [ -e "$RULE_PATH" ]; then
            echo -e "  Rule    : $RULE (${YELLOW}Regular file${NC})"
        else
            echo -e "  Rule    : $RULE (${RED}Missing${NC})"
        fi
    done
    echo -e "${YELLOW}======================================================${NC}"
}

list_tags() {
    echo -e "${YELLOW}======================================================${NC}"
    echo -e "${YELLOW} BMAD-Solo Available Release Tags ${NC}"
    echo -e "${YELLOW}======================================================${NC}"
    if git -C "$SCRIPT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        git -C "$SCRIPT_DIR" --no-pager tag -l -n1
        echo -e "\n${GREEN}Tip:${NC} Rollback to any tag: ./bs.sh --tag <tag>"
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
        --latest)
            SWITCH_LATEST=1
            shift
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
    echo -e "${YELLOW}Uninstalling BMAD-Solo Plugin...${NC}"
    if [ $DRY_RUN -eq 1 ]; then
        echo "[DRY-RUN] Would remove $GEMINI_CONFIG_DIR/plugins/bmad-suite"
        echo "[DRY-RUN] Would remove rules from $GEMINI_CONFIG_DIR/rules/"
    else
        rm -rf "$TARGET_DIR"
        rm -rf "$GEMINI_CONFIG_DIR/plugins/bmad-suite"
        rm -f "$GEMINI_CONFIG_DIR/rules/bmad-constitution.md"
        rm -f "$GEMINI_CONFIG_DIR/rules/bmad-core.md"
        echo -e "${GREEN}Successfully uninstalled bmad-suite from $GEMINI_CONFIG_DIR${NC}"
    fi
    exit 0
fi

if [ -n "$SWITCH_TAG" ]; then
    echo -e "${YELLOW}======================================================${NC}"
    echo -e "${YELLOW} GitOps: Activating Release Tag: $SWITCH_TAG (Shadow Snapshot)... ${NC}"
    echo -e "${YELLOW}======================================================${NC}"
    if ! git -C "$SCRIPT_DIR" rev-parse "refs/tags/$SWITCH_TAG" >/dev/null 2>&1; then
        echo -e "${RED}Error: Tag '$SWITCH_TAG' does not exist in repository.${NC}"
        echo -e "Run '$0 --tags' to see available release tags."
        exit 1
    fi

    VERSION_CACHE="$SCRIPT_DIR/.versions/$SWITCH_TAG"
    if [ ! -d "$VERSION_CACHE" ]; then
        echo -e "  [i] Extracting tag $SWITCH_TAG snapshot to .versions/$SWITCH_TAG..."
        mkdir -p "$VERSION_CACHE"
        git -C "$SCRIPT_DIR" archive "tags/$SWITCH_TAG" | tar -x -C "$VERSION_CACHE"
    fi

    SOURCE_SUITE="$VERSION_CACHE/bmad-suite-v4"
    if [ ! -d "$SOURCE_SUITE" ] && [ -d "$VERSION_CACHE/bmad-suite" ]; then
        SOURCE_SUITE="$VERSION_CACHE/bmad-suite"
    fi
    VERSION_TITLE="BMAD-Solo Tag $SWITCH_TAG (Isolated Snapshot)"
    COMMAND_TIPS="  • /bmad-solo  : V4 Engineering Loop (Isolated Snapshot: $SWITCH_TAG)\n  • /ana-solo   : Dedicated Deep Analysis Channel"
    echo -e "${GREEN}[✔] Target suite isolated at: $SOURCE_SUITE${NC}\n"
elif [ $SWITCH_LATEST -eq 1 ]; then
    echo -e "${YELLOW}======================================================${NC}"
    echo -e "${YELLOW} GitOps: Returning to main branch (latest V4)... ${NC}"
    echo -e "${YELLOW}======================================================${NC}"
    if git -C "$SCRIPT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        CURRENT_BRANCH=$(git -C "$SCRIPT_DIR" branch --show-current 2>/dev/null || echo "")
        if [ -n "$CURRENT_BRANCH" ] && [ "$CURRENT_BRANCH" != "main" ]; then
            git -C "$SCRIPT_DIR" checkout main 2>/dev/null || true
        fi
    fi
    SOURCE_SUITE="$SCRIPT_DIR/bmad-suite-v4"
    VERSION_TITLE="BMAD-Solo V4 (Analyst Closed-Loop + /ana-solo + 4 Convergence Locks)"
    COMMAND_TIPS="  • /bmad-solo  : V4 Engineering Loop (with Analyst Gate)\n  • /ana-solo   : Dedicated Deep Analysis Channel"
    echo -e "${GREEN}[✔] Successfully returned to main branch (latest V4)${NC}\n"
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
    echo -e "${YELLOW}[DRY-RUN MODE] No files will be modified.${NC}"
fi

# We install into the plugins folder
PLUGIN_DIR="$GEMINI_CONFIG_DIR/plugins"
TARGET_DIR="$PLUGIN_DIR/bmad-suite"

if [ $DRY_RUN -eq 0 ]; then mkdir -p "$PLUGIN_DIR"; fi

if [ -e "$TARGET_DIR" ] && [ ! -L "$TARGET_DIR" ]; then
    echo -e "${RED}Error: $TARGET_DIR exists and is not a symlink. Please remove it manually to avoid conflicts.${NC}"
    exit 1
fi

echo -e "${YELLOW}Linking $VERSION_TITLE Plugin to namespace...${NC}"

if [ $DRY_RUN -eq 1 ]; then
    echo "[DRY-RUN] Would create symlink: $TARGET_DIR -> $SOURCE_SUITE"
    echo "[DRY-RUN] Would link rules into $GEMINI_CONFIG_DIR/rules/"
else
    # Remove existing symlink
    rm -f "$TARGET_DIR"
    rm -f "$GEMINI_CONFIG_DIR/skills/bmad-solo"

    ln -s "$SOURCE_SUITE" "$TARGET_DIR"
    echo -e "  [✔] Linked plugin namespace ($VERSION) -> $SOURCE_SUITE"
    
    # Explicitly link rules so they appear in the Customizations UI
    mkdir -p "$GEMINI_CONFIG_DIR/rules"
    ln -sf "$SOURCE_SUITE/rules/bmad-constitution.md" "$GEMINI_CONFIG_DIR/rules/bmad-constitution.md"
    ln -sf "$SOURCE_SUITE/rules/bmad-core.md" "$GEMINI_CONFIG_DIR/rules/bmad-core.md"
    echo -e "  [✔] Linked global rules to $GEMINI_CONFIG_DIR/rules/"
fi

echo -e "\n${GREEN}======================================================${NC}"
echo -e "${GREEN} $VERSION_TITLE successfully activated! ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo -e "Active Commands:"
echo -e "$COMMAND_TIPS"
echo -e "\nNext steps:"
echo -e "1. Open your Antigravity IDE."
echo -e "2. Execute: 'Developer: Reload Window'."
echo -e "3. Version & Rollback management:
   • Check active version:  ./bs.sh --status
   • View release tags:     ./bs.sh --tags
   • Rollback to tag:       ./bs.sh --tag <tag> (e.g. ./bs.sh --tag v4.0.0)
   • Return to latest:      ./bs.sh --latest
   • Switch major version:  ./bs.sh v3 | ./bs.sh v4"
echo -e ""
