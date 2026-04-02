"""Rappi MCP server — exposes Rappi services as tools for AI assistants."""

import os
from contextlib import asynccontextmanager

from rappi.client import RappiClient
from rappi.memory import MemoryManager
from rappi.models.store import Product, StoreDetail, ToppingCategory
from rappi.services.address import list_addresses as _list_addresses
from rappi.services.address import set_active_address as _set_active_address
from rappi.services.auth import get_profile as _get_profile
from rappi.services.auth import is_prime as _is_prime
from rappi.services.cart import add_to_cart as _add_to_cart
from rappi.services.cart import get_carts as _get_carts
from rappi.services.cart import recalculate_cart as _recalculate_cart
from rappi.services.cart import remove_from_cart as _remove_from_cart
from rappi.services.checkout import get_checkout_detail as _get_checkout_detail
from rappi.services.checkout import place_order as _place_order
from rappi.services.checkout import set_tip as _set_tip
from rappi.services.order import get_orders as _get_orders
from rappi.services.search import search as _search
from rappi.services.store import get_product_toppings as _get_toppings
from rappi.services.store import get_restaurant_catalog as _get_catalog
from rappi.services.store import get_store_detail as _get_store_detail
from rappi.services.store import search_store_products as _search_store_products
from rappi.utils.ids import make_compound_id

from mcp.server.fastmcp import FastMCP

# Disable DNS rebinding protection for remote transports (Railway, etc.)
_transport = os.environ.get("MCP_TRANSPORT", "stdio")
_mcp_kwargs: dict = dict(
    name="rappi",
    instructions=(
        "Rappi food delivery tools for searching restaurants, browsing menus, "
        "managing a cart, and placing orders in Colombia (prices in COP).\n\n"
        "WORKFLOW: Start with get_ordering_context to understand current state. "
        "Then: search_restaurants or browse_restaurants -> get_restaurant_menu -> "
        "get_product_toppings (if has_toppings=true) -> add_to_cart -> "
        "checkout(confirm=false) to preview -> checkout(confirm=true) to place.\n\n"
        "The user must authenticate first via `rappi auth login` in their terminal."
    ),
)

if _transport in ("sse", "streamable-http", "http"):
    try:
        from mcp.server.auth.settings import TransportSecuritySettings
    except ImportError:
        from mcp.server.transport_security import TransportSecuritySettings  # type: ignore[no-redef]
    _mcp_kwargs["transport_security"] = TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    )

mcp = FastMCP(**_mcp_kwargs)


# --- Resources (workflow playbooks for any MCP client) ---


@mcp.resource("rappi://workflow/ordering")
async def ordering_workflow() -> str:
    """Complete ordering workflow — the step-by-step playbook for placing an order."""
    return """# Rappi Ordering Workflow

Follow these steps in order. Skip steps that aren't needed.

## Step 1: Context
Call `get_ordering_context` FIRST. This returns:
- User profile (name, Prime status)
- Active delivery address
- Current cart contents (if any)
- Active orders being tracked
- Memory summary (order count, last order, favorites)
- Taste summary (one-line profile)

If not authenticated, tell user to run `rappi auth login`.

## Step 2: Find Food
Choose based on what the user wants:
- **Specific food/restaurant**: `search_restaurants(query)`
- **Browse nearby**: `browse_restaurants(offset, limit)`
- **Suggestions**: `get_recommendations(context)` — uses taste profile + time of day
- **Reorder**: `get_order_history(limit)` then `quick_reorder(order_id)`
- **Favorites**: `get_favorites()` then browse that store

Search returns ALL store types (restaurants, Turbo, markets, pharmacies).
Check the `store_type` field to know which kind of store it is.

## Step 3: Browse Menu
- **Restaurants** (store_type="restaurant"): `get_restaurant_menu(store_id)`
- **Turbo/markets/pharmacies**: `search_in_store(store_id, query)` — no static menu
- **Score items**: `score_menu(store_id)` ranks items by taste match

If `get_restaurant_menu` returns empty categories with a "hint", use `search_in_store`.

## Step 4: Toppings (IMPORTANT)
If a product has `has_toppings=true`:
1. Call `get_product_toppings(store_id, product_id)` BEFORE adding to cart
2. Categories with `min_required > 0` are MANDATORY
3. Present options to user, get their choices
4. Include selected `topping_ids` in `add_to_cart`

Skipping this for required toppings will cause `add_to_cart` to return an error.

## Step 5: Add to Cart
Call `add_to_cart(store_id, product_id, quantity, topping_ids)`.
- Price and product details are auto-fetched (no need to pass them)
- If error says "missing required toppings", go back to Step 4
- Ask if user wants to add more items

## Step 6: Checkout
1. Call `checkout(tip_amount=0, confirm=false)` — PREVIEW ONLY
2. Show the summary to the user (products, delivery fee, total)
3. Check preferences for default tip: `get_preferences()`
4. Ask user to confirm
5. ONLY after explicit confirmation: `checkout(tip_amount=X, confirm=true)`
6. NEVER place an order without user saying yes

## Step 7: Track
After placing: `get_order_status()` shows delivery state and ETA.
Order states: created → in_store → on_the_way → delivered

## Prices
All prices are in COP (Colombian Pesos). Format with dots: $35.500 (not commas).

## Error Recovery
- Token expired → tell user to run `rappi auth login`
- Store unavailable → suggest alternatives
- Missing toppings → show which categories need selection
- Product out of stock → suggest similar items from menu
"""


@mcp.resource("rappi://workflow/personalization")
async def personalization_workflow() -> str:
    """How to use the memory and intelligence features for personalized experiences."""
    return """# Rappi Personalization Guide

## Understanding the User
Call `get_taste_profile()` to get the full computed profile:
- Category preferences: what cuisines they like (with percentages)
- Store type preferences: restaurant vs turbo vs market
- Price range: average order, average item, min/max
- Time patterns: when they order (morning/lunch/evening/night), which days
- Topping preferences: what customizations they always pick
- Top products: most reordered items
- Top stores: most ordered from
- Spending: total, average, tip habits, orders per week
- Dietary restrictions and allergies

## Making Recommendations
Call `get_recommendations(context)` for scored suggestions:
- "usual" — their regular order from specific stores (highest confidence)
- "time_based" — stores they order from at this time of day
- "similar_product" — products similar to their taste (requires embeddings)
- "new_store" — stores they haven't tried matching their preferences

Always respect dietary_restrictions and allergies from the profile.

## Scoring Menus
After fetching a menu, call `score_menu(store_id)` to rank items by taste match.
Present highest-scored items first: "Based on your taste, I'd recommend..."

## Memory Tools
- `get_order_history(limit)` — what they've ordered before
- `get_favorites()` — explicitly saved stores
- `get_preferences()` — dietary, allergies, default tip
- `set_preference(key, value)` — save new preferences
- `smart_search(query)` — search across cached products by meaning

## Embeddings
If embeddings are enabled (check `get_ordering_context` → memory.embeddings_enabled):
- `smart_search` uses semantic matching ("something refreshing" finds Sprite)
- `score_menu` ranks by cosine similarity to taste vector
- `get_recommendations` includes similar_product suggestions
If disabled, all features fall back to SQL keyword/frequency matching.
"""


@mcp.resource("rappi://info/store-types")
async def store_types_info() -> str:
    """How different store types work on Rappi."""
    return """# Rappi Store Types

| Type | Examples | How to Browse | Cart URL Type |
|------|----------|--------------|---------------|
| restaurant | El Corral, McDonald's | `get_restaurant_menu(store_id)` — returns categories with products | "restaurant" |
| turbo | Turbo convenience stores | `search_in_store(store_id, query)` — no static menu | "turbo" |
| larebaja | La Rebaja pharmacy | `search_in_store(store_id, query)` | varies |
| markets | Carulla, Exito | `search_in_store(store_id, query)` | varies |

Key differences:
- Restaurants have menu corridors (categories like "Hamburguesas", "Bebidas")
- Non-restaurant stores have thousands of SKUs, only searchable — no browse menu
- Store type appears in search results as `store_type` field
- The store type determines which URL path the cart/checkout API uses
"""


# --- Helpers ---


@asynccontextmanager
async def _client_with_memory():
    """Create a RappiClient with MemoryManager for MCP tool calls."""
    async with MemoryManager() as memory:
        async with RappiClient(memory=memory) as client:
            yield client, memory


def _find_product(store: StoreDetail, product_id: int) -> Product | None:
    """Find a product in a store's menu corridors."""
    for corridor in store.corridors:
        for p in corridor.products:
            if p.id == product_id:
                return p
    return None


def _validate_toppings(
    categories: list[ToppingCategory], selected_ids: list[int]
) -> dict:
    """Check that all required topping categories have enough selections."""
    missing = []
    for cat in categories:
        if cat.min_toppings_for_categories > 0:
            cat_topping_ids = {t.id for t in cat.toppings}
            selected_in_cat = [tid for tid in selected_ids if tid in cat_topping_ids]
            if len(selected_in_cat) < cat.min_toppings_for_categories:
                missing.append({
                    "category_id": cat.id,
                    "category_name": cat.description,
                    "min_required": cat.min_toppings_for_categories,
                    "selected_count": len(selected_in_cat),
                    "available_toppings": [
                        {"id": t.id, "name": t.description, "price": t.price}
                        for t in cat.toppings
                        if t.is_available
                    ],
                })
    return {"valid": len(missing) == 0, "missing": missing}


# --- Tools ---


@mcp.tool()
async def get_ordering_context() -> dict:
    """Get a snapshot of the user's current state: active address, cart contents, and active orders.

    When to use: Call this FIRST at the start of any ordering conversation to understand
    where the user is in the process before making suggestions.
    Next step: Based on the state, suggest searching for restaurants, continuing checkout, or tracking orders.
    """
    async with _client_with_memory() as (client, memory):
        profile = await _get_profile(client)
        prime = await _is_prime(client)
        addresses = await _list_addresses(client)
        active_addr = next((a for a in addresses if a.active), None)
        carts = await _get_carts(client)
        orders = await _get_orders(client)

        cart_summary = None
        if carts:
            all_items = []
            for cart in carts:
                for store in cart.stores:
                    for p in store.products:
                        all_items.append({"name": p.name, "quantity": p.units, "price": p.total})
            total = sum(c.sub_total for c in carts)
            if all_items:
                cart_summary = {"items": all_items, "total": total}

        # Memory context
        memory_summary = {}
        taste_summary = ""
        try:
            memory_summary = await memory.get_memory_summary()
            taste_summary = await memory.get_taste_summary()
        except Exception:
            pass

        return {
            "user": {"name": profile.name, "is_prime": prime.is_prime},
            "active_address": {
                "id": active_addr.id,
                "title": active_addr.title or active_addr.tag,
                "address": active_addr.address,
            } if active_addr else None,
            "cart": cart_summary,
            "memory": memory_summary,
            "taste_summary": taste_summary,
            "active_orders": [
                {
                    "id": o.id,
                    "store": o.store.name if o.store else None,
                    "state": o.state,
                    "eta": o.eta,
                }
                for o in orders.active_orders
            ],
        }


@mcp.tool()
async def auth_status() -> dict:
    """Check if the Rappi auth token is valid and return user profile.

    When to use: When the user asks about their account or you need to verify auth works.
    Next step: If authenticated, use get_ordering_context for full state.
    """
    async with RappiClient() as client:
        profile = await _get_profile(client)
        prime = await _is_prime(client)
        return {
            "authenticated": True,
            "name": profile.name,
            "email": profile.email,
            "is_prime": prime.is_prime,
        }


@mcp.tool()
async def list_delivery_addresses() -> dict:
    """List all saved delivery addresses. The active address determines which restaurants appear.

    When to use: When the user wants to check or switch their delivery location.
    Next step: Use set_delivery_address to switch, then search or browse restaurants.
    """
    async with RappiClient() as client:
        addresses = await _list_addresses(client)
        return {
            "addresses": [
                {
                    "id": a.id,
                    "title": a.title or a.tag,
                    "address": a.address,
                    "active": a.active,
                    "lat": a.lat,
                    "lng": a.lng,
                }
                for a in addresses
            ]
        }


@mcp.tool()
async def set_delivery_address(address_id: int) -> dict:
    """Set which address to deliver to. This affects which restaurants are available.

    When to use: When the user wants to switch delivery location.
    Next step: Search or browse restaurants for the new location.
    """
    async with RappiClient() as client:
        await _set_active_address(client, address_id)
        return {"success": True, "address_id": address_id}


@mcp.tool()
async def search_restaurants(query: str) -> dict:
    """Search for restaurants, stores, and products matching a query.

    Returns ALL store types: restaurants, Turbo (convenience), markets, pharmacies, etc.
    The store_type field tells you what kind of store it is.

    When to use: The user asks for a specific food, product, or store by name.
    Next step: For restaurants (store_type="restaurant"), use get_restaurant_menu.
    For other stores (Turbo, markets), use search_in_store to find more products.
    Or use add_to_cart directly if the user wants a product from the results.
    """
    async with RappiClient() as client:
        stores = await _search(client, query)
        return {
            "stores": [
                {
                    "store_id": s.store_id,
                    "store_name": s.store_name,
                    "store_type": s.store_type,
                    "eta": s.eta,
                    "shipping_cost": s.shipping_cost,
                    "products": [
                        {
                            "product_id": p.product_id,
                            "name": p.name,
                            "price": p.price,
                            "in_stock": p.in_stock,
                            "has_toppings": p.has_toppings,
                        }
                        for p in s.products
                    ],
                }
                for s in stores
            ]
        }


@mcp.tool()
async def search_in_store(store_id: int, query: str) -> dict:
    """Search for products within a specific store.

    This is the primary way to browse non-restaurant stores (Turbo, markets, pharmacies)
    which don't have a static menu. Results are grouped by category.

    When to use: When the user wants to find products in a specific Turbo, market, or other
    non-restaurant store. Also useful for searching within a restaurant.
    Next step: Use add_to_cart with the store_id and product_id from the results.
    """
    async with RappiClient() as client:
        corridors = await _search_store_products(client, store_id, query)
        return {
            "categories": [
                {
                    "name": c.name,
                    "products": [
                        {
                            "id": p.id,
                            "name": p.name,
                            "description": p.description,
                            "price": p.price,
                            "in_stock": p.in_stock,
                        }
                        for p in c.products
                    ],
                }
                for c in corridors
            ]
        }


@mcp.tool()
async def browse_restaurants(offset: int = 0, limit: int = 20) -> dict:
    """Browse nearby restaurants without searching. Returns a paginated list sorted by relevance.

    When to use: The user wants to see what's available nearby without a specific query.
    Next step: Use get_restaurant_menu with a store_id to see the full menu.
    """
    async with RappiClient() as client:
        stores = await _get_catalog(client, offset=offset, limit=limit)
        return {
            "stores": [
                {
                    "store_id": s.store_id,
                    "name": s.name,
                    "rating": s.score,
                    "eta": s.eta,
                    "shipping_cost": s.shipping_cost,
                    "is_available": s.is_available,
                }
                for s in stores
            ]
        }


@mcp.tool()
async def get_restaurant_menu(store_id: int) -> dict:
    """Get the full menu for a store, organized by category.

    Works for restaurants (returns menu corridors). For non-restaurant stores
    (Turbo, markets) this may return an empty menu — use search_in_store instead.

    When to use: After the user picks a restaurant from search/browse results.
    Next step: If a product has has_toppings=true, call get_product_toppings before adding to cart.
    If categories is empty, use search_in_store to find products.
    """
    async with RappiClient() as client:
        store = await _get_store_detail(client, store_id)
        result = {
            "store_id": store.store_id,
            "name": store.name,
            "store_type": store.effective_store_type,
            "status": store.status.status if store.status else "unknown",
            "categories": [
                {
                    "name": c.name,
                    "products": [
                        {
                            "id": p.id,
                            "name": p.name,
                            "description": p.description,
                            "price": p.price,
                            "in_stock": p.in_stock,
                            "has_toppings": p.has_toppings,
                        }
                        for p in c.products
                    ],
                }
                for c in store.corridors
            ],
        }
        if not store.corridors and not store.is_restaurant:
            result["hint"] = (
                f"This is a {store.effective_store_type} store with no static menu. "
                "Use search_in_store to find products."
            )
        return result


@mcp.tool()
async def get_product_toppings(store_id: int, product_id: int) -> dict:
    """Get available toppings/customizations for a product.

    When to use: Before adding a product that has has_toppings=true. REQUIRED for products
    with mandatory topping categories (min_required > 0).
    Next step: Pass the selected topping IDs to add_to_cart.
    """
    async with RappiClient() as client:
        result = await _get_toppings(client, store_id, product_id)
        return {
            "categories": [
                {
                    "id": cat.id,
                    "description": cat.description,
                    "type": cat.topping_type_id,
                    "min_required": cat.min_toppings_for_categories,
                    "max_allowed": cat.max_toppings_for_categories,
                    "toppings": [
                        {
                            "id": t.id,
                            "description": t.description,
                            "price": t.price,
                            "available": t.is_available,
                        }
                        for t in cat.toppings
                    ],
                }
                for cat in result.categories
            ]
        }


@mcp.tool()
async def add_to_cart(
    store_id: int,
    product_id: int,
    quantity: int = 1,
    topping_ids: list[int] | None = None,
) -> dict:
    """Add a product to the cart. Price and details are automatically fetched.

    IMPORTANT: If a product has required toppings (min_required > 0 in get_product_toppings),
    you MUST provide topping_ids for those categories. Otherwise this returns an error
    explaining which categories need selections.

    When to use: After the user picks a product and (if needed) customizations.
    Next step: Ask if they want to add more items, or use checkout to review/place the order.
    """
    async with RappiClient() as client:
        store = await _get_store_detail(client, store_id)
        product = _find_product(store, product_id)

        if not product:
            return {"error": f"Product {product_id} not found in store {store_id}"}

        if not product.in_stock:
            return {"error": f"'{product.name}' is currently out of stock"}

        # Validate toppings for products that require them
        selected_toppings = []
        if product.has_toppings:
            toppings_resp = await _get_toppings(client, store_id, product_id)

            # Check required toppings are provided
            validation = _validate_toppings(toppings_resp.categories, topping_ids or [])
            if not validation["valid"]:
                return {
                    "error": "Missing required toppings",
                    "missing_categories": validation["missing"],
                    "hint": "Call get_product_toppings first, then provide topping_ids for all required categories.",
                }

            # Resolve topping objects
            if topping_ids:
                topping_map = {}
                for cat in toppings_resp.categories:
                    for t in cat.toppings:
                        topping_map[t.id] = t
                selected_toppings = [topping_map[tid] for tid in topping_ids if tid in topping_map]

        carts = await _add_to_cart(client, store_id, product, selected_toppings, quantity)
        total_items = sum(p.units for cart in carts for s in cart.stores for p in s.products)
        total_price = sum(cart.sub_total for cart in carts)
        return {
            "success": True,
            "product": product.name,
            "quantity": quantity,
            "unit_price": product.price,
            "cart_items": total_items,
            "cart_total": total_price,
        }


@mcp.tool()
async def view_cart() -> dict:
    """View current cart contents with items, quantities, prices, and totals.

    When to use: When the user wants to see what's in their cart before checking out.
    Next step: Use checkout(confirm=false) to preview the order, or remove_from_cart to remove items.
    """
    async with RappiClient() as client:
        carts = await _get_carts(client)
        if not carts:
            return {"empty": True, "stores": []}
        result_stores = []
        for cart in carts:
            for store in cart.stores:
                result_stores.append({
                    "store_id": store.id,
                    "store_name": store.name,
                    "is_open": store.is_open,
                    "products": [
                        {
                            "id": p.id,
                            "name": p.name,
                            "quantity": p.units,
                            "price": p.price,
                            "total": p.total,
                        }
                        for p in store.products
                    ],
                    "product_total": store.product_total,
                    "shipping": store.charge_total,
                    "total": store.total,
                })
        return {"empty": False, "stores": result_stores}


@mcp.tool()
async def remove_from_cart(store_id: int, product_id: int) -> dict:
    """Remove a product from the cart.

    When to use: When the user wants to remove a specific item.
    Next step: Use view_cart to show updated contents.
    """
    compound_id = make_compound_id(store_id, product_id)
    async with RappiClient() as client:
        await _remove_from_cart(client, compound_id)
        return {"success": True, "removed": compound_id}


@mcp.tool()
async def checkout(tip_amount: int = 0, confirm: bool = False) -> dict:
    """Preview checkout summary or place the order.

    IMPORTANT: Always call with confirm=False first to show the summary to the user.
    Only call with confirm=True after the user explicitly approves.

    When to use: After the user is done adding items and wants to review or place the order.
    Next step: If preview, show the summary and ask user to confirm. If placed, use get_order_status to track.
    """
    async with RappiClient() as client:
        await _recalculate_cart(client)

        if tip_amount > 0:
            await _set_tip(client, tip_amount)

        detail = await _get_checkout_detail(client)

        summary = []
        for s in detail.summary:
            items = [{"type": d.type, "label": d.key, "value": d.value} for d in s.details]
            summary.append({
                "store": s.header.title if s.header else None,
                "items": items,
            })

        if not confirm:
            return {"preview": True, "summary": summary, "return_key_available": bool(detail.return_key)}

        if not detail.return_key:
            return {"error": "No return_key — cannot place order. Cart may be empty or invalid."}

        result = await _place_order(client, detail.return_key)
        return {"placed": True, "summary": summary, "result": result}


@mcp.tool()
async def get_order_status() -> dict:
    """Get active and cancelled orders with their current status.

    When to use: After placing an order, or when the user asks about their order status.
    Order states: created -> in_store -> on_the_way -> delivered (or cancelled).
    """
    async with RappiClient() as client:
        result = await _get_orders(client)
        return {
            "active_orders": [
                {
                    "id": o.id,
                    "store": o.store.name if o.store else None,
                    "state": o.state,
                    "total": o.total,
                    "eta": o.eta,
                    "tip": o.tip,
                    "can_cancel": o.can_be_cancel,
                }
                for o in result.active_orders
            ],
            "cancelled_orders": [
                {"id": o.id, "store": o.store.name if o.store else None}
                for o in result.cancel_orders
            ],
        }


# --- Memory tools ---


@mcp.tool()
async def get_order_history(limit: int = 10) -> dict:
    """Get past orders with store names, items, totals, and dates from local memory.

    When to use: User asks "what did I order last time?" or "show my order history".
    Next step: Use quick_reorder to re-add items from a past order.
    """
    async with MemoryManager() as memory:
        orders = await memory.orders.list_recent(limit=limit)
        return {
            "orders": [
                {
                    "id": o.id,
                    "store": o.store_name,
                    "store_type": o.store_type,
                    "total": o.total,
                    "tip": o.tip,
                    "state": o.state,
                    "date": o.placed_at,
                    "items": o.items or [],
                }
                for o in orders
            ]
        }


@mcp.tool()
async def get_favorites() -> dict:
    """Get the user's favorite stores.

    When to use: User asks for favorites or wants to quickly pick a restaurant.
    Next step: Use get_restaurant_menu or search_in_store for a favorite.
    """
    async with MemoryManager() as memory:
        store_ids = await memory.preferences.get_favorite_store_ids()
        stores = []
        for sid in store_ids:
            cached = await memory.stores.get(sid, ttl_hours=99999)
            stores.append({
                "store_id": sid,
                "name": cached["name"] if cached else None,
                "store_type": cached.get("store_type") if cached else None,
            })
        return {"favorites": stores}


@mcp.tool()
async def add_favorite(store_id: int) -> dict:
    """Mark a store as a favorite for quick access later.

    When to use: User says "save this restaurant" or "add to favorites".
    """
    async with MemoryManager() as memory:
        await memory.preferences.add_favorite_store(store_id)
        return {"success": True, "store_id": store_id}


@mcp.tool()
async def remove_favorite(store_id: int) -> dict:
    """Remove a store from favorites."""
    async with MemoryManager() as memory:
        await memory.preferences.remove_favorite_store(store_id)
        return {"success": True, "store_id": store_id}


@mcp.tool()
async def quick_reorder(order_id: int) -> dict:
    """Re-add all items from a past order to the cart.

    When to use: User says "order the same thing as last time" or "reorder".
    Next step: Use checkout to review and place the order.
    """
    async with _client_with_memory() as (client, memory):
        order = await memory.orders.get_by_id(order_id)
        if not order:
            return {"error": f"Order {order_id} not found in history"}

        if not order.items:
            return {"error": "No items found for this order"}

        # Get store detail to fetch current prices
        store = await _get_store_detail(client, order.store_id)

        added = []
        failed = []
        for item in order.items:
            product = _find_product(store, int(item["product_id"]))
            if product and product.in_stock:
                try:
                    await _add_to_cart(
                        client, order.store_id, product, [],
                        item.get("quantity", 1),
                        store_type=store.effective_store_type,
                    )
                    added.append(item["name"])
                except Exception:
                    failed.append(item["name"])
            else:
                failed.append(f"{item['name']} (unavailable)")

        return {
            "success": True,
            "store": order.store_name,
            "added": added,
            "failed": failed,
        }


@mcp.tool()
async def get_preferences() -> dict:
    """Get user preferences: dietary restrictions, allergies, default tip.

    When to use: When making food recommendations or setting up checkout.
    """
    async with MemoryManager() as memory:
        return await memory.preferences.get_all()


@mcp.tool()
async def set_preference(key: str, value: str) -> dict:
    """Set a user preference.

    Keys: default_tip (int), dietary_restrictions (comma-separated), allergies (comma-separated).
    When to use: User says "I'm vegetarian", "always tip 5000", or "I'm allergic to peanuts".
    """
    async with MemoryManager() as memory:
        if key == "default_tip":
            await memory.preferences.set_default_tip(int(value))
        elif key == "dietary_restrictions":
            await memory.preferences.set_dietary_restrictions([v.strip() for v in value.split(",")])
        elif key == "allergies":
            await memory.preferences.set_allergies([v.strip() for v in value.split(",")])
        else:
            await memory.preferences.set(key, value)
        return {"success": True, "key": key, "value": value}


@mcp.tool()
async def smart_search(query: str, limit: int = 10) -> dict:
    """Search across cached products, order history, and favorites using
    text matching — or semantic search if embeddings are enabled.

    When to use: User asks vague things like "that spicy chicken thing from last week"
    or "something sweet". Falls back to keyword search if embeddings are not configured.
    """
    async with MemoryManager() as memory:
        results = await memory.smart_search(query, limit=limit)
        return {"results": results}


@mcp.tool()
async def get_taste_profile() -> dict:
    """Get the user's computed taste profile based on their entire order history.

    Returns: category preferences (what cuisines they like), store type preferences,
    price range, time-of-day patterns, topping preferences, top products/stores,
    spending summary, dietary restrictions, and allergies.

    When to use: User asks "what do I usually order?", "what are my food habits?",
    or when you need context to make personalized food recommendations.
    Next step: Use this to inform search queries and restaurant suggestions.
    """
    async with MemoryManager() as memory:
        profile = await memory.get_taste_profile()
        return profile.model_dump()


@mcp.tool()
async def get_recommendations(context: str | None = None) -> dict:
    """Get smart food recommendations based on the user's taste profile, current time,
    and order history.

    Returns scored recommendations: "the usual" orders, time-appropriate stores,
    stores they haven't tried yet.

    Args:
        context: Optional hint like "lunch", "quick snack", "something cheap".

    When to use: User asks "what should I eat?", "suggest something", "I'm hungry",
    or at the start of a conversation to proactively offer relevant options.
    Next step: Use the store_id from a recommendation with get_restaurant_menu or quick_reorder.
    """
    async with MemoryManager() as memory:
        ctx = {"raw_context": context} if context else None
        result = await memory.get_recommendations(ctx)
        return result.model_dump()


@mcp.tool()
async def score_menu(store_id: int) -> dict:
    """Score a restaurant's menu items by how well they match the user's taste.

    Uses embeddings (if enabled) to compute similarity between each product and
    the user's taste vector. Falls back to order-frequency scoring without embeddings.
    Items the user has ordered before or that match their taste rank highest.

    When to use: After fetching a menu with get_restaurant_menu, call this to help
    the user pick. "Based on your taste, I'd recommend these items."
    """
    async with _client_with_memory() as (client, memory):
        store = await _get_store_detail(client, store_id)
        all_products = [p for c in store.corridors for p in c.products if p.in_stock]

        if not all_products:
            return {"store_id": store_id, "scored_items": [], "note": "No available products"}

        scored = await memory.intelligence.score_menu_items(store_id, all_products)
        return {
            "store_id": store_id,
            "store_name": store.name,
            "scored_items": [
                {
                    "product_id": getattr(s["product"], "id", 0),
                    "name": getattr(s["product"], "name", ""),
                    "price": getattr(s["product"], "price", 0),
                    "match_score": s["match_score"],
                    "scoring_method": s["source"],
                }
                for s in scored[:15]
            ],
        }


def main():
    if _transport in ("sse", "streamable-http", "http"):
        from starlette.applications import Starlette
        from starlette.responses import PlainTextResponse
        from starlette.routing import Route, Mount
        import uvicorn

        host = os.environ.get("MCP_HOST", "0.0.0.0")
        port = int(os.environ.get("PORT", os.environ.get("MCP_PORT", "8000")))

        def health(_request):
            return PlainTextResponse("ok")

        mcp_app = mcp.sse_app() if _transport == "sse" else mcp.streamable_http_app()

        app = Starlette(
            routes=[
                Route("/health", health),
                Mount("/", app=mcp_app),
            ],
        )

        print(f"[rappi-mcp] Starting {_transport} on {host}:{port}", flush=True)
        uvicorn.run(app, host=host, port=port)
    else:
        mcp.run(transport=_transport)
