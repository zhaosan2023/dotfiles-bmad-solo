#!/bin/bash
set -e

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting BMAD-Solo V2 Bootstrap Process...${NC}"

# 1. Dynamically identify the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo -e "Detected dotfiles directory at: ${SCRIPT_DIR}"

# 2. Check and create target config directory
GEMINI_CONFIG_DIR="$HOME/.gemini/config"
if [ ! -d "$GEMINI_CONFIG_DIR" ]; then
    echo -e "Creating ${GEMINI_CONFIG_DIR}..."
    mkdir -p "$GEMINI_CONFIG_DIR"
fi

# 3. Create Symlinks
echo -e "${YELLOW}Linking BMAD-Solo rules and skills...${NC}"

# Link GEMINI.md
if [ -f "$SCRIPT_DIR/GEMINI.md" ]; then
    ln -sf "$SCRIPT_DIR/GEMINI.md" "$GEMINI_CONFIG_DIR/GEMINI.md"
    echo -e "  [✔] Linked GEMINI.md"
else
    echo -e "${RED}Error: GEMINI.md not found in ${SCRIPT_DIR}${NC}"
    exit 1
fi

# Link AGENTS.md
if [ -f "$SCRIPT_DIR/config/AGENTS.md" ]; then
    ln -sf "$SCRIPT_DIR/config/AGENTS.md" "$GEMINI_CONFIG_DIR/AGENTS.md"
    echo -e "  [✔] Linked AGENTS.md"
else
    echo -e "${RED}Error: config/AGENTS.md not found in ${SCRIPT_DIR}${NC}"
    exit 1
fi

# Link skills directory
if [ -d "$SCRIPT_DIR/config/skills" ]; then
    ln -sfn "$SCRIPT_DIR/config/skills" "$GEMINI_CONFIG_DIR/skills"
    echo -e "  [✔] Linked skills directory"
else
    echo -e "${RED}Error: config/skills directory not found in ${SCRIPT_DIR}${NC}"
    exit 1
fi

# 4. Finish
echo -e "\n${GREEN}======================================================${NC}"
echo -e "${GREEN} BMAD-Solo environment successfully bootstrapped!     ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo -e "Next steps:"
echo -e "1. Open your Antigravity IDE."
echo -e "2. Open the Command Palette (Ctrl+Shift+P / Cmd+Shift+P)."
echo -e "3. Execute: 'Developer: Reload Window'."
echo -e "4. Type '/' in the chat to verify the '/bmad-solo' skill is active."
echo -e ""
