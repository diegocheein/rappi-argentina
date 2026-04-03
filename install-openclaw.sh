#!/usr/bin/env bash
# Install the Rappi plugin for OpenClaw.
# Usage: ./install-openclaw.sh
#
# What this does:
# 1. Checks for uv (Python package manager) — installs if missing
# 2. Installs Python dependencies
# 3. Registers the MCP server with OpenClaw
# 4. Copies skills to the OpenClaw workspace
# 5. Prompts to restart the gateway

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

PLUGIN_DIR="$(cd "$(dirname "$0")" && pwd)"
OPENCLAW_WORKSPACE="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"

echo -e "${BOLD}Rappi Plugin — OpenClaw Installer${NC}\n"

# Step 1: Check for uv
echo -e "${DIM}[1/5] Checking for uv...${NC}"
if command -v uv &>/dev/null; then
    echo -e "  ${GREEN}uv found:${NC} $(uv --version)"
else
    echo -e "  ${YELLOW}uv not found — installing...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Source the updated PATH
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    if command -v uv &>/dev/null; then
        echo -e "  ${GREEN}uv installed:${NC} $(uv --version)"
    else
        echo -e "  ${RED}Failed to install uv. Install manually: https://docs.astral.sh/uv/${NC}"
        exit 1
    fi
fi

# Step 2: Install dependencies
echo -e "${DIM}[2/5] Installing Python dependencies...${NC}"
cd "$PLUGIN_DIR"
uv sync 2>&1 | tail -1
echo -e "  ${GREEN}Dependencies installed${NC}"

# Step 3: Register MCP server with OpenClaw
echo -e "${DIM}[3/5] Registering MCP server with OpenClaw...${NC}"
if command -v openclaw &>/dev/null; then
    openclaw mcp set rappi "{\"command\":\"uv\",\"args\":[\"run\",\"--project\",\"$PLUGIN_DIR\",\"rappi-mcp\"]}" 2>/dev/null || {
        echo -e "  ${YELLOW}Could not auto-register. Add manually to your openclaw.json:${NC}"
        echo -e "  ${DIM}\"rappi\": {\"command\": \"uv\", \"args\": [\"run\", \"--project\", \"$PLUGIN_DIR\", \"rappi-mcp\"]}${NC}"
    }
    echo -e "  ${GREEN}MCP server registered as 'rappi'${NC}"
else
    echo -e "  ${YELLOW}openclaw CLI not found. Add manually to your MCP config:${NC}"
    echo -e "  ${DIM}\"rappi\": {\"command\": \"uv\", \"args\": [\"run\", \"--project\", \"$PLUGIN_DIR\", \"rappi-mcp\"]}${NC}"
fi

# Step 4: Copy skills to OpenClaw workspace
echo -e "${DIM}[4/5] Installing skills...${NC}"
if [ -d "$PLUGIN_DIR/skills" ]; then
    mkdir -p "$OPENCLAW_WORKSPACE/skills"
    for skill_dir in "$PLUGIN_DIR/skills"/*/; do
        skill_name=$(basename "$skill_dir")
        target="$OPENCLAW_WORKSPACE/skills/$skill_name"
        if [ -d "$target" ]; then
            rm -rf "$target"
        fi
        cp -r "$skill_dir" "$target"
        echo -e "  ${GREEN}Installed skill:${NC} $skill_name"
    done
else
    echo -e "  ${YELLOW}No skills directory found${NC}"
fi

# Step 5: Summary
echo -e "\n${GREEN}${BOLD}Installation complete!${NC}\n"
echo -e "${BOLD}Next steps:${NC}"
echo ""
echo -e "  1. Authenticate with Rappi:"
echo -e "     ${DIM}# If you have a browser:${NC}"
echo -e "     uv run --project $PLUGIN_DIR rappi auth login"
echo -e ""
echo -e "     ${DIM}# Headless server (no browser):${NC}"
echo -e "     uv run --project $PLUGIN_DIR rappi auth token <RAPPI_TOKEN> <DEVICE_ID>"
echo -e "     ${DIM}# Get these from ~/.rappi/config.json on a machine where you've logged in${NC}"
echo ""
echo -e "  2. Restart OpenClaw gateway:"
echo -e "     openclaw gateway restart"
echo ""
echo -e "  3. Try it out:"
echo -e "     \"Search for pizza on Rappi\""
