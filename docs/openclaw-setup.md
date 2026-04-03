# OpenClaw Setup Guide

This guide covers installing and configuring the Rappi plugin for [OpenClaw](https://openclaw.ai).

OpenClaw recognizes the Rappi plugin as a **bundle** — it reads the `.claude-plugin/` structure, auto-maps skills, and connects to the MCP tools. No TypeScript or native plugin code needed.

## Prerequisites

- [OpenClaw](https://openclaw.ai) installed and running
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- A Rappi account (Colombia or Mexico)

## Option A: Local Installation (Recommended)

This runs the MCP server as a local subprocess — same as Claude Code. Best for personal use.

### 1. Clone and install

```bash
git clone https://github.com/garavitgabriel/rappi-claude-plugin.git
cd rappi-claude-plugin
uv sync
uv run playwright install chromium
```

### 2. Authenticate with Rappi

```bash
# Colombia (default)
uv run rappi auth login

# Mexico
uv run rappi auth login --country mx
```

### 3. Install as OpenClaw bundle

```bash
openclaw plugins install ./rappi-claude-plugin
openclaw gateway restart
```

### 4. Verify

```bash
openclaw plugins list          # Should show "rappi" bundle
openclaw plugins inspect rappi # Check details
```

### 5. Use it

Start a conversation with OpenClaw and try:
- "Search for pizza on Rappi"
- "What's available on Rappi near me?"
- "Order me a burger"

The plugin auto-activates when you mention food, ordering, or Rappi.

### How it works

OpenClaw reads the `.mcp.json` in the plugin root:
```json
{
  "mcpServers": {
    "rappi": {
      "command": "uv",
      "args": ["run", "--project", ".", "rappi-mcp"]
    }
  }
}
```

This spawns the MCP server as a subprocess using stdio transport. The 39 tools become available as `rappi__<tool_name>` in OpenClaw.

The 4 skills (`order-food`, `rappi-search`, `rappi-reorder`, `rappi-suggest`) are loaded as OpenClaw skills automatically.

## Option B: Remote MCP Server

Connect OpenClaw to a deployed MCP server over HTTP. Best for shared setups or when you don't want Python installed on the OpenClaw machine.

### 1. Deploy the MCP server

Deploy to Railway (or any host). See the main [README deployment section](../README.md#deployment) for full instructions.

Quick version:
1. Fork the repo, connect to [Railway](https://railway.com)
2. Set env vars: `MCP_TRANSPORT=sse`, `RAPPI_TOKEN`, `RAPPI_DEVICE_ID`, `RAPPI_COUNTRY`
3. Verify: `curl https://your-app.up.railway.app/health` returns `ok`

### 2. Generate the OpenClaw bundle

```bash
uv run rappi build-plugin build --target openclaw --url https://your-app.up.railway.app/sse
```

This creates a bundle zip with the SSE URL pre-configured.

### 3. Install the bundle

```bash
openclaw plugins install ~/Desktop/rappi-openclaw-plugin.zip
openclaw gateway restart
```

### 4. Verify

```bash
openclaw plugins list
openclaw plugins inspect rappi
```

## What Gets Mapped

| Plugin Component | OpenClaw Mapping | Status |
|---|---|---|
| `skills/order-food/SKILL.md` | OpenClaw skill | Works |
| `skills/rappi-search/SKILL.md` | OpenClaw skill | Works |
| `skills/rappi-reorder/SKILL.md` | OpenClaw skill | Works |
| `skills/rappi-suggest/SKILL.md` | OpenClaw skill | Works |
| `.mcp.json` (39 tools) | MCP tools (`rappi__*`) | Works |
| `agents/rappi-agent.md` | Not mapped | OpenClaw ignores agents |

## Tool Naming

In OpenClaw, MCP tools are prefixed with the server name:

| Claude Code | OpenClaw |
|---|---|
| `mcp__rappi__search_restaurants` | `rappi__search_restaurants` |
| `mcp__rappi__add_to_cart` | `rappi__add_to_cart` |
| `mcp__rappi__checkout` | `rappi__checkout` |

The skills reference tools using the Claude naming convention (`mcp__rappi__*`). OpenClaw's bundle mapper handles the translation.

## Configuration

### Country

Set your country before authenticating:

```bash
# In the plugin directory
uv run rappi auth login --country co   # Colombia
uv run rappi auth login --country mx   # Mexico
```

For remote deployments, set `RAPPI_COUNTRY` as an environment variable on your server.

### Memory

The plugin stores order history, preferences, and taste profiles locally at `~/.rappi/rappi.db`. This works the same regardless of whether you're using Claude or OpenClaw.

### Spending Limit

Orders over $500,000 COP are blocked by default. To change:
```bash
uv run rappi prefs set max_order_amount 1000000
```

## Troubleshooting

### Plugin not showing in `openclaw plugins list`

Make sure you restarted the gateway:
```bash
openclaw gateway restart
```

### MCP tools not available

Check that `uv` is in your PATH and the plugin dependencies are installed:
```bash
which uv
cd /path/to/rappi-claude-plugin && uv sync
```

### "Token expired" errors

Re-authenticate:
```bash
cd /path/to/rappi-claude-plugin
uv run rappi auth login
```

For remote deployments, update `RAPPI_TOKEN` in your Railway dashboard.

### 403 errors from Rappi API

The `app-version` header may be outdated. See [Updating the app-version Header](../README.md#updating-the-app-version-header).

## Differences from Claude

| Feature | Claude | OpenClaw |
|---|---|---|
| Skills | Auto-triggered by description | Auto-triggered by description |
| MCP Tools | 39 tools via `mcp__rappi__*` | 39 tools via `rappi__*` |
| Agent | `rappi-agent.md` (Sonnet) | Not supported (agents ignored) |
| Memory | Full (SQLite local) | Full (SQLite local) |
| Remote deploy | Railway + Cowork zip | Railway + bundle install |
| Auth | `rappi auth login` | `rappi auth login` (same) |
