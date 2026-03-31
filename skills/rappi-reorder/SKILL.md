---
name: rappi-reorder
description: Reorder from Rappi order history. Use when the user wants to order the same thing again, reorder, or mentions a past order.
allowed-tools: "mcp__rappi__get_order_history,mcp__rappi__quick_reorder,mcp__rappi__checkout,mcp__rappi__view_cart,mcp__rappi__get_ordering_context"
---

# Rappi Quick Reorder

Help the user reorder from their order history.

## Steps

1. Call `get_order_history(limit=10)` to fetch recent orders.

2. If no history exists, tell the user they haven't placed any orders yet through the CLI and suggest using `/order-food`.

3. Present past orders in a numbered list:
   - Store name
   - Items ordered (with quantities)
   - Total price
   - Date

4. Ask the user which order they want to reorder (by number).

5. Call `quick_reorder(order_id)` with the selected order's ID.
   - This re-adds all available items to the cart
   - It reports which items were added and which failed (unavailable/out of stock)

6. Call `view_cart` to show what's in the cart now.

7. If some items failed, ask if they want to proceed with what was added or find replacements.

8. Call `checkout(confirm=false)` to show the order summary.

9. After user confirms, call `checkout(tip_amount=X, confirm=true)` to place the order.
   - Check preferences for a default tip amount
   - NEVER place without explicit user confirmation

Prices are in COP — format as $35.500.
