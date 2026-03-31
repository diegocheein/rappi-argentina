---
name: rappi-search
description: Quick search for restaurants, stores, or products on Rappi. Use when the user asks what's available, wants to find a specific restaurant, or is looking for a product.
argument-hint: "<query>"
allowed-tools: "mcp__rappi__search_restaurants,mcp__rappi__search_in_store,mcp__rappi__get_restaurant_menu,mcp__rappi__get_ordering_context"
---

# Rappi Quick Search

Search for restaurants, stores, and products on Rappi. This is a lightweight search — no cart or checkout.

## Steps

1. If `$ARGUMENTS` is provided, use it as the search query. Otherwise, ask the user what they're looking for.

2. Call `search_restaurants` with the query.

3. Present results in a table:
   - Store name and type (restaurant, turbo, market, pharmacy)
   - ETA and delivery cost
   - Top matching products with prices

4. If the user wants to see a full menu:
   - For restaurants: call `get_restaurant_menu(store_id)` and show categories with products
   - For Turbo/markets: call `search_in_store(store_id, query)` since they don't have static menus

5. Prices are in COP (Colombian Pesos) — format as $35.500 with dot separators.

6. If the user wants to order something they found, suggest using `/order-food` or guide them through the ordering flow.
