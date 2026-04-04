"""Cart management services.

CRITICAL: The cart PUT endpoint is a FULL REPLACEMENT operation.
Sending only the new item replaces the entire cart. You must:
1. GET the current cart
2. Merge the new item into the existing products array
3. PUT the full list

Same for remove: PUT the full array minus the removed item.
Clear cart: PUT an empty array [].
"""

from rappi.client import RappiClient
from rappi.constants import Endpoints
from rappi.models.cart import Cart, CartProduct, CartStore, CartTopping
from rappi.models.store import Product, Topping
from rappi.utils.ids import make_compound_id


def _build_topping_payload(toppings: list[Topping]) -> list[dict]:
    """Convert Topping model objects into the cart API's expected format."""
    return [
        {
            "id": t.id,
            "description": t.description or "",
            "units": 1,
            "price": t.price,
        }
        for t in toppings
    ]


def _cart_product_to_payload(cp: CartProduct) -> dict:
    """Convert an existing CartProduct back into the PUT payload format."""
    return {
        "id": cp.id,
        "units": cp.units,
        "sale_type": "U",
        "toppings": [
            {"id": t.id, "description": t.description, "units": t.units, "price": t.price}
            for t in cp.toppings
        ],
    }


def _new_product_payload(
    store_id: int,
    product: Product,
    toppings: list[Topping] | None = None,
    quantity: int = 1,
) -> dict:
    """Build the payload dict for a new product being added."""
    compound_id = make_compound_id(store_id, product.id)
    topping_payload = _build_topping_payload(toppings) if toppings else []
    return {
        "id": compound_id,
        "units": quantity,
        "sale_type": "U",
        "toppings": topping_payload,
    }


async def _get_existing_cart_products(
    client: RappiClient, store_id: int
) -> list[dict]:
    """Get the current products array for a store from the cart.

    Returns the products as payload-ready dicts for the PUT body.
    """
    carts = await get_carts(client)
    for cart in carts:
        for store in cart.stores:
            if store.id == store_id:
                return [_cart_product_to_payload(p) for p in store.products]
    return []


async def add_to_cart(
    client: RappiClient,
    store_id: int,
    product: Product,
    toppings: list[Topping] | None = None,
    quantity: int = 1,
    store_type: str = "restaurant",
) -> list[Cart]:
    """Add a product to the cart. Merges with existing cart contents.

    The cart API is a full-replacement PUT — we must send ALL items,
    not just the new one. This function:
    1. Gets the current cart for this store
    2. Appends the new product
    3. PUTs the full list
    """
    # Get existing products in cart for this store
    existing_products = await _get_existing_cart_products(client, store_id)

    # Build the new product entry
    new_product = _new_product_payload(store_id, product, toppings, quantity)

    # Check if this product already exists in cart (update quantity instead of duplicate)
    compound_id = make_compound_id(store_id, product.id)
    found = False
    for p in existing_products:
        if p["id"] == compound_id:
            p["units"] = p.get("units", 1) + quantity
            found = True
            break

    if not found:
        existing_products.append(new_product)

    # PUT the full cart (all products for this store)
    payload = [
        {
            "id": store_id,
            "products": existing_products,
        }
    ]

    path = Endpoints.CART_ADD.format(store_type=store_type)
    data = await client.put(path, json=payload)
    if isinstance(data, list):
        return [Cart(**c) for c in data]
    return [Cart(**data)]


async def get_carts(client: RappiClient) -> list[Cart]:
    """Get all current carts."""
    data = await client.post(Endpoints.CART_GET_ALL, json={})
    if isinstance(data, list):
        return [Cart(**c) for c in data]
    return []


async def remove_from_cart(
    client: RappiClient,
    store_id: int,
    compound_product_id: str,
    store_type: str = "restaurant",
) -> list[Cart]:
    """Remove a product from the cart.

    Uses the same full-replacement PUT — sends all products minus the removed one.
    """
    # Get existing products
    existing_products = await _get_existing_cart_products(client, store_id)

    # Filter out the product to remove
    remaining = [p for p in existing_products if p["id"] != compound_product_id]

    if len(remaining) == len(existing_products):
        # Product wasn't in the cart — try without store prefix
        remaining = [p for p in existing_products if not p["id"].endswith(f"_{compound_product_id}")]

    # PUT the remaining products (or empty to clear this store)
    if remaining:
        payload = [{"id": store_id, "products": remaining}]
    else:
        payload = []

    path = Endpoints.CART_ADD.format(store_type=store_type)
    data = await client.put(path, json=payload)
    if isinstance(data, list):
        return [Cart(**c) for c in data]
    return []


async def clear_cart(
    client: RappiClient,
    store_type: str = "restaurant",
) -> None:
    """Clear the entire cart by sending an empty array."""
    path = Endpoints.CART_ADD.format(store_type=store_type)
    await client.put(path, json=[])


async def recalculate_cart(
    client: RappiClient, store_type: str = "restaurant"
) -> Cart:
    """Recalculate cart totals."""
    path = Endpoints.CART_RECALCULATE.format(store_type=store_type)
    data = await client.post(path, json={})
    return Cart(**data)
