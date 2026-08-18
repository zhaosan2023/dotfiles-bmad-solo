#!/bin/bash
set -euo pipefail

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

DRY_RUN=0
UNINSTALL=0

# Parse arguments
for arg in "$@"; do
    case $arg in
        --dry-run)
        DRY_RUN=1
        shift
        ;;
        --uninstall)
        UNINSTALL=1
        shift
        ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GEMINI_CONFIG_DIR="$HOME/.gemini/config"
TARGET_DIR="$GEMINI_CONFIG_DIR/skills/bmad-solo"

if [ $UNINSTALL -eq 1 ]; then
    echo -e "${YELLOW}Uninstalling BMAD-Solo V2...${NC}"
    if [ $DRY_RUN -eq 1 ]; then
        echo "[DRY-RUN] Would remove $TARGET_DIR"
    else
        rm -rf "$TARGET_DIR"
        echo -e "${GREEN}Successfully uninstalled bmad-solo from $TARGET_DIR${NC}"
    fi
    exit 0
fi

echo -e "${YELLOW}Starting BMAD-Solo V2 Bootstrap Process (AGSL Lightweight)...${NC}"

if [ $DRY_RUN -eq 1 ]; then
    echo -e "${YELLOW}[DRY-RUN MODE] No files will be modified.${NC}"
fi

# We only install into the namespaced skills folder to prevent breaking existing Antigravity setups
if [ -L "$GEMINI_CONFIG_DIR/skills" ]; then
    REAL_PARENT=$(readlink -f "$GEMINI_CONFIG_DIR/skills")
    if [ "$REAL_PARENT" = "$SCRIPT_DIR/config/skills" ]; then
        echo -e "  [✔] The entire config/skills directory is already linked. bmad-solo is implicitly loaded."
    else
        echo -e "${RED}Error: $GEMINI_CONFIG_DIR/skills is a symlink pointing to $REAL_PARENT.${NC}"
        echo -e "${RED}Please remove it manually to avoid conflicts.${NC}"
        exit 1
    fi
else
    if [ $DRY_RUN -eq 0 ]; then mkdir -p "$GEMINI_CONFIG_DIR/skills"; fi

    if [ -e "$TARGET_DIR" ] && [ ! -L "$TARGET_DIR" ]; then
        echo -e "${RED}Error: $TARGET_DIR exists and is not a symlink. Please remove it manually to avoid conflicts.${NC}"
        exit 1
    fi

    echo -e "${YELLOW}Linking BMAD-Solo skill to namespace...${NC}"

    if [ $DRY_RUN -eq 1 ]; then
        echo "[DRY-RUN] Would create symlink: $TARGET_DIR -> $SCRIPT_DIR/config/skills/bmad-solo"
    else
        # Remove existing symlink if any (to avoid ln -sfn pointing to itself if broken)
        rm -f "$TARGET_DIR"
        ln -s "$SCRIPT_DIR/config/skills/bmad-solo" "$TARGET_DIR"
        echo -e "  [✔] Linked bmad-solo skill namespace"
    fi
fi

echo -e "\n${GREEN}======================================================${NC}"
echo -e "${GREEN} BMAD-Solo (AGSL Lightweight) successfully bootstrapped! ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo -e "Next steps:"
echo -e "1. Open your Antigravity IDE."
echo -e "2. Execute: 'Developer: Reload Window'."
echo -e "3. Type '/' in the chat to verify the '/bmad-solo' skill is active."
echo -e ""
