---
name: order-food
description: Order food delivery from Rappi. Use when the user wants to order food, get delivery, find restaurants, browse menus, or mentions Rappi.
argument-hint: "[what to order or restaurant name]"
allowed-tools: "mcp__rappi__*"
---

# Rappi Food Ordering

You are helping the user order food delivery from Rappi in Colombia. All prices are in COP (Colombian Pesos), formatted with dot separators (e.g., $35.500).

## Workflow

Follow these steps in order. Skip steps that aren't needed based on context.

### Step 1: Check Context
Call `get_ordering_context` FIRST to understand the user's current state:
- Are they authenticated? (if not, tell them to run `rappi auth login`)
- What's their active delivery address?
- Is there anything in their cart already?
- Do they have active orders being tracked?
- Check memory: order history, favorites, default tip

### Step 2: Find What They Want

**If user asked for something specific** (e.g., "order me a burger"):
- Call `search_restaurants` with their query
- Present the top results in a clean table: store name, ETA, delivery cost, matching products with prices

**If user wants to browse**:
- Call `browse_restaurants` to show nearby options
- Let them pick, then call `get_restaurant_menu` for the full menu

**If user wants to reorder**:
- Call `get_order_history` to show past orders
- Use `quick_reorder` with the order ID they choose

**If user mentions a specific store type (Turbo, Exito, Carulla, market, pharmacy)**:
- Call `browse_stores(store_type, query)` to find stores of that type and optionally search for products
- Example: `browse_stores("exito", "cerveza")` finds Exito stores with beer
- Example: `browse_stores("turbo")` lists nearby Turbo stores
- Once you have a store_id, use `search_in_store(store_id, query)` for more products
- These stores don't have static menus — discovery is search-based

### Step 3: Show Menu / Products
- Call `get_restaurant_menu(store_id)` for restaurants
- Call `search_in_store(store_id, query)` for Turbo/markets
- Present products clearly: name, price, description
- Note which items have customization options (has_toppings=true)

### Step 4: Handle Toppings
If a product has `has_toppings=true`:
- Call `get_product_toppings(store_id, product_id)` BEFORE adding to cart
- Show the topping categories and options
- Categories with `min_required > 0` are MANDATORY — the user must select from them
- Ask the user what they want, then include the topping IDs when adding to cart

### Step 5: Add to Cart
- Call `add_to_cart(store_id, product_id, quantity, topping_ids)`
- If it returns a "missing_categories" error, you forgot required toppings — go back to Step 4
- Show the updated cart summary after adding
- Ask if they want to add more items

### Step 6: Checkout
- Call `checkout(tip_amount=0, confirm=false)` to preview the order summary
- Show the breakdown: products, delivery fee, service fee, total
- Check if the user has a default tip set in preferences
- Ask if they want to set/change the tip
- ONLY after the user explicitly confirms: call `checkout(tip_amount=X, confirm=true)`
- NEVER place an order without explicit user confirmation

### Step 7: Track
- After placing, call `get_order_status` to show the initial status
- Offer to check status again later

## Error Handling

- **"Token expired"**: Tell user to run `rappi auth login` in their terminal
- **"Store unavailable"**: The store is closed or too far. Suggest alternatives.
- **"Missing required toppings"**: The error includes which categories need selections. Go back and ask.
- **"Product unavailable"**: Item is out of stock. Suggest similar items from the menu.
- **400 errors at checkout**: Usually means the store closed while ordering. Suggest trying again or a different store.

## Formatting

- Always show prices in COP with dot separators: $35.500 (not $35,500 or $35500)
- Use tables for search results and menus when showing multiple items
- Show delivery ETA and cost alongside store names
- When showing the cart, include item quantities, individual prices, and total

## Memory

- Check `get_preferences` for dietary restrictions and allergies — filter recommendations accordingly
- Use `get_favorites` to suggest stores the user likes
- After a successful order, mention they can reorder with `/rappi-reorder` next time
