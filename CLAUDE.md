# CLAUDE.md — Project Guide for AI Assistants

## What This Project Is

Rappi CLI is a Python CLI + MCP server that wraps Rappi's internal (undocumented) food delivery API. It lets users order food from the terminal and enables AI assistants to order food via MCP tools. Colombia-focused (prices in COP, Bogota default location).

## Quick Reference

```bash
uv sync                           # Install dependencies
uv run rappi --help               # CLI help
uv run rappi go                   # Interactive ordering
uv run rappi auth login           # Browser auth
uv run rappi-mcp                  # Start MCP server (stdio)
uv run pytest                     # Run tests
```

## Architecture

**Shared services pattern**: CLI, MCP, and interactive mode all call the same async service functions in `src/rappi/services/`. Never duplicate business logic across interfaces.

```
CLI (typer) ──┐
MCP (fastmcp) ┼──→ Services (async) ──→ RappiClient (httpx) ──→ Rappi API
Interactive ──┘         │
                        └──→ MemoryManager (aiosqlite) ──→ ~/.rappi/rappi.db
```

**RappiClient** (`src/rappi/client.py`): Async HTTP client. Injects auth headers. Raises `TokenExpiredError` on 401, `RappiAPIError` on other errors. Has optional `memory: MemoryManager` field.

**MemoryManager** (`src/rappi/memory/manager.py`): Facade for SQLite persistence. All memory writes are best-effort (try/except pass) — never block the ordering flow.

## Key Files

| File | Purpose |
|------|---------|
| `src/rappi/constants.py` | ALL API endpoints and headers — single source of truth |
| `src/rappi/client.py` | HTTP client with auth injection |
| `src/rappi/services/cart.py` | Most complex service — compound IDs, topping objects, price fields |
| `src/rappi/services/store.py` | Store detail + menu (separate API calls). Non-restaurant stores use search |
| `src/rappi/cli/interactive.py` | The `rappi go` guided flow (~500 lines) |
| `src/rappi/mcp/server.py` | 22 MCP tools |
| `src/rappi/memory/manager.py` | MemoryManager facade |
| `src/rappi/memory/db.py` | Schema DDL and migrations |

## API Gotchas

These are critical and easy to get wrong:

1. **Store detail doesn't include menu**. The menu is at a SEPARATE endpoint: `/api/restaurant-bus/store/{id}/menu`. `get_store_detail()` in `services/store.py` fetches both and merges them.

2. **Non-restaurant stores (Turbo, markets) have no menu endpoint**. Products are only discoverable via the unified search API. Use `search_store_products()`.

3. **Cart product IDs must be compound format**: `"storeId_productId"` (string), not just the product ID.

4. **Three price fields are mandatory**: `price`, `real_price`, `markup_price` must ALL be set. The API silently accepts $0 if missing.

5. **Toppings must be objects**: `{id, description, units, price}` — not bare integers.

6. **Trailing slashes required** on store detail and toppings endpoints. Without them you get 404.

7. **The API returns HTML in some fields** — `return_key` from checkout comes wrapped in `<b>` tags. We strip HTML via `utils/pricing.py:strip_html()`.

8. **Checkout response has `None` values and separator rows** — filter them out when displaying.

9. **`app-version` header** contains a commit hash that changes when Rappi deploys. If requests start failing with 403, update the hash in `constants.py` from browser DevTools.

## Store Types

| Type | Menu Source | Cart store_type | Example |
|------|------------|-----------------|---------|
| `restaurant` | `/api/restaurant-bus/store/{id}/menu` (corridors) | `"restaurant"` | El Corral, McDonald's |
| `turbo` | Unified search (no menu endpoint) | `"turbo"` | Turbo convenience stores |
| `larebaja` | Unified search | varies | La Rebaja pharmacy |
| Other markets | Unified search | varies | Carulla, Exito |

The `StoreDetail.effective_store_type` property returns the correct type for cart/checkout URLs. The `StoreDetail.is_restaurant` property tells you which browse flow to use.

## Memory System

SQLite at `~/.rappi/rappi.db`. Schema version tracked in `schema_version` table. Migrations in `memory/db.py`.

**Tables**: orders, order_items, product_cache, store_cache, preferences, search_history, embeddings.

**Repositories** (in `memory/repositories/`): One per domain. Accept `aiosqlite.Connection`, use parameterized SQL (no ORM).

**Embeddings** are optional. Enabled via `preferences.set("embeddings.enabled", True)`. Provider abstraction in `memory/embeddings.py`. Currently only `OpenAIEmbeddingProvider` (text-embedding-3-small). Vector storage as BLOB (packed float32). Cosine similarity in pure Python.

## Adding a New Feature

**New API endpoint**: Add path to `constants.py:Endpoints`. Create/update service in `services/`. Add model in `models/` if needed.

**New CLI command**: Create file in `cli/`, register in `cli/__init__.py` with `app.add_typer()`.

**New MCP tool**: Add `@mcp.tool()` function in `mcp/server.py`. Use `async with _client_with_memory() as (client, memory):` for tools needing both API + memory. Use `async with MemoryManager() as memory:` for memory-only tools. Use `async with RappiClient() as client:` for API-only tools.

**New memory table**: Add DDL to `memory/db.py:SCHEMA_V1`. Increment `SCHEMA_VERSION`. Create repository in `memory/repositories/`. Add to `MemoryManager.__aenter__`.

## Testing

```bash
# Test MCP server tools load
uv run python -c "from rappi.mcp.server import mcp; print([t.name for t in mcp._tool_manager._tools.values()])"

# Test memory system
uv run python -c "
import asyncio
from rappi.memory import MemoryManager
async def t():
    async with MemoryManager() as m:
        print(await m.get_memory_summary())
asyncio.run(t())
"

# Test MCP with inspector
npx @modelcontextprotocol/inspector uv run rappi-mcp
```

## Claude Code Plugin

This project is a Claude Code Plugin. The plugin files live alongside the source code.

### Plugin Structure

| File | Purpose |
|------|---------|
| `.claude-plugin/plugin.json` | Manifest — name, version, author. Required for plugin recognition. |
| `.mcp.json` | Auto-registers `rappi-mcp` as an MCP server when plugin is loaded. Claude Code reads this automatically. |
| `skills/order-food/SKILL.md` | Main skill — `/order-food`. Triggers on food/ordering requests. Contains full workflow instructions for Claude. |
| `skills/rappi-search/SKILL.md` | Search skill — `/rappi-search <query>`. Lightweight product lookup. |
| `skills/rappi-reorder/SKILL.md` | Reorder skill — `/rappi-reorder`. Uses memory to re-add past order items. |
| `agents/rappi-agent.md` | Specialized Sonnet agent with deep Rappi knowledge. Used by skills for complex flows. |
| `.claude/settings.json` | SessionStart hook — checks auth status when project opens. |

### How Skills Work

Skills are markdown files with YAML frontmatter. The frontmatter controls:
- `name` — slash command name (`/order-food`)
- `description` — Claude uses this to decide when to auto-invoke the skill
- `allowed-tools` — which tools the skill can use (MCP tools, Bash, Read, etc.)
- `argument-hint` — shown in autocomplete

The markdown body is the **prompt** Claude follows when the skill is invoked. It contains step-by-step instructions, error handling, and formatting rules.

### Adding a New Skill

1. Create `skills/<skill-name>/SKILL.md`
2. Add frontmatter with `name`, `description`, `allowed-tools`
3. Write the prompt body with workflow instructions
4. The skill auto-registers — no changes to other files needed

### MCP Tool Names in Skills

When referencing MCP tools in skills, use the namespaced format: `mcp__rappi__<tool_name>`. Examples:
- `mcp__rappi__search_restaurants`
- `mcp__rappi__add_to_cart`
- `mcp__rappi__checkout`
- Wildcard: `mcp__rappi__*` (all Rappi tools)

### Claude Desktop

The MCP server is also configured for Claude Desktop at:
`~/Library/Application Support/Claude/claude_desktop_config.json`

Restart Claude Desktop after changes. The 22 MCP tools appear as available tools in conversations.

## Dependencies

Core: `httpx`, `typer`, `rich`, `pydantic`, `mcp`, `playwright`, `aiosqlite`
Optional: `openai` (for embeddings — `uv add openai`)

## Data Locations

| Path | Contents |
|------|----------|
| `~/.rappi/config.json` | Auth token, device ID, lat/lng |
| `~/.rappi/rappi.db` | SQLite memory database |
| `~/.rappi/rappi.db-wal` | SQLite write-ahead log (auto-managed) |
| `.claude-plugin/plugin.json` | Plugin manifest |
| `.mcp.json` | MCP server config (auto-loaded by Claude Code) |
| `skills/` | Claude Code skills (slash commands) |
| `agents/` | Claude Code agent definitions |
| `.claude/settings.json` | Project-level hooks |
| `~/Library/Application Support/Claude/claude_desktop_config.json` | Claude Desktop MCP config |
| Project `.venv/` | Python virtual environment |
