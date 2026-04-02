---
name: rappi-suggest
description: Smart food suggestions based on your taste profile and ordering habits. Use when the user asks "what should I eat?", "suggest something", "I'm hungry but don't know what", or wants personalized recommendations.
argument-hint: "[optional: 'lunch', 'something cheap', 'burger place']"
allowed-tools: "mcp__rappi__get_taste_profile,mcp__rappi__get_recommendations,mcp__rappi__get_ordering_context,mcp__rappi__search_restaurants,mcp__rappi__browse_stores,mcp__rappi__get_restaurant_menu,mcp__rappi__add_to_cart,mcp__rappi__checkout,mcp__rappi__view_cart,mcp__rappi__quick_reorder"
---

# Rappi Smart Suggestions

Help the user decide what to eat based on their personal taste profile and ordering habits.

## Steps

1. Call `get_recommendations` with any context the user provided (e.g., "lunch", "something cheap", $ARGUMENTS).

2. Present recommendations grouped by type:

   **Your Usual** (type="usual"):
   - Show the store name and items they always order
   - "You order [items] from [store] regularly — want the usual?"
   - Action: offer to `quick_reorder` if order exists, or `add_to_cart` for each item

   **Right Now** (type="time_based"):
   - "You usually order from [store] around this time"
   - Action: offer to browse their menu with `get_restaurant_menu`

   **Try Something New** (type="new_store"):
   - "You haven't tried [store] yet"
   - Action: offer to `search_restaurants` or `get_restaurant_menu`

3. For each recommendation, offer a clear next action the user can take.

4. If the user wants deeper insight into their habits, call `get_taste_profile` and present:
   - Top food categories with percentages ("Hamburguesas 40%, Bebidas 25%")
   - Favorite stores and how often they order from each
   - Spending patterns (average per order, total this month)
   - Time habits ("You mostly order at lunch")
   - Top topping preferences

5. If the user picks a recommendation, transition into the ordering flow:
   - Use `quick_reorder` for "usual" recommendations
   - Use `get_restaurant_menu` + `add_to_cart` for specific stores
   - Always confirm before checkout

6. Prices in COP, formatted as $35.500.
