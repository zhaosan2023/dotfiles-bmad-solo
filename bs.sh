#!/bin/bash
set -euo pipefail

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

DRY_RUN=0
UNINSTALL=0
VERSION="v4"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
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
            echo -e "Usage: $0 [v3 | v4] [--dry-run] [--uninstall]"
            exit 1
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GEMINI_CONFIG_DIR="$HOME/.gemini/config"
TARGET_DIR="$GEMINI_CONFIG_DIR/skills/bmad-solo"

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

if [ "$VERSION" = "v3" ]; then
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
echo -e "3. To switch versions at any time:
   • Switch to V3: ./bs.sh v3
   • Switch to V4: ./bs.sh v4"
echo -e ""
