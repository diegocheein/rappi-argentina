# OpenClaw Setup Guide

This guide covers installing and configuring the Rappi plugin for [OpenClaw](https://openclaw.ai).

OpenClaw recognizes the Rappi plugin as a **bundle** — it reads the `.claude-plugin/` structure, auto-maps skills, and connects to the MCP tools. No TypeScript or native plugin code needed.

## Prerequisites

- [OpenClaw](https://openclaw.ai) installed and running
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager — the install script can set this up for you)
- A Rappi account (Colombia or Mexico)

## Quick Install (One Command)

The install script handles everything — uv, dependencies, MCP registration, and skill installation:

```bash
git clone https://github.com/garavitgabriel/rappi-claude-plugin.git
cd rappi-claude-plugin
./install-openclaw.sh
```

Then authenticate (see [Authentication](#authentication)) and restart the gateway:

```bash
openclaw gateway restart
```

## Manual Installation

### Option A: Local (Recommended)

This runs the MCP server as a local subprocess — same as Claude Code. Best for personal use.

#### 1. Clone and install

```bash
git clone https://github.com/garavitgabriel/rappi-claude-plugin.git
cd rappi-claude-plugin
uv sync
```

#### 2. Register MCP server with OpenClaw

```bash
# Auto-register
openclaw mcp set rappi '{"command":"uv","args":["run","--project","/path/to/rappi-claude-plugin","rappi-mcp"]}'

# Or install as a bundle (if supported by your OpenClaw version)
openclaw plugins install ./rappi-claude-plugin
```

#### 3. Install skills

Copy the skills to your OpenClaw workspace:

```bash
cp -r skills/* ~/.openclaw/workspace/skills/
```

#### 4. Authenticate and restart

```bash
uv run rappi auth login        # Browser auth (see below for headless)
openclaw gateway restart
```

### Option B: Remote MCP Server

Connect OpenClaw to a deployed MCP server over HTTP. Best for shared setups or when you don't want Python installed on the OpenClaw machine.

#### 1. Deploy the MCP server

Deploy to Railway (or any host). See the main [README deployment section](../README.md#deployment) for full instructions.

Quick version:
1. Fork the repo, connect to [Railway](https://railway.com)
2. Set env vars: `MCP_TRANSPORT=sse`, `RAPPI_TOKEN`, `RAPPI_DEVICE_ID`, `RAPPI_COUNTRY`
3. Verify: `curl https://your-app.up.railway.app/health` returns `ok`

#### 2. Generate and install the OpenClaw bundle

```bash
uv run rappi build-plugin build --target openclaw --url https://your-app.up.railway.app/sse
openclaw plugins install ~/Desktop/rappi-openclaw-plugin.zip
openclaw gateway restart
```

## Authentication

### With a browser (interactive)

```bash
uv run rappi auth login              # Colombia (default)
uv run rappi auth login --country mx # Mexico
```

This opens a browser window for Rappi's login flow (phone number + OTP).

### Headless servers (no browser — SSH, VPS, etc.)

Use the `token` command to set credentials directly:

```bash
uv run rappi auth token <RAPPI_TOKEN> <DEVICE_ID>
uv run rappi auth token <RAPPI_TOKEN> <DEVICE_ID> --country mx  # Mexico
```

**How to get your token and device ID:**

1. On a machine where you've already logged in via browser:
   ```bash
   cat ~/.rappi/config.json
   # Copy the "token" and "device_id" values
   ```

2. Or capture from Rappi's website via browser DevTools:
   - Open rappi.com.co → DevTools → Network tab
   - Look for any API request's `Authorization` header (the Bearer token)
   - Look for the `x-device-id` header (the device ID)

### Verify authentication

```bash
uv run rappi auth status
```

## What Gets Mapped

| Plugin Component | OpenClaw Mapping | Status |
|---|---|---|
| `skills/order-food/SKILL.md` | OpenClaw skill | Works |
| `skills/rappi-search/SKILL.md` | OpenClaw skill | Works |
| `skills/rappi-reorder/SKILL.md` | OpenClaw skill | Works |
| `skills/rappi-suggest/SKILL.md` | OpenClaw skill | Works |
| `.mcp.json` (40 tools) | MCP tools (`rappi__*`) | Works |
| `agents/rappi-agent.md` | Not mapped | OpenClaw ignores agents |

## Tool Naming

MCP tools have different naming conventions per platform:

| Claude Code / Cowork | OpenClaw |
|---|---|
| `mcp__rappi__search_restaurants` | `rappi__search_restaurants` |
| `mcp__rappi__add_to_cart` | `rappi__add_to_cart` |
| `mcp__rappi__checkout` | `rappi__checkout` |

The skills reference tools using `mcp__rappi__*` (Claude convention). OpenClaw's bundle mapper translates these automatically. If you're writing custom prompts for OpenClaw, use `rappi__<tool_name>` directly.

## Configuration

### Country

Set your country when authenticating:

```bash
uv run rappi auth login --country co   # Colombia
uv run rappi auth login --country mx   # Mexico
# Or with direct token:
uv run rappi auth token <token> <device_id> --country mx
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
# Or on headless:
uv run rappi auth token <new_token> <device_id>
```

For remote deployments, update `RAPPI_TOKEN` in your Railway dashboard.

### Browser auth fails on headless server

Use the `token` command instead — see [Headless servers](#headless-servers-no-browser--ssh-vps-etc).

### 403 errors from Rappi API

The `app-version` header may be outdated. See [Updating the app-version Header](../README.md#updating-the-app-version-header).

## Differences from Claude

| Feature | Claude | OpenClaw |
|---|---|---|
| Skills | Auto-triggered by description | Auto-triggered by description |
| MCP Tools | 40 tools via `mcp__rappi__*` | 40 tools via `rappi__*` |
| Agent | `rappi-agent.md` (Sonnet) | Not supported (agents ignored) |
| Memory | Full (SQLite local) | Full (SQLite local) |
| Remote deploy | Railway + Cowork zip | Railway + bundle install |
| Auth | `rappi auth login` | `rappi auth login` or `rappi auth token` |
| Install | Auto-discovered from `.mcp.json` | `./install-openclaw.sh` or manual |
