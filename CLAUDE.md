# CLAUDE.md — Rappi Claude Plugin

## What This Project Is

A **Claude plugin** for ordering food from Rappi (Colombia's leading delivery platform). The plugin gives Claude the ability to search restaurants, browse menus, manage a cart, place orders, and track deliveries — with a local memory system that learns the user's preferences over time.

The plugin consists of: **skills** (what Claude follows), **MCP tools** (what Claude calls), **an agent** (specialized ordering intelligence), **memory** (SQLite persistence), and a **CLI** (terminal alternative).

## Quick Reference

```bash
uv sync                           # Install dependencies
uv run rappi auth login           # Authenticate (opens browser)
claude                            # Claude Code (auto-discovers plugin from .mcp.json)
uv run rappi go                   # Terminal ordering (alternative)
uv run rappi-mcp                  # Start MCP server standalone (stdio)
MCP_TRANSPORT=sse uv run rappi-mcp  # Start MCP server as HTTP (for Railway)
uv run pytest tests/ -q           # Run 196 automated tests
```

## Plugin Structure

```
rappi-claude-plugin/
├── .claude-plugin/plugin.json   # Plugin manifest (required)
├── .mcp.json                    # Auto-registers MCP server (stdio, local)
├── .claude/settings.json        # SessionStart auth check hook
│
├── skills/                      # Claude skills (slash commands)
│   ├── order-food/SKILL.md      # /order-food — full ordering workflow
│   ├── rappi-search/SKILL.md    # /rappi-search — quick product lookup
│   ├── rappi-reorder/SKILL.md   # /rappi-reorder — reorder from history
│   └── rappi-suggest/SKILL.md   # /rappi-suggest — smart suggestions from taste profile
│
├── agents/
│   └── rappi-agent.md           # Specialized ordering agent (Sonnet)
│
├── src/rappi/                   # Plugin engine
│   ├── mcp/server.py            # 38 MCP tools (stdio + SSE transport)
│   ├── services/                # Shared business logic
│   │   ├── auth.py              # Authentication, profile
│   │   ├── address.py           # Delivery addresses
│   │   ├── search.py            # Unified search + CPG product search
│   │   ├── store.py             # Store detail, menu, toppings, catalog
│   │   ├── cart.py              # Cart CRUD (compound IDs, 3 prices)
│   │   ├── checkout.py          # Checkout, tip, payment, place order
│   │   ├── order.py             # Order tracking, resume, cost breakdown
│   │   ├── home.py              # Homepage verticals discovery
│   │   ├── dynamic.py           # Store aisles/categories (dynamic content)
│   │   └── account.py           # Favorites API, credits, active orders
│   ├── memory/                  # SQLite + optional embeddings + intelligence engine
│   ├── cli/                     # Terminal interface
│   ├── models/                  # Pydantic data models
│   ├── constants.py             # ALL API endpoints, headers, app versions
│   └── client.py                # Rappi API client
│
├── Dockerfile                   # Railway deployment (Python 3.12 + uv)
├── railway.json                 # Railway config (healthcheck at /health)
├── API_ENDPOINTS.md             # Full Rappi API reference (from browser capture)
└── tests/                       # 196 automated tests
```

## How the Pieces Connect

```
Claude Code / Desktop (local)     Claude Cowork (web)
        |                                |
    stdio transport               SSE over HTTP (Railway)
        |                                |
        +---------- MCP Server ----------+
                  38 tools
                      |
        +------ Services Layer ------+---- CLI (terminal alternative)
                      |
              +-------+-------+
              |               |
        Rappi API        Memory (SQLite)
        (internet)       (~/.rappi/rappi.db)
```

**Skills** tell Claude the workflow. **MCP tools** give Claude capabilities. **Services** contain business logic (shared by MCP and CLI). **Memory** makes it personal. The server runs locally (stdio) or on Railway (SSE) — same code, different transport.

## Key Files

| File | Purpose |
|------|---------|
| `.claude-plugin/plugin.json` | Plugin manifest — name, version, author |
| `.mcp.json` | Auto-registers `rappi-mcp` server in Claude Code |
| `skills/order-food/SKILL.md` | Main skill — triggers on food/ordering requests |
| `agents/rappi-agent.md` | Specialized agent with full Rappi API knowledge |
| `skills/rappi-suggest/SKILL.md` | Smart suggestions skill — taste-aware recommendations |
| `src/rappi/mcp/server.py` | 38 MCP tools (the plugin's capabilities) |
| `src/rappi/services/home.py` | Homepage verticals discovery |
| `src/rappi/services/dynamic.py` | Store aisles/categories (dynamic content) |
| `src/rappi/services/account.py` | Favorites, credits, active orders |
| `API_ENDPOINTS.md` | Full Rappi API reference (captured from browser) |
| `src/rappi/memory/manager.py` | MemoryManager facade (the plugin's brain) |
| `src/rappi/memory/intelligence.py` | IntelligenceEngine — taste profile + recommendations |
| `src/rappi/models/intelligence.py` | TasteProfile, Recommendation models |
| `src/rappi/constants.py` | ALL API endpoints and headers — single source of truth |
| `src/rappi/services/cart.py` | Most complex service — compound IDs, toppings, prices |
| `src/rappi/services/store.py` | Store detail + menu. Non-restaurant stores use search |
| `src/rappi/cli/interactive.py` | `rappi go` guided terminal flow |
| `src/rappi/memory/db.py` | SQLite schema DDL and migrations |

## Skills

Skills are markdown files with YAML frontmatter. Claude auto-invokes them based on the `description` field.

| Skill | Trigger | Allowed Tools |
|-------|---------|---------------|
| `/order-food` | Food ordering, "I'm hungry", mentions Rappi | All 38 MCP tools |
| `/rappi-search` | "Find restaurants", "search for pizza", "find Turbo stores" | All 38 MCP tools |
| `/rappi-reorder` | "Order the same", "reorder" | All 38 MCP tools |
| `/rappi-suggest` | "What should I eat?", "suggest something" | All 38 MCP tools |

### Adding a New Skill

1. Create `skills/<name>/SKILL.md`
2. Add frontmatter: `name`, `description`, `allowed-tools`
3. Write workflow instructions in the body
4. Auto-registers — no other files to change

### MCP Tool Names in Skills

Use namespaced format: `mcp__rappi__<tool_name>`. Wildcard: `mcp__rappi__*`.

## API Gotchas

These are critical and easy to get wrong:

1. **Store detail doesn't include menu**. Menu is at a SEPARATE endpoint: `/api/restaurant-bus/store/{id}/menu`. `get_store_detail()` fetches both and merges.

2. **Non-restaurant stores (Turbo, markets) have no menu endpoint**. Products only via unified search. Use `search_store_products()`.

3. **Cart product IDs must be compound**: `"storeId_productId"` (string), not just the product ID.

4. **Three price fields mandatory**: `price`, `real_price`, `markup_price` must ALL be set. API silently accepts $0.

5. **Toppings must be objects**: `{id, description, units, price}` — not bare integers.

6. **Trailing slashes required** on store detail and toppings endpoints.

7. **API returns HTML in fields** — `return_key` from checkout wrapped in `<b>` tags. Strip via `strip_html()`.

8. **Checkout response has `None` values** — filter separator rows when displaying.

9. **`app-version` header** changes with Rappi deploys. Update hash in `constants.py` from browser DevTools if 403s appear.

## Store Types

| Type | Menu Source | Cart store_type | Examples |
|------|------------|-----------------|---------|
| `restaurant` | `/api/restaurant-bus/store/{id}/menu` | `"restaurant"` | El Corral, McDonald's |
| `turbo` | Unified search (no menu) | `"turbo"` | Turbo convenience |
| `larebaja` | Unified search | varies | La Rebaja pharmacy |
| Other markets | Unified search | varies | Carulla, Exito |

`StoreDetail.is_restaurant` → which browse flow. `StoreDetail.effective_store_type` → cart/checkout URL type.

## Memory System

SQLite at `~/.rappi/rappi.db`. All writes best-effort — never blocks ordering.

**Tables**: orders, order_items, product_cache, store_cache, preferences, search_history, embeddings.

**Repositories** (`memory/repositories/`): One per domain, parameterized SQL, no ORM.

**Embeddings**: Optional. Enable via `preferences.set("embeddings.enabled", True)`. `OpenAIEmbeddingProvider` (text-embedding-3-small). Vectors as BLOB. Cosine similarity in pure Python.

## Intelligence Engine

`memory/intelligence.py` — `IntelligenceEngine` computes derived insights from raw data.

**Taste Profile** (`compute_taste_profile()`): Aggregates all order history into:
- Category preferences (% breakdown from product_cache categories)
- Store type preferences (restaurant vs turbo vs market %)
- Price range (avg order total, avg item price, min/max)
- Time patterns (hour-of-day slots, day-of-week distribution, peaks)
- Topping preferences (parsed from toppings_json, counted)
- Top products/stores (by frequency)
- Spending summary (total, avg, tip, orders/week)
- Taste vector (average embedding of all ordered products — only with embeddings enabled)

**Recommendations** (`get_recommendations()`): Scored suggestions:
- `usual` — products ordered 3+ times from same store (confidence = times/10)
- `time_based` — stores ordered from at current hour (confidence = count/total*5)
- `similar_product` — products similar to taste vector, not yet ordered (**embeddings only**)
- `new_store` — unvisited stores matching preferred type (confidence = 0.3)

**Menu Scoring** (`score_menu_items(store_id, products)`):
- With embeddings: cosine similarity of each item vs taste vector
- Without: order-frequency scoring (how many times user ordered each product)

**SQL vs Embeddings — when each is used:**
- SQL handles: aggregations, counting, time patterns, "the usual", spending, favorites
- Embeddings handle: similarity ("like what I usually get"), menu scoring, semantic search, cross-store product matching
- Everything works without embeddings. Embeddings add similarity-based intelligence on top.

## Adding New Features

**New skill**: Create `skills/<name>/SKILL.md` with frontmatter + instructions.

**New MCP tool**: Add `@mcp.tool()` in `mcp/server.py`. Use `_client_with_memory()` for API+memory, `MemoryManager()` for memory-only.

**New API endpoint**: Add to `constants.py:Endpoints`. Create/update service. Add model if needed.

**New CLI command**: Create file in `cli/`, register in `cli/__init__.py`.

**New memory table**: Add DDL to `memory/db.py`. Increment `SCHEMA_VERSION`. Create repository. Add to `MemoryManager.__aenter__`.

## Testing

```bash
# All 196 automated tests
uv run pytest tests/ -q

# Verify tool count (should be 38)
uv run python -c "from rappi.mcp.server import mcp; print(f'{len(mcp._tool_manager._tools)} tools')"

# Test a tool against live API
uv run python -c "
import asyncio
from rappi.mcp.server import explore_verticals
r = asyncio.run(explore_verticals())
for v in r['verticals'][:5]: print(f'  {v[\"id\"]}: {v[\"name\"]}')
"

# MCP inspector (browser UI)
npx @modelcontextprotocol/inspector uv run rappi-mcp

# CLI smoke test
uv run rappi auth status
uv run rappi search "pizza"
uv run rappi store browse
```

See [TESTING.md](TESTING.md) for the full 22-section manual testing checklist.

## Remote Deployment (Railway + Cowork)

The MCP server supports remote deployment for use with Claude Cowork (web), Claude Desktop, and any MCP client that speaks HTTP.

### Architecture

```
Claude Code (local)     → stdio transport  → rappi-mcp (local process)
Claude Desktop (local)  → stdio transport  → rappi-mcp (local process)
Cowork / Web clients    → SSE over HTTP    → Railway (rappi-mcp container)
```

### How the Remote Server Works

`src/rappi/mcp/server.py` detects `MCP_TRANSPORT` env var at import time:
- **`stdio`** (default): Runs as a local subprocess — used by Claude Code and Claude Desktop.
- **`sse`**: Runs uvicorn on `0.0.0.0:$PORT` with SSE transport — used for Railway/cloud deployment.

**Critical pattern** (learned the hard way):

1. **`transport_security` must be set in the `FastMCP()` constructor**, not on `mcp.settings` later. FastMCP's DNS rebinding protection is configured at construction time. If you set it after, the SSE transport creates its own security validator from the original settings and ignores your changes.

2. **Run uvicorn directly** with a custom Starlette app (don't use `mcp.run()`). This gives control over host/port binding and lets you add a `/health` endpoint for Railway healthchecks.

3. **Use SSE transport for Cowork**, not streamable-http. Cowork connects to the `/sse` endpoint. The `.mcp.json` in the Cowork plugin uses `"type": "http"` with the `/sse` URL — this is correct and matches how other working MCP servers (e.g., ESPN Fantasy) are configured.

4. **Auth is handled via env vars**, not OAuth. The Rappi token is set as `RAPPI_TOKEN` in Railway. Cowork connects to the MCP server without OAuth — no auth handshake needed. The server authenticates to Rappi's API using the pre-configured token.

### Server Setup Pattern

```python
# At module level — BEFORE FastMCP() is created
transport = os.environ.get("MCP_TRANSPORT", "stdio")
mcp_kwargs = dict(name="rappi", instructions="...")

if transport in ("sse", "streamable-http", "http"):
    from mcp.server.transport_security import TransportSecuritySettings
    mcp_kwargs["transport_security"] = TransportSecuritySettings(
        enable_dns_rebinding_protection=False,  # Required for cloud deploy
    )

mcp = FastMCP(**mcp_kwargs)

# In main() — run uvicorn directly for HTTP transports
def main():
    if transport in ("sse", "streamable-http", "http"):
        from starlette.applications import Starlette
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route, Mount
        import uvicorn

        host = os.environ.get("MCP_HOST", "0.0.0.0")
        port = int(os.environ.get("PORT", os.environ.get("MCP_PORT", "8000")))

        def health(_request):
            return PlainTextResponse("ok")

        mcp_app = mcp.sse_app()
        app = Starlette(routes=[
            Route("/health", health),
            Mount("/", app=mcp_app),
        ])
        uvicorn.run(app, host=host, port=port)
    else:
        mcp.run(transport=transport)
```

### Railway Configuration

**Environment variables** (set in Railway dashboard):
| Variable | Value | Purpose |
|----------|-------|---------|
| `MCP_TRANSPORT` | `sse` | Enables HTTP transport |
| `RAPPI_TOKEN` | `ft.xxxxx` | Rappi auth token (from `~/.rappi/config.json`) |
| `RAPPI_DEVICE_ID` | UUID | Device ID (from `~/.rappi/config.json`) |
| `RAPPI_LAT` | `4.624335` | Delivery latitude (from `rappi address set`) |
| `RAPPI_LNG` | `-74.063644` | Delivery longitude (from `rappi address set`) |
| `PORT` | (auto-set by Railway) | Railway injects this |

**Files**: `Dockerfile` (Python 3.12 + uv), `railway.json` (healthcheck at `/health`).

**Token refresh**: Rappi tokens expire. Re-authenticate locally (`rappi auth login`), then update `RAPPI_TOKEN` in Railway.

### Cowork Plugin

The Cowork plugin is a zip uploaded to Claude Cowork (Customize > Plugins):

```
rappi-cowork-plugin.zip
├── .claude-plugin/plugin.json     # Plugin manifest
├── .mcp.json                      # Points to Railway SSE endpoint
├── skills/                        # Auto-activated workflow instructions
│   ├── order-food/SKILL.md
│   ├── rappi-search/SKILL.md
│   ├── rappi-reorder/SKILL.md
│   └── rappi-suggest/SKILL.md
└── agents/
    └── rappi-agent.md
```

**`.mcp.json` for Cowork** (different from local — generated by `rappi build-plugin`):
```json
{
  "mcpServers": {
    "rappi": {
      "type": "http",
      "url": "https://<your-railway-app>.up.railway.app/sse"
    }
  }
}
```

**Connector setup in Cowork**: Add as remote MCP connector — URL only, no OAuth.

### Local `.mcp.json` (Claude Code / Desktop)

The repo's `.mcp.json` uses stdio for local development:
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

These two configs coexist — local `.mcp.json` for Claude Code, Cowork zip with HTTP `.mcp.json` for web.

## Dependencies

Core: `httpx`, `typer`, `rich`, `pydantic`, `mcp`, `playwright`, `aiosqlite`
Optional: `openai` (for embeddings)

## Data Locations

| Path | Contents |
|------|----------|
| `~/.rappi/config.json` | Auth token, device ID, coordinates |
| `~/.rappi/rappi.db` | Memory database (orders, cache, preferences) |
| `.claude-plugin/plugin.json` | Plugin manifest |
| `.mcp.json` | MCP server config |
| `skills/` | Plugin skills |
| `agents/` | Plugin agents |
| `.claude/settings.json` | Project hooks |
