---
name: rappi-search
description: Quick search for restaurants, stores, or products on Rappi. Use when the user asks what's available, wants to find a specific restaurant or store (Turbo, Exito, Carulla, etc.), or is looking for a product.
argument-hint: "<query>"
allowed-tools: "mcp__rappi__*"
---

# Rappi Quick Search

Search for restaurants, stores, and products on Rappi. This is a lightweight search — no cart or checkout.

## Steps

1. If `$ARGUMENTS` is provided, use it as the search query. Otherwise, ask the user what they're looking for.

2. Determine the search type:
   - **"What's available?"** → Call `explore_verticals` to show all store types (Restaurants, Turbo, Markets, Farmacia, Licores, Tiendas, etc.)
   - **Product search** (e.g., "cerveza michelob", "pizza") → Call `search_restaurants` — returns ALL store types with matching products.
   - **Non-restaurant store browsing** (e.g., "find Turbo stores", "show me Exito") → Call `browse_stores(store_type, query)`.
   - **Restaurant browsing** (e.g., "what's nearby") → Call `browse_restaurants`.
   - **Search within a store** (e.g., "find beer in Turbo") → Call `search_store_products(store_id, query)` for CPG stores (richer results), or `search_in_store(store_id, query)` for any store.

3. Present results in a table:
   - Store name and type (restaurant, turbo, market, pharmacy)
   - ETA and delivery cost
   - Top matching products with prices

4. If the user wants to see more products from a store:
   - For restaurants: call `get_restaurant_menu(store_id)`
   - For Turbo/markets: call `search_store_products(store_id, query)` — returns brand info, category, and more product details
   - Use `get_store_info(store_id)` if they ask about hours or delivery fees

5. Additional info available:
   - `get_credits_balance()` — show Rappi credits
   - `get_rappi_favorites()` — user's favorite stores
   - `get_order_detail(order_id)` — details of a past order
   - `get_order_breakdown(order_id)` — fee breakdown of a past order

6. Prices are in COP (Colombian Pesos) — format as $35.500 with dot separators.

7. If the user wants to order something they found, suggest using `/order-food` or guide them through the ordering flow.
