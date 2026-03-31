# Testing Checklist — Rappi Claude Plugin

Work through this top-to-bottom. Each section builds on the previous. Fix bugs as you find them before moving to the next section.

---

## 1. Auth & Setup

- [ ] `uv run rappi auth login` — browser opens, log in, token captured
- [ ] `uv run rappi auth status` — shows your name, email, Prime status
- [ ] `~/.rappi/config.json` exists with token and device_id
- [ ] `uv run rappi auth logout` — clears token
- [ ] `uv run rappi auth status` — now shows "Not authenticated"
- [ ] `uv run rappi auth login` — re-authenticate for remaining tests

## 2. Addresses

- [ ] `uv run rappi address list` — shows all saved addresses with active marker
- [ ] Note which address is active (delivery location matters for all searches)

## 3. Search (Restaurants)

- [ ] `uv run rappi search "hamburguesa"` — returns stores with products, prices, stock
- [ ] Results include store names, ETAs, delivery costs
- [ ] Products show real prices (not $0 — $0 means store is closed)
- [ ] `~/.rappi/rappi.db` — search recorded: `uv run python -c "import asyncio; from rappi.memory import MemoryManager; asyncio.run((mm := MemoryManager()).__aenter__()); asyncio.run(mm.search.list_recent(1))"`

## 4. Store Menu (Restaurant)

- [ ] Pick a store_id from search results
- [ ] `uv run rappi store detail <store_id>` — shows store info + menu categories
- [ ] Menu has categories with products (not "No menu items")
- [ ] Products show prices, stock status, topping indicator
- [ ] Try a store that's currently open (check during daytime Colombia hours)

## 5. Store Menu (Turbo / Non-Restaurant)

- [ ] `uv run rappi search "turbo"` — find a Turbo store
- [ ] `uv run rappi store detail <turbo_store_id>` — shows store info, 0 categories (expected)
- [ ] Console should say "This is a turbo store — search for products to browse"

## 6. Toppings

- [ ] Find a product with toppings from a restaurant menu (look for "Toppings: Yes")
- [ ] `uv run rappi store toppings <store_id> <product_id>` — shows topping categories
- [ ] Required toppings marked with "(required)"
- [ ] Each topping shows price (even if $0)

## 7. Cart — Add Item

- [ ] `uv run rappi cart add <store_id> <product_id>` — interactive topping selection
- [ ] Required toppings prompt correctly (can't skip)
- [ ] Optional toppings can be skipped with Enter
- [ ] Quantity prompt works
- [ ] "Added to cart!" confirmation shown
- [ ] `uv run rappi cart show` — item appears with correct price

## 8. Cart — Turbo Item

- [ ] Search for a Turbo product (e.g., `uv run rappi search "coca cola"`)
- [ ] Add a Turbo item: `uv run rappi cart add <turbo_store_id> <product_id>`
- [ ] `uv run rappi cart show` — Turbo item appears

## 9. Cart — Remove

- [ ] `uv run rappi cart remove <store_id> <product_id>` — item removed
- [ ] `uv run rappi cart show` — confirms item gone

## 10. Checkout (Preview Only)

- [ ] Add an item to cart first
- [ ] `uv run rappi order checkout` — shows price breakdown
- [ ] No HTML tags in output (no `<b>`, `<font>`, etc.)
- [ ] No "None: None" lines
- [ ] Total looks correct
- [ ] When prompted "Place this order?" — say **No** (unless you want to spend money)

## 11. Place a Real Order

**This costs real money. Do it when you actually want food.**

- [ ] `uv run rappi order checkout --tip 3000` — set tip
- [ ] Review summary, confirm with "y"
- [ ] "Order placed!" success message (no traceback)
- [ ] `uv run rappi order list` — shows the active order with status
- [ ] `uv run rappi order track` — live tracking updates

## 12. Memory — After Real Order

- [ ] `uv run rappi history` — order appears with store, items, total, date
- [ ] `uv run rappi history detail <order_id>` — shows full item breakdown
- [ ] Product cache populated: check with `uv run rappi prefs` (should have data)

## 13. Interactive Mode (`rappi go`)

- [ ] `uv run rappi go` — shows welcome with name, Prime status
- [ ] If you have order history: shows "Last order: ..." and order count
- [ ] Shows delivery address, offers to switch if multiple
- [ ] "What are you looking for?" menu shows:
  - [ ] 1. Search
  - [ ] 2. Browse nearby
  - [ ] 3. Reorder from history (if orders exist)
  - [ ] 4. Pick a favorite (if favorites exist)
  - [ ] 5. Suggested for you (if orders exist)

### 13a. Interactive — Search Flow

- [ ] Pick option 1, enter a search query
- [ ] Recent search suggestions appear (if prior searches exist)
- [ ] Results numbered — pick by number
- [ ] Store loads, shows status and menu
- [ ] Pick category → pick product → toppings (if any) → quantity → added
- [ ] Cart summary bar shows after adding
- [ ] "What next?" menu — try "View cart", then "Checkout"

### 13b. Interactive — Turbo Flow

- [ ] Search for "turbo" or similar
- [ ] Pick the Turbo store
- [ ] Prompted to search within store (not browse categories)
- [ ] Search for a product (e.g., "agua")
- [ ] Pick product, add to cart

### 13c. Interactive — Reorder Flow

- [ ] Start `rappi go`, pick "Reorder from history"
- [ ] Past orders shown with items and totals
- [ ] Pick one — items re-added to cart
- [ ] Shows which items were added and which failed (if any)
- [ ] Cart summary updates

### 13d. Interactive — Favorites Flow

- [ ] `uv run rappi favorites add <store_id>` — save a store first
- [ ] Start `rappi go`, pick "Pick a favorite"
- [ ] Favorite stores listed, pick one
- [ ] Store loads with menu

### 13e. Interactive — Suggestions Flow

- [ ] Start `rappi go`, pick "Suggested for you"
- [ ] Shows taste profile summary
- [ ] Recommendations listed with types (usual, time-based, new store)
- [ ] Pick one — navigates to that store or reorders

### 13f. Interactive — Checkout

- [ ] From "What next?" pick Checkout
- [ ] Default tip pre-filled (if set via `rappi prefs set tip 5000`)
- [ ] Summary shows clean text (no HTML)
- [ ] "Place this order?" — confirm or cancel
- [ ] On confirm: order placed, offers to track

## 14. Preferences

- [ ] `uv run rappi prefs set tip 5000` — saves
- [ ] `uv run rappi prefs set diet vegetarian` — saves
- [ ] `uv run rappi prefs set allergy "peanuts, shellfish"` — saves
- [ ] `uv run rappi prefs` — shows all three correctly
- [ ] `uv run rappi prefs clear diet` — removes it
- [ ] Next `rappi go` checkout pre-fills the $5,000 tip

## 15. Favorites

- [ ] `uv run rappi favorites add <store_id>` — saved
- [ ] `uv run rappi favorites` — shows store name (not just ID)
- [ ] `uv run rappi favorites remove <store_id>` — removed
- [ ] `uv run rappi favorites` — empty

## 16. Taste Profile (need 3+ orders for meaningful data)

- [ ] Place at least 3 orders from different stores/categories
- [ ] Run:
  ```bash
  uv run python -c "
  import asyncio, json
  from rappi.memory import MemoryManager
  async def t():
      async with MemoryManager() as m:
          p = await m.get_taste_profile()
          print(json.dumps(p.model_dump(), indent=2, default=str))
  asyncio.run(t())
  "
  ```
- [ ] Category preferences show real percentages (not empty)
- [ ] Time patterns reflect when you actually ordered
- [ ] Top products/stores match reality
- [ ] Spending summary looks correct

## 17. Recommendations (need 3+ orders)

- [ ] Run:
  ```bash
  uv run python -c "
  import asyncio
  from rappi.memory import MemoryManager
  async def t():
      async with MemoryManager() as m:
          r = await m.get_recommendations()
          print(r.profile_summary)
          for rec in r.recommendations:
              print(f'  [{rec.type}] {rec.title} ({rec.confidence:.0%})')
  asyncio.run(t())
  "
  ```
- [ ] "The usual" appears for stores you've ordered from 3+ times
- [ ] Time-based suggestions match current time of day
- [ ] Profile summary reads naturally

## 18. MCP Server

- [ ] `uv run python -c "from rappi.mcp.server import mcp; print(len(mcp._tool_manager._tools), 'tools')"` — shows 25
- [ ] MCP Inspector: `npx @modelcontextprotocol/inspector uv run rappi-mcp`
  - [ ] All 25 tools listed
  - [ ] 3 resources listed
  - [ ] Call `get_ordering_context` — returns user, address, cart, memory, taste_summary
  - [ ] Call `search_restaurants` with query "pizza" — returns stores
  - [ ] Call `get_taste_profile` — returns computed profile

## 19. Claude Desktop

- [ ] Restart Claude Desktop (to pick up MCP config)
- [ ] Start a new conversation
- [ ] "Search for burger restaurants near me on Rappi"
  - [ ] Claude uses `search_restaurants` tool
  - [ ] Shows results with names, ETAs, prices
- [ ] "What's my Rappi order history?"
  - [ ] Claude uses `get_order_history`
  - [ ] Shows past orders
- [ ] "What should I eat?" 
  - [ ] Claude uses `get_recommendations`
  - [ ] Shows personalized suggestions

## 20. Claude Code — Skills

- [ ] Open project in Claude Code: `claude --plugin-dir .`
- [ ] Type `/order-food hamburguesa`
  - [ ] Skill triggers
  - [ ] Claude follows the ordering workflow
  - [ ] Calls MCP tools in correct sequence
- [ ] Type `/rappi-search pizza`
  - [ ] Quick search results shown
- [ ] Type `/rappi-suggest`
  - [ ] Shows taste-based recommendations
- [ ] Type `/rappi-reorder`
  - [ ] Shows order history, offers to reorder

## 21. Edge Cases

- [ ] Search with no results — shows friendly "nothing found" message
- [ ] Try to add out-of-stock product — handled gracefully
- [ ] Try checkout with empty cart — error message, not crash
- [ ] Ctrl+C during `rappi go` — clean exit with "Goodbye!"
- [ ] Ctrl+C during `rappi order track` — stops tracking cleanly
- [ ] Run any command after `rappi auth logout` — shows "not authenticated" message

## 22. Embeddings (Optional)

Skip this section unless you want to test semantic search.

- [ ] `uv add openai`
- [ ] `export OPENAI_API_KEY="sk-..."`
- [ ] `uv run rappi prefs set embeddings.enabled true`
- [ ] Search for products to populate cache, then:
  ```bash
  uv run python -c "
  import asyncio
  from rappi.memory import MemoryManager
  async def t():
      async with MemoryManager() as m:
          count = await m.generate_embeddings_for_cached_products()
          print(f'Embedded {count} products')
  asyncio.run(t())
  "
  ```
- [ ] Test semantic search:
  ```bash
  uv run python -c "
  import asyncio
  from rappi.memory import MemoryManager
  async def t():
      async with MemoryManager() as m:
          results = await m.smart_search('something refreshing')
          for r in results[:5]:
              print(f'  {r[\"text\"]} (score={r[\"score\"]:.2f})')
  asyncio.run(t())
  "
  ```
- [ ] Results are semantically relevant (not just keyword matches)

---

## Quick Smoke Test (5 minutes)

If you just want to verify nothing is broken:

```bash
uv run rappi auth status           # Auth works
uv run rappi search "pizza"        # Search works
uv run rappi store browse          # Browse works
uv run rappi history               # Memory works
uv run rappi prefs                 # Preferences work
uv run rappi --help                # All 10 command groups show

# MCP loads
uv run python -c "from rappi.mcp.server import mcp; print(f'{len(mcp._tool_manager._tools)} tools, {len(mcp._resource_manager._resources)} resources')"
```

Expected output for the last command: `25 tools, 3 resources`
