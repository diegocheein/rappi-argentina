# CLAUDE.md — Rappi Claude Plugin

## What This Project Is

A **Claude plugin** for ordering food from Rappi (Colombia's leading delivery platform). The plugin gives Claude the ability to search restaurants, browse menus, manage a cart, place orders, and track deliveries — with a local memory system that learns the user's preferences over time.

The plugin consists of: **skills** (what Claude follows), **MCP tools** (what Claude calls), **an agent** (specialized ordering intelligence), **memory** (SQLite persistence), and a **CLI** (terminal alternative).

## Quick Reference

```bash
uv sync                           # Install dependencies
uv run rappi auth login           # Authenticate (opens browser)
claude --plugin-dir .             # Load plugin in Claude Code
uv run rappi go                   # Terminal ordering (alternative)
uv run rappi-mcp                  # Start MCP server standalone
```

## Plugin Structure

```
rappi-claude-plugin/
├── .claude-plugin/plugin.json   # Plugin manifest (required)
├── .mcp.json                    # Auto-registers MCP server
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
└── src/rappi/                   # Plugin engine
    ├── mcp/server.py            # 25 MCP tools
    ├── services/                # Shared business logic
    ├── memory/                  # SQLite + optional embeddings + intelligence engine
    ├── cli/                     # Terminal interface
    ├── models/                  # Pydantic data models
    └── client.py                # Rappi API client
```

## How the Pieces Connect

```
Skills & Agent          (what Claude follows — workflow instructions)
      |
      v
MCP Tools (25)          (what Claude calls — structured JSON in/out)
      |
      +------ Services Layer ------+---- CLI (terminal alternative)
                  |
          +-------+-------+
          |               |
    Rappi API        Memory (SQLite)
    (internet)       (~/.rappi/rappi.db)
```

**Skills** tell Claude the workflow. **MCP tools** give Claude capabilities. **Services** contain business logic (shared by MCP and CLI). **Memory** makes it personal.

## Key Files

| File | Purpose |
|------|---------|
| `.claude-plugin/plugin.json` | Plugin manifest — name, version, author |
| `.mcp.json` | Auto-registers `rappi-mcp` server in Claude Code |
| `skills/order-food/SKILL.md` | Main skill — triggers on food/ordering requests |
| `agents/rappi-agent.md` | Specialized agent with full Rappi API knowledge |
| `skills/rappi-suggest/SKILL.md` | Smart suggestions skill — taste-aware recommendations |
| `src/rappi/mcp/server.py` | 25 MCP tools (the plugin's capabilities) |
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
| `/order-food` | Food ordering, "I'm hungry", mentions Rappi | All 22 MCP tools + Bash |
| `/rappi-search` | "Find restaurants", "search for pizza" | Search + menu tools |
| `/rappi-reorder` | "Order the same", "reorder" | History + cart + checkout tools |

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
# Plugin loads
uv run rappi --help

# MCP tools
uv run python -c "from rappi.mcp.server import mcp; print([t.name for t in mcp._tool_manager._tools.values()])"

# Memory
uv run python -c "
import asyncio
from rappi.memory import MemoryManager
async def t():
    async with MemoryManager() as m:
        print(await m.get_memory_summary())
asyncio.run(t())
"

# MCP inspector
npx @modelcontextprotocol/inspector uv run rappi-mcp
```

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
