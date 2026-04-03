# Rappi Claude Plugin

A Claude plugin that lets you order food from [Rappi](https://www.rappi.com) through conversation. Say "order me a burger" and Claude handles the rest — searching restaurants, browsing menus, customizing toppings, managing your cart, and placing the order. It remembers your favorites, preferences, and order history across conversations.

Works on **Claude Code**, **Claude Desktop**, and **Claude Cowork** (web).

Supports all Rappi countries: Colombia, Mexico, Brazil, Argentina, Chile, Peru, Ecuador, Costa Rica, and Uruguay.

## How It Works

```
You: "I'm hungry, order me something from that burger place I liked"

Claude: *checks your order history, finds El Corral*
        *shows their menu, suggests items you've ordered before*
        *adds to cart with your usual toppings*
        *shows checkout summary with your default $3,000 tip*

You: "Looks good, place it"

Claude: *places the order, tracks delivery with real-time ETA*
```

The plugin gives Claude **38 tools** to interact with Rappi, **4 skills** for common workflows, a specialized ordering agent, and a local memory system that learns your preferences over time.

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
# Opens a browser — log in with your phone + OTP
uv run rappi auth login

# For other countries (default is Colombia):
uv run rappi auth login --country mx   # Mexico
uv run rappi auth login --country br   # Brazil
uv run rappi auth login --country ar   # Argentina
uv run rappi auth login --country cl   # Chile
uv run rappi auth login --country pe   # Peru
uv run rappi auth login --country ec   # Ecuador
uv run rappi auth login --country cr   # Costa Rica
uv run rappi auth login --country uy   # Uruguay
```

Your token is saved locally at `~/.rappi/config.json`. It never leaves your machine.

For Railway deployment, also set `RAPPI_COUNTRY` environment variable to your country code.

### Activate the Plugin

**Claude Code** (auto-discovers everything):
```bash
cd rappi-claude-plugin
claude   # MCP server auto-registers from .mcp.json
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

**Claude Cowork** (web — requires remote MCP server):
1. Deploy the MCP server (see [Deployment](#deployment))
2. Generate plugin zip: `uv run rappi build-plugin --url https://your-server.up.railway.app/sse`
3. Upload the zip via Cowork > Customize > Plugins
4. Add the SSE URL as a remote MCP connector

## What You Can Do

### Through Claude (Skills)

Just talk to Claude naturally. The plugin auto-triggers when you mention food, ordering, or Rappi.

| Skill | Trigger | What Claude Does |
|-------|---------|-----------------|
| `/order-food` | "Order me food", "I'm hungry", "get me a burger" | Full workflow: search → menu → toppings → cart → checkout → track |
| `/rappi-search` | "What restaurants are nearby?", "find beer at Turbo" | Searches stores and products, shows results |
| `/rappi-reorder` | "Order the same as last time", "reorder" | Pulls from order history, re-adds items to cart |
| `/rappi-suggest` | "What should I eat?", "suggest something" | Analyzes taste profile, suggests based on habits, time, and history |

### Through Claude (Conversational)

Beyond the skills, Claude can use the 38 MCP tools in any combination:

- "What's available on Rappi?" — shows all verticals (Restaurants, Turbo, Markets, Farmacia, Licores)
- "Find me beer at Exito" — searches specific store types with products
- "Browse the Turbo store aisles" — shows store categories
- "What should I eat?" — analyzes taste profile, gives personalized suggestions
- "What did I order last week?" — checks order history with cost breakdown
- "How much Rappi credit do I have?" — shows wallet balance
- "Track my order" — real-time delivery state, ETA, driver position
- "What were the fees on my last order?" — detailed cost breakdown
- "Save El Corral as a favorite" — adds to favorites
- "I'm allergic to peanuts" — saves to preferences
- "Always tip $5,000" — saves default tip

### Through the Terminal (CLI)

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
| `rappi favorites` | List favorite stores |
| `rappi prefs` | View preferences |
| `rappi prefs set tip 5000` | Set default tip |

</details>

## MCP Tools Reference

<details>
<summary>All 38 tools</summary>

**Discovery & Browsing**
- `explore_verticals` — all available store types in area (Restaurants, Turbo, Markets, Farmacia, Licores)
- `search_restaurants(query)` — search products/stores by keyword (all store types)
- `browse_restaurants(offset, limit)` — nearby restaurants
- `browse_stores(store_type, query)` — find stores by type (turbo, exito, carulla, olimpica, etc.)
- `get_store_categories(store_id)` — browse store aisles/categories
- `get_aisle_products(store_id, aisle_id)` — products in a category
- `get_store_info(store_id)` — hours, charges, address
- `search_store_products(store_id, query)` — CPG product search with brand info
- `search_in_store(store_id, query)` — search within any store

**Menu & Products**
- `get_restaurant_menu(store_id)` — full menu by category
- `get_product_toppings(store_id, product_id)` — customization options

**Cart & Checkout**
- `add_to_cart(store_id, product_id, quantity, topping_ids, product_name, product_price)` — add item
- `view_cart` / `remove_from_cart(store_id, product_id)`
- `checkout(tip_amount, confirm)` — preview then place (auto-detects store_type)
- `get_payment_methods` — available payment methods and cards

**Order Tracking**
- `get_active_orders` — currently active orders
- `track_order(order_id)` — real-time state, ETA, driver position
- `get_order_detail(order_id)` — full order summary
- `get_order_breakdown(order_id)` — detailed costs, fees, discounts
- `get_order_status` — active and cancelled orders
- `get_order_history(limit)` — past orders with items

**Account**
- `get_ordering_context` — full state snapshot (user, address, cart, memory)
- `auth_status` — profile and Prime status
- `list_delivery_addresses` / `set_delivery_address(address_id)`
- `get_credits_balance` — Rappi credits/wallet balance
- `get_rappi_favorites` — favorite stores from Rappi
- `get_favorites` / `add_favorite` / `remove_favorite` — local favorites

**Intelligence & Memory**
- `get_taste_profile` — computed taste profile (categories, time patterns, spending)
- `get_recommendations(context?)` — smart suggestions based on habits
- `score_menu(store_id)` — rank menu items by taste match
- `quick_reorder(order_id)` — re-add past order to cart
- `get_preferences` / `set_preference(key, value)`
- `smart_search(query)` — semantic search across cached products

</details>

## Store Types

The plugin works with all Rappi store types. Cart, checkout, and order tracking automatically detect the correct store type.

| Type | Examples | How It Works |
|------|----------|-------------|
| Restaurants | El Corral, McDonald's, local places | Browse menu categories, customize toppings |
| Turbo | Turbo convenience stores | Search for products, browse by aisle |
| Markets | Carulla, Exito, Jumbo, Olimpica | Search for products |
| Pharmacies | La Rebaja, Farmatodo | Search for products |
| Liquor | Cervesia, Exito Licores | Search for products |

## Deployment

The MCP server supports two modes:

- **Local (stdio)**: For Claude Code and Claude Desktop — runs as a subprocess
- **Remote (SSE over HTTP)**: For Claude Cowork — deployed to Railway

### Railway Deployment

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/template/rappi-mcp?referralCode=rappi-claude-plugin)

Or deploy manually:

1. Fork this repo to your GitHub account
2. Connect it to [Railway](https://railway.com) (New Project → Deploy from GitHub)
3. Set environment variables in Railway dashboard:

| Variable | Value | Purpose |
|----------|-------|---------|
| `RAPPI_TOKEN` | `ft.xxxxx` | Auth token from `~/.rappi/config.json` |
| `RAPPI_DEVICE_ID` | UUID | Device ID from config |
| `MCP_TRANSPORT` | `sse` | Enables HTTP transport |
| `RAPPI_COUNTRY` | `co` | Country code (co, mx, br, ar, cl, pe, ec, cr, uy) |

4. Railway auto-assigns a URL like `https://your-app.up.railway.app`
5. Verify: `curl https://your-app.up.railway.app/health` should return `ok`

Coordinates are auto-synced from your Rappi active address — no need to set lat/lng.

**Get your token and device ID:**
```bash
uv run rappi auth login                    # Authenticate first
cat ~/.rappi/config.json | python3 -c "import json,sys; c=json.load(sys.stdin); print(f'RAPPI_TOKEN={c[\"token\"]}\nRAPPI_DEVICE_ID={c[\"device_id\"]}')"
```

### Cowork Plugin Setup

After deploying to Railway:

```bash
# Generate the Cowork plugin zip with your Railway URL
uv run rappi build-plugin --url https://your-app.up.railway.app/sse
```

This creates `rappi-cowork-plugin.zip` on your Desktop. Upload it to Cowork > Customize > Plugins, then add the SSE URL as a remote MCP connector.

See [CLAUDE.md](CLAUDE.md) for the full deployment reference including the critical FastMCP patterns.

## Intelligence & Personalization

The plugin stores everything locally in SQLite (`~/.rappi/rappi.db`) and computes a **taste profile** from your order history.

### What It Learns

| Data | Source | What It Computes |
|------|--------|-----------------|
| Order history | Auto-recorded after checkout | "The usual" per store, reorder patterns |
| Product cache | Auto-cached from menus/searches | Category preferences (Hamburguesas 40%, Bebidas 25%) |
| Time patterns | Order timestamps | Peak ordering times, day-of-week habits |
| Topping choices | Stored per order item | "Always adds extra cheese" |
| Price patterns | Order totals | Average spend, price sensitivity |
| Preferences | You tell Claude or set via CLI | Dietary restrictions, allergies, default tip |

### Embeddings (Optional)

Enable OpenAI embeddings for semantic search — "something refreshing" matches "Sprite" and "Limonada".

```bash
uv add openai
export OPENAI_API_KEY="sk-..."
uv run rappi prefs set embeddings.enabled true
```

## Development

```bash
uv sync --group dev            # Install dev dependencies
uv run rappi --help            # Test CLI
uv run pytest                  # Run tests (196 tests)
npx @modelcontextprotocol/inspector uv run rappi-mcp  # Test MCP in browser
```

See [CLAUDE.md](CLAUDE.md) for the developer reference, [API_ENDPOINTS.md](API_ENDPOINTS.md) for the full Rappi API map, and [TESTING.md](TESTING.md) for the manual testing checklist.

## License

MIT
