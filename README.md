# Rappi CLI

A command-line interface and MCP server for Rappi, Colombia's leading food delivery platform. Order food from your terminal or let AI assistants order for you.

## Features

- **Interactive ordering** (`rappi go`) — guided flow from search to checkout, no IDs to memorize
- **22 MCP tools** — plug into Claude Desktop so AI can search, browse, order, and track deliveries
- **Browser-based auth** — opens Chromium, you log in normally, token captured automatically
- **All store types** — restaurants, Turbo (convenience), markets, pharmacies
- **Local memory** — SQLite database remembers your orders, favorites, preferences, and search history
- **Optional semantic search** — enable OpenAI embeddings to search by meaning ("that spicy chicken thing")
- **Rich terminal UI** — tables, panels, color-coded status, live order tracking

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Install

```bash
git clone https://github.com/your-username/rappi-cli.git
cd rappi-cli
uv sync
uv run playwright install chromium
```

### Authenticate

```bash
# Opens a browser — log in with your phone + WhatsApp OTP
uv run rappi auth login

# Or paste a token manually (from browser DevTools)
uv run rappi auth login --token "ft.gAAAAA..."
```

### Order Food

```bash
# Interactive mode — the easiest way
uv run rappi go

# Or use individual commands
uv run rappi search "hamburguesa"
uv run rappi store detail 900004197
uv run rappi cart add 900004197 3523055
uv run rappi order checkout
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `rappi go` | Interactive ordering session |
| `rappi auth login` | Authenticate (browser or manual token) |
| `rappi auth status` | Show profile and Prime status |
| `rappi auth logout` | Clear saved token |
| `rappi address list` | List delivery addresses |
| `rappi address set <id>` | Switch active address |
| `rappi search <query>` | Search restaurants and products |
| `rappi store browse` | Browse nearby restaurants |
| `rappi store detail <id>` | View store info and menu |
| `rappi store toppings <store> <product>` | View product customizations |
| `rappi cart show` | View cart contents |
| `rappi cart add <store> <product>` | Add item with interactive toppings |
| `rappi cart remove <store> <product>` | Remove item from cart |
| `rappi order checkout` | Review and place order |
| `rappi order list` | View active and past orders |
| `rappi order track` | Live order tracking |
| `rappi history` | View order history from memory |
| `rappi history detail <id>` | View order details |
| `rappi history stores` | Most-ordered-from stores |
| `rappi favorites` | List favorite stores |
| `rappi favorites add <id>` | Save a favorite |
| `rappi favorites remove <id>` | Remove a favorite |
| `rappi prefs` | View preferences |
| `rappi prefs set tip 5000` | Set default tip |
| `rappi prefs set diet vegetarian` | Set dietary restrictions |
| `rappi prefs set allergy "peanuts"` | Set allergies |

## Interactive Mode (`rappi go`)

The interactive session guides you through the full ordering flow:

```
Welcome, Gabriel! | Prime

Delivering to: House — Diagonal 108 A # 08 A - 10
Last order: El Corral — $38.000
3 orders in history

What are you looking for?
  1. Search (restaurants, stores, products)
  2. Browse nearby restaurants
  3. Reorder from history
  4. Pick a favorite
```

Each step flows naturally to the next. Search results are numbered — pick by number. Toppings are prompted interactively. The cart total updates in real time. After checkout, you can track your order live.

## MCP Server (for Claude Desktop)

The MCP server exposes 22 tools that let AI assistants interact with Rappi on your behalf.

### Setup

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "rappi": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/rappi-cli", "rappi-mcp"]
    }
  }
}
```

### Available Tools

**Context & Auth**
- `get_ordering_context` — user state, address, cart, orders, memory summary
- `auth_status` — check token validity

**Addresses**
- `list_delivery_addresses` / `set_delivery_address`

**Search & Browse**
- `search_restaurants(query)` — search all store types
- `search_in_store(store_id, query)` — search within a specific store (Turbo, markets)
- `browse_restaurants(offset, limit)` — nearby restaurants

**Menu**
- `get_restaurant_menu(store_id)` — full menu by category
- `get_product_toppings(store_id, product_id)` — customization options

**Cart**
- `add_to_cart(store_id, product_id, quantity, topping_ids)` — validates toppings
- `view_cart` / `remove_from_cart(store_id, product_id)`

**Checkout**
- `checkout(tip_amount, confirm)` — preview (confirm=false) then place (confirm=true)
- `get_order_status` — active and cancelled orders

**Memory**
- `get_order_history(limit)` — past orders with items
- `get_favorites` / `add_favorite` / `remove_favorite`
- `quick_reorder(order_id)` — re-add items from a past order to cart
- `get_preferences` / `set_preference(key, value)`
- `smart_search(query)` — semantic search across memory (with embeddings) or keyword fallback

### Typical AI Workflow

```
User: "Order me a burger from that place I liked"

AI calls: get_ordering_context    -> sees order history
AI calls: get_order_history       -> finds past burger order from El Corral
AI calls: quick_reorder(order_id) -> re-adds items
AI calls: checkout(confirm=false) -> shows preview
User: "Looks good, place it"
AI calls: checkout(tip_amount=3000, confirm=true) -> order placed
```

## Memory System

All data is stored locally in a SQLite database at `~/.rappi/rappi.db`. Nothing is sent to external services (unless you enable OpenAI embeddings).

### What's Remembered

| Data | How It Gets There | What It Enables |
|------|-------------------|-----------------|
| **Order history** | Recorded after each successful checkout | "What did I order last time?", reordering |
| **Product cache** | Auto-cached when you search or browse menus | Faster lookups, smart search |
| **Store cache** | Auto-cached from search results and store views | Favorite store names, quick access |
| **Search history** | Recorded on every search | Autocomplete suggestions, popular queries |
| **Preferences** | Set via `rappi prefs set` or MCP `set_preference` | Default tip, dietary restrictions, allergies |
| **Favorites** | Set via `rappi favorites add` or MCP `add_favorite` | Quick store access in interactive mode |

### Database Schema

```
~/.rappi/
├── config.json   # Auth token, device ID, coordinates
└── rappi.db      # SQLite database
    ├── orders          # Past orders with store info
    ├── order_items     # Line items per order
    ├── product_cache   # Cached products with TTL
    ├── store_cache     # Cached store metadata with TTL
    ├── preferences     # Key-value user preferences
    ├── search_history  # Past search queries
    └── embeddings      # Optional: vector embeddings for semantic search
```

All memory writes are **best-effort** — if the database fails for any reason, the ordering flow continues normally. Memory enhances the experience but is never required.

### Reset Memory

```bash
# Delete the database (preferences, history, cache — everything)
rm ~/.rappi/rappi.db

# Delete auth token only
uv run rappi auth logout

# Delete everything
rm -rf ~/.rappi/
```

## Embeddings (Optional)

By default, the `smart_search` tool and product lookups use SQL `LIKE` matching (keyword search). You can optionally enable semantic search using OpenAI embeddings, which understands meaning — so "something refreshing" can match "Sprite" or "Limonada".

### How It Works

1. When you browse stores or search products, the results are cached in SQLite
2. When embeddings are enabled, cached products are converted to vector representations using OpenAI's `text-embedding-3-small` model
3. Searches compute cosine similarity between your query and all cached product vectors
4. Results are ranked by semantic relevance, not just keyword match

### Enable Embeddings

```bash
# Install the OpenAI dependency
uv add openai

# Set your API key
export OPENAI_API_KEY="sk-..."

# Enable in preferences
uv run rappi prefs set embeddings.enabled true
uv run rappi prefs set embeddings.provider openai
```

### Cost

OpenAI `text-embedding-3-small` costs ~$0.02 per 1 million tokens. A typical product name is 5-10 tokens. Embedding 1,000 products costs less than $0.001. For personal use, the cost is effectively zero.

### Architecture

```
Query: "that spicy chicken thing"
         |
         v
   Embeddings enabled?
         |
    No --+--> SQL LIKE search (keyword match)
         |
    Yes --+--> OpenAI API: embed query -> 1536-dim vector
              |
              v
         SQLite: load all product vectors
         Compute cosine similarity, rank by score
              |
              v
         Top-k results: "Pollo Picante BBQ", "Alitas Picantes", ...
```

The embedding provider is abstracted — `OpenAIEmbeddingProvider` can be swapped for a local model (e.g., Ollama with `nomic-embed-text`) by implementing the `EmbeddingProvider` interface.

## Claude Code Plugin

This project is packaged as a **Claude Code Plugin** — it bundles skills, an agent, and the MCP server into one installable unit.

### Install as Plugin

```bash
# From the project directory (local development)
claude --plugin-dir .

# Or from another project, reference the path
claude --plugin-dir /path/to/rappi-cli
```

Once installed, Claude auto-discovers the skills and MCP tools. No manual configuration needed.

### Skills (Slash Commands)

| Command | Description |
|---------|-------------|
| `/order-food [query]` | Full ordering flow — search, browse menu, customize toppings, cart, checkout. Claude handles the entire workflow using MCP tools. |
| `/rappi-search <query>` | Quick product/store search. Lightweight — just shows results, no cart management. |
| `/rappi-reorder` | Shows past orders from memory, lets you pick one, re-adds items to cart and checks out. |

Skills are auto-invoked by Claude when relevant. If you say "I'm hungry, order me a burger," Claude will trigger the order-food skill automatically without you typing the slash command.

### Rappi Agent

A specialized agent (`agents/rappi-agent.md`) that deeply understands the Rappi ordering workflow:

- Knows all 22 MCP tools and when to use each
- Handles store type differences (restaurants vs Turbo vs markets)
- Manages required toppings validation
- Checks your preferences (dietary restrictions, allergies, default tip)
- Recovers from errors (closed stores, unavailable products, expired tokens)
- Uses Sonnet for fast responses

The agent is used by skills via `context: fork` for complex ordering flows.

### Session Hook

When you open this project in Claude Code, a `SessionStart` hook automatically checks your Rappi auth status and tells Claude whether you're logged in and ready to order.

### Plugin File Structure

```
.claude-plugin/
└── plugin.json              # Plugin manifest (name, version, author)

skills/
├── order-food/
│   └── SKILL.md             # Full ordering workflow skill
├── rappi-search/
│   └── SKILL.md             # Quick search skill
└── rappi-reorder/
    └── SKILL.md             # Reorder from history skill

agents/
└── rappi-agent.md           # Specialized ordering agent

.mcp.json                    # MCP server auto-configuration
.claude/settings.json        # Session start auth check hook
```

### How Skills Use the MCP Server

Skills instruct Claude to call MCP tools (not CLI commands). This is intentional — MCP tools return structured JSON that Claude can reason about, while CLI commands return formatted text meant for humans.

```
User: "Order me a burger"
  -> Claude triggers /order-food skill
    -> Skill instructs Claude to call MCP tools:
      1. get_ordering_context (check state)
      2. search_restaurants("burger") (find options)
      3. get_restaurant_menu(store_id) (show menu)
      4. get_product_toppings(...) (if needed)
      5. add_to_cart(...) (add items)
      6. checkout(confirm=false) (preview)
      7. checkout(confirm=true) (place order after user confirms)
```

## Project Architecture

```
src/rappi/
├── cli/                    # Typer CLI commands + Rich formatting
│   ├── interactive.py      # "rappi go" — guided ordering session
│   ├── auth.py             # Login, status, logout
│   ├── address.py          # Address management
│   ├── search.py           # Product/store search
│   ├── store.py            # Browse, detail, toppings
│   ├── cart.py             # Cart management
│   ├── order.py            # Checkout and tracking
│   ├── history.py          # Order history
│   ├── favorites.py        # Favorite stores
│   ├── prefs.py            # User preferences
│   ├── formatters.py       # Rich table/panel renderers
│   └── session.py          # Interactive session state
│
├── mcp/
│   └── server.py           # FastMCP server — 22 tools
│
├── services/               # Business logic (shared by CLI + MCP)
│   ├── auth.py             # Profile, Prime status
│   ├── browser_auth.py     # Playwright token capture
│   ├── address.py          # Address CRUD + geocoding
│   ├── search.py           # Unified search (all store types)
│   ├── store.py            # Store detail, menus, toppings
│   ├── cart.py             # Cart operations with correct payload
│   ├── checkout.py         # Checkout flow, place order
│   └── order.py            # Order tracking
│
├── memory/                 # Persistence layer
│   ├── db.py               # SQLite connection + migrations
│   ├── manager.py          # MemoryManager facade
│   ├── embeddings.py       # Optional embedding providers
│   └── repositories/       # Data access (one per domain)
│       ├── orders.py
│       ├── products.py
│       ├── stores.py
│       ├── preferences.py
│       └── search.py
│
├── models/                 # Pydantic response models
│   ├── user.py, address.py, store.py, cart.py, order.py
│
├── utils/
│   ├── pricing.py          # COP formatting, HTML stripping
│   └── ids.py              # Compound cart IDs
│
├── client.py               # Async HTTP client (httpx)
├── config.py               # Auth config (~/.rappi/config.json)
└── constants.py            # API endpoints, headers, URLs
```

**Key design pattern**: Services are shared. CLI commands, MCP tools, and the interactive session all call the same service functions. The memory layer (`MemoryManager`) is passed through `RappiClient` so services can read/write to it without coupling to a specific interface.

## API Notes

This project uses Rappi's internal API — the same endpoints the Rappi website calls. There is no public API documentation. Key details:

- **Base URL**: `https://services.grability.rappi.com`
- **Auth**: Bearer tokens (`ft.gAAAAA...`) captured from browser login
- **Tokens expire** periodically — re-run `rappi auth login` when you get 401 errors
- **Restaurant menus** come from a separate endpoint (`/api/restaurant-bus/store/{id}/menu`)
- **Non-restaurant stores** (Turbo, markets) don't have a menu endpoint — products are discovered via search
- **Cart payloads** require compound IDs (`storeId_productId`), full topping objects, and all three price fields
- **Prices** are in COP (Colombian Pesos), formatted with dot separators ($35.500)

## Development

```bash
# Install dev dependencies
uv sync --group dev

# Run tests
uv run pytest

# Run the CLI
uv run rappi --help

# Test MCP server
npx @modelcontextprotocol/inspector uv run rappi-mcp
```

## License

MIT
