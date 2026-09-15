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

DRY_RUN=0
UNINSTALL=0
VERSION="v4"
SWITCH_TAG=""
SWITCH_LATEST=0
UPDATE_REMOTE=0

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
    echo "  --uninstall       Remove bmad-suite and global rules from Gemini config"
    echo "  --help, -h        Show this help message"
    echo ""
}

show_status() {
    echo -e "${YELLOW}======================================================${NC}"
    echo -e "${YELLOW} BMAD-Solo Environment & Version Status ${NC}"
    echo -e "${YELLOW}======================================================${NC}"
    CURRENT_SHORT_COMMIT=""
    if git -C "$SCRIPT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        BRANCH=$(git -C "$SCRIPT_DIR" branch --show-current 2>/dev/null || echo "")
        COMMIT=$(git -C "$SCRIPT_DIR" log -1 --format="%h (%s)" 2>/dev/null || echo "Unknown")
        CURRENT_SHORT_COMMIT=$(git -C "$SCRIPT_DIR" rev-parse --short HEAD 2>/dev/null || echo "")
        EXACT_TAG=$(git -C "$SCRIPT_DIR" describe --tags --exact-match 2>/dev/null || echo "")
        TAG_DESC=$(git -C "$SCRIPT_DIR" describe --tags 2>/dev/null || echo "No tag")
        
        if [ -z "$BRANCH" ]; then
            BRANCH="[HEAD detached at ${EXACT_TAG:-$TAG_DESC}]"
        fi
        
        echo -e "Git Repo Path      : ${GREEN}$SCRIPT_DIR${NC}"
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
    
    echo -e "\nInstalled Global Runtime Environment:"
    TARGET_PLUGIN="$GEMINI_CONFIG_DIR/plugins/bmad-suite"
    if [ -L "$TARGET_PLUGIN" ]; then
        DEST=$(readlink "$TARGET_PLUGIN")
        echo -e "  Plugin Mode : ${YELLOW}Legacy Symlink${NC} (⚠️ Subject to cross-workspace permission barriers)"
        echo -e "  Plugin Path : $TARGET_PLUGIN -> $DEST"
        echo -e "  Action      : ${YELLOW}Run './bs.sh' to upgrade to physical mirror${NC}"
    elif [ -d "$TARGET_PLUGIN" ]; then
        MANIFEST="$TARGET_PLUGIN/.manifest.json"
        if [ -f "$MANIFEST" ]; then
            INSTALLED_VER=$(python3 -c "import json; print(json.load(open('$MANIFEST')).get('installed_version', 'Unknown'))" 2>/dev/null || echo "Unknown")
            DEPLOY_COMMIT=$(python3 -c "import json; print(json.load(open('$MANIFEST')).get('source_commit', ''))" 2>/dev/null || echo "")
            DEPLOY_TIME=$(python3 -c "import json; print(json.load(open('$MANIFEST')).get('deploy_timestamp', 'Unknown'))" 2>/dev/null || echo "Unknown")
            SOURCE_REPO=$(python3 -c "import json; print(json.load(open('$MANIFEST')).get('source_repository', 'Unknown'))" 2>/dev/null || echo "Unknown")
            
            echo -e "  Plugin Mode : ${GREEN}Physical Mirror (Active Sandbox Safe)${NC}"
            echo -e "  Version     : $INSTALLED_VER"
            echo -e "  Deployed At : $DEPLOY_TIME"
            echo -e "  Source Repo : $SOURCE_REPO"
            echo -e "  Plugin Path : $TARGET_PLUGIN"
            
            if [ -n "$CURRENT_SHORT_COMMIT" ] && [ -n "$DEPLOY_COMMIT" ]; then
                if [ "$CURRENT_SHORT_COMMIT" = "$DEPLOY_COMMIT" ]; then
                    echo -e "  Sync Status : ${GREEN}[✔] UP-TO-DATE with local HEAD ($DEPLOY_COMMIT)${NC}"
                else
                    echo -e "  Sync Status : ${YELLOW}[!] STALE (Deployed: $DEPLOY_COMMIT, Local HEAD: $CURRENT_SHORT_COMMIT)${NC}"
                    echo -e "                ${YELLOW}Run './bs.sh' to synchronize local changes.${NC}"
                fi
            fi
        else
            echo -e "  Plugin Mode : ${GREEN}Physical Directory (No Manifest)${NC}"
            echo -e "  Plugin Path : $TARGET_PLUGIN"
            echo -e "  Sync Status : ${YELLOW}[!] Run './bs.sh' to generate deployment manifest.${NC}"
        fi
    else
        echo -e "  Plugin Path : ${RED}Not installed${NC}"
    fi

    echo -e "\nGlobal Rules Status:"
    for RULE in bmad-constitution.md bmad-core.md; do
        RULE_PATH="$GEMINI_CONFIG_DIR/rules/$RULE"
        if [ -L "$RULE_PATH" ]; then
            DEST=$(readlink "$RULE_PATH")
            echo -e "  Rule : $RULE -> ${YELLOW}$DEST (Legacy symlink)${NC}"
        elif [ -f "$RULE_PATH" ]; then
            echo -e "  Rule : $RULE -> ${GREEN}$RULE_PATH (Physical File)${NC}"
        else
            echo -e "  Rule : $RULE -> ${RED}Missing${NC}"
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

if [ $UPDATE_REMOTE -eq 1 ]; then
    echo -e "${YELLOW}======================================================${NC}"
    echo -e "${YELLOW} GitOps: Fetching & Pulling Latest from GitHub...     ${NC}"
    echo -e "${YELLOW}======================================================${NC}"
    if ! git -C "$SCRIPT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        echo -e "${RED}Error: $SCRIPT_DIR is not a git repository.${NC}"
        exit 1
    fi
    
    echo -e "  [i] Fetching latest commits and tags from origin..."
    git -C "$SCRIPT_DIR" fetch --tags origin
    
    CURRENT_BRANCH=$(git -C "$SCRIPT_DIR" branch --show-current 2>/dev/null || echo "")
    if [ -n "$CURRENT_BRANCH" ] && [ "$CURRENT_BRANCH" != "main" ]; then
        echo -e "  [i] Switching branch from $CURRENT_BRANCH to main..."
        git -C "$SCRIPT_DIR" checkout main
    fi
    
    echo -e "  [i] Pulling latest changes on branch 'main'..."
    git -C "$SCRIPT_DIR" pull --ff-only origin main
    echo -e "${GREEN}[✔] Local repository is up to date with origin/main.${NC}\n"
    SWITCH_LATEST=1
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

echo -e "${YELLOW}Deploying $VERSION_TITLE Physical Mirror to namespace...${NC}"

if [ $DRY_RUN -eq 1 ]; then
    echo "[DRY-RUN] Would remove any legacy symlinks at: $TARGET_DIR"
    echo "[DRY-RUN] Would sync physical directory: $SOURCE_SUITE/ -> $TARGET_DIR/"
    echo "[DRY-RUN] Would copy rules into $RULES_DIR/"
    echo "[DRY-RUN] Would generate deployment manifest: $TARGET_DIR/.manifest.json"
else
    # Remove legacy symlinks or old target if it was a symlink
    if [ -L "$TARGET_DIR" ] || [ -f "$TARGET_DIR" ]; then
        rm -rf "$TARGET_DIR"
    fi
    rm -f "$GEMINI_CONFIG_DIR/skills/bmad-solo"
    mkdir -p "$TARGET_DIR" "$RULES_DIR"

    # Physical mirror of plugin directory
    rsync -a --delete "$SOURCE_SUITE/" "$TARGET_DIR/"
    echo -e "  [✔] Mirrored plugin contents ($VERSION) -> $TARGET_DIR (Physical Directory)"

    # Physical copy of global rules (remove old symlinks first)
    for RULE in bmad-constitution.md bmad-core.md; do
        RULE_TARGET="$RULES_DIR/$RULE"
        rm -f "$RULE_TARGET"
        if [ -f "$SOURCE_SUITE/rules/$RULE" ]; then
            cp -f "$SOURCE_SUITE/rules/$RULE" "$RULE_TARGET"
            echo -e "  [✔] Copied rule: $RULE -> $RULES_DIR/ (Physical File)"
        fi
    done

    # Write deployment manifest for GitOps auditing
    COMMIT_HASH=$(git -C "$SCRIPT_DIR" rev-parse --short HEAD 2>/dev/null || echo "unknown")
    COMMIT_FULL=$(git -C "$SCRIPT_DIR" rev-parse HEAD 2>/dev/null || echo "unknown")
    COMMIT_DATE=$(git -C "$SCRIPT_DIR" log -1 --format="%cd" --date=iso 2>/dev/null || echo "unknown")
    DEPLOY_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    cat <<EOF > "$TARGET_DIR/.manifest.json"
{
  "installed_version": "$VERSION_TITLE",
  "source_repository": "$SCRIPT_DIR",
  "source_commit": "$COMMIT_HASH",
  "source_commit_full": "$COMMIT_FULL",
  "commit_date": "$COMMIT_DATE",
  "deploy_timestamp": "$DEPLOY_TIME",
  "deploy_type": "physical_mirror"
}
EOF
    echo -e "  [✔] Generated deployment manifest: $TARGET_DIR/.manifest.json"
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
   • Pull remote updates:   ./bs.sh --update
   • View release tags:     ./bs.sh --tags
   • Rollback to tag:       ./bs.sh --tag <tag> (e.g. ./bs.sh --tag v4.1.0)
   • Return to latest:      ./bs.sh --latest
   • Switch major version:  ./bs.sh v3 | ./bs.sh v4"
echo -e ""
