#!/bin/bash
set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

REPO_URL="https://github.com/zhaosan2023/dotfiles-bmad-solo.git"
TARGET_DIR="${BMAD_SOLO_DIR:-$HOME/.dotfiles/dotfiles-bmad-solo}"

echo -e "${YELLOW}======================================================${NC}"
echo -e "${YELLOW} BMAD-Solo Remote One-Line Installer                  ${NC}"
echo -e "${YELLOW}======================================================${NC}"

if [ ! -d "$TARGET_DIR/.git" ]; then
    echo -e "  [i] Cloning repository to: ${GREEN}$TARGET_DIR${NC}..."
    mkdir -p "$(dirname "$TARGET_DIR")"
    git clone "$REPO_URL" "$TARGET_DIR"
else
    echo -e "  [i] Existing repository detected at: ${GREEN}$TARGET_DIR${NC}."
    echo -e "  [i] Fetching and pulling latest changes from origin..."
    git -C "$TARGET_DIR" fetch --tags origin
    git -C "$TARGET_DIR" checkout main 2>/dev/null || true
    git -C "$TARGET_DIR" pull --ff-only origin main || true
fi

echo -e "\n  [i] Bootstrapping Physical Mirror via bs.sh..."
cd "$TARGET_DIR"
./bs.sh --latest

echo -e "\n${GREEN}======================================================${NC}"
echo -e "${GREEN} BMAD-Solo Installation Complete!                     ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo -e "Repository Path : ${GREEN}$TARGET_DIR${NC}"
echo -e "Global Mirror   : ${GREEN}$HOME/.gemini/config/plugins/bmad-suite${NC}"
echo -e "\nTo check status at any time:"
echo -e "  cd $TARGET_DIR && ./bs.sh --status"
echo -e "\nTo pull future updates:"
echo -e "  cd $TARGET_DIR && ./bs.sh --update"
echo -e "\nRemember to reload your Antigravity IDE (Developer: Reload Window)."
