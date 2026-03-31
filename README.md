# Rappi Claude Plugin

A Claude plugin that lets you order food from Rappi through conversation. Say "order me a burger" and Claude handles the rest — searching restaurants, browsing menus, customizing toppings, managing your cart, and placing the order. It remembers your favorites, preferences, and order history across conversations.

## How It Works

```
You: "I'm hungry, order me something from that burger place I liked"

Claude: *checks your order history, finds El Corral*
        *shows their menu, suggests items you've ordered before*
        *adds to cart with your usual toppings*
        *shows checkout summary with your default $3,000 tip*

You: "Looks good, place it"

Claude: *places the order, tracks delivery*
```

The plugin gives Claude 22 tools to interact with Rappi, 3 skills for common workflows, a specialized ordering agent, and a local memory system that learns your preferences over time.

## Install

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- A Rappi account (Colombia)

### Setup

```bash
git clone https://github.com/garavitgabriel/rappi-claude-plugin.git
cd rappi-claude-plugin
uv sync
uv run playwright install chromium
```

### Authenticate

```bash
# Opens a browser — log in with your phone + WhatsApp OTP
uv run rappi auth login
```

Your token is saved locally at `~/.rappi/config.json`. It never leaves your machine.

### Activate the Plugin

**Claude Code** (auto-discovers everything):
```bash
claude --plugin-dir .
```

**Claude Desktop** (add to `~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "rappi": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/rappi-claude-plugin", "rappi-mcp"]
    }
  }
}
```

## What You Can Do

### Through Claude (Skills)

Just talk to Claude naturally. The plugin auto-triggers when you mention food, ordering, or Rappi.

| Skill | Trigger | What Claude Does |
|-------|---------|-----------------|
| `/order-food` | "Order me food", "I'm hungry", "get me a burger" | Full workflow: search → menu → toppings → cart → checkout → track |
| `/rappi-search` | "What restaurants are nearby?", "find pizza" | Searches stores and products, shows results |
| `/rappi-reorder` | "Order the same as last time", "reorder" | Pulls from order history, re-adds items to cart |

### Through Claude (Conversational)

Beyond the skills, Claude can use the 22 MCP tools in any combination:

- "What did I order last week?" — checks order history
- "Save El Corral as a favorite" — adds to favorites
- "I'm allergic to peanuts" — saves to preferences, filters future recommendations
- "Always tip $5,000" — saves default tip
- "What's in my cart?" — shows cart contents
- "Track my order" — shows delivery status and ETA
- "Switch delivery to my office address" — changes active address

### Through the Terminal (CLI)

The plugin also includes a full CLI for direct terminal use:

```bash
uv run rappi go                    # Interactive guided ordering
uv run rappi search "hamburguesa"  # Quick search
uv run rappi store detail 900004   # View a store menu
uv run rappi cart show             # View cart
uv run rappi order checkout        # Place order
uv run rappi history               # Past orders
uv run rappi favorites             # Saved stores
uv run rappi prefs                 # Your preferences
```

<details>
<summary>Full CLI command reference</summary>

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

</details>

## Memory & Personalization

The plugin stores everything locally in a SQLite database at `~/.rappi/rappi.db`. Nothing is sent to external services. Over time, it builds a profile of your food preferences:

| What's Remembered | How | What It Enables |
|-------------------|-----|-----------------|
| **Order history** | Auto-recorded after each checkout | "What did I order last time?", quick reorder |
| **Product cache** | Auto-cached from searches and menus | Faster lookups, offline product search |
| **Store cache** | Auto-cached from interactions | Favorite store names, quick access |
| **Search history** | Auto-recorded on every search | Suggestions, popular queries |
| **Preferences** | You tell Claude or set via CLI | Default tip, dietary restrictions, allergies |
| **Favorites** | You mark stores as favorites | Quick access in any ordering flow |

### What Makes This Different

No food delivery app does this today. Rappi's own app doesn't:
- Build a taste profile from your history
- Let you say "the usual" and have it understood
- Remember your topping preferences per product
- Give time-aware suggestions ("you usually order coffee around now")
- Respect dietary restrictions across every recommendation
- Track your spending patterns

The combination of **AI reasoning** (Claude) + **personal memory** (SQLite) + **real ordering** (Rappi API) creates something that doesn't exist: a food assistant that actually knows you.

### Reset Memory

```bash
rm ~/.rappi/rappi.db      # Delete history, preferences, cache
uv run rappi auth logout   # Delete auth token
rm -rf ~/.rappi/           # Delete everything
```

## Embeddings (Optional)

By default, product search uses keyword matching. Enable OpenAI embeddings for semantic search — "something refreshing" matches "Sprite" and "Limonada" even though the words don't overlap.

```bash
uv add openai
export OPENAI_API_KEY="sk-..."
uv run rappi prefs set embeddings.enabled true
```

Cost is effectively zero (~$0.001 per 1,000 products). The embedding provider is abstracted — swap OpenAI for a local model (Ollama) by implementing the `EmbeddingProvider` interface.

## Plugin Architecture

```
rappi-claude-plugin/
│
├── .claude-plugin/plugin.json   # Plugin manifest
├── .mcp.json                    # MCP server auto-config
├── .claude/settings.json        # Session hooks
│
├── skills/                      # What Claude can do
│   ├── order-food/SKILL.md      # Full ordering workflow
│   ├── rappi-search/SKILL.md    # Quick search
│   └── rappi-reorder/SKILL.md   # Reorder from history
│
├── agents/
│   └── rappi-agent.md           # Specialized ordering agent (Sonnet)
│
├── src/rappi/                   # Plugin engine
│   ├── mcp/server.py            # 22 MCP tools (what Claude calls)
│   ├── services/                # Business logic (shared by all interfaces)
│   ├── memory/                  # SQLite persistence + optional embeddings
│   ├── cli/                     # Terminal interface
│   ├── models/                  # Pydantic data models
│   └── client.py                # Rappi API client
│
└── pyproject.toml               # Dependencies & entry points
```

**How the pieces connect:**

```
Skills & Agent (what Claude follows)
        |
        v
MCP Tools (what Claude calls)        CLI (terminal alternative)
        |                                    |
        +-------- Services Layer ------------+
                      |
              +-------+-------+
              |               |
        Rappi API        Memory (SQLite)
        (internet)       (~/.rappi/rappi.db)
```

Skills tell Claude the workflow. MCP tools give Claude the capabilities. Services contain the business logic. Memory makes it personal. The CLI provides a direct terminal interface to the same engine.

## MCP Tools Reference

<details>
<summary>All 22 tools</summary>

**Context**
- `get_ordering_context` — full state snapshot: user, address, cart, orders, memory
- `auth_status` — check token validity

**Addresses**
- `list_delivery_addresses` / `set_delivery_address`

**Search & Browse**
- `search_restaurants(query)` — all store types (restaurants, Turbo, markets, pharmacies)
- `search_in_store(store_id, query)` — products within a specific store
- `browse_restaurants(offset, limit)` — nearby restaurants

**Menu**
- `get_restaurant_menu(store_id)` — full menu by category
- `get_product_toppings(store_id, product_id)` — customization options

**Cart**
- `add_to_cart(store_id, product_id, quantity, topping_ids)`
- `view_cart` / `remove_from_cart(store_id, product_id)`

**Checkout**
- `checkout(tip_amount, confirm)` — preview then place
- `get_order_status` — active order tracking

**Memory**
- `get_order_history(limit)` — past orders with items
- `get_favorites` / `add_favorite` / `remove_favorite`
- `quick_reorder(order_id)` — re-add past order to cart
- `get_preferences` / `set_preference(key, value)`
- `smart_search(query)` — semantic search across memory

</details>

## Store Types

The plugin works with all Rappi store types:

| Type | Examples | How It Works |
|------|----------|-------------|
| Restaurants | El Corral, McDonald's, local places | Browse menu categories, customize toppings |
| Turbo | Turbo convenience stores | Search for products (no static menu) |
| Markets | Carulla, Exito | Search for products |
| Pharmacies | La Rebaja, Farmatodo | Search for products |

## API Notes

This plugin uses Rappi's internal API — the same endpoints the Rappi website calls. There is no public API documentation. Tokens expire periodically — re-run `rappi auth login` when needed.

## Development

```bash
uv sync --group dev            # Install dev dependencies
uv run rappi --help            # Test CLI
uv run pytest                  # Run tests
npx @modelcontextprotocol/inspector uv run rappi-mcp  # Test MCP
```

## License

MIT
