"""Cart management services."""

from rappi.client import RappiClient
from rappi.constants import Endpoints
from rappi.models.cart import Cart, CartTopping
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


def _build_add_payload(
    store_id: int,
    product: Product,
    toppings: list[Topping] | None = None,
    quantity: int = 1,
) -> list[dict]:
    """Build the full cart PUT payload for adding a product."""
    compound_id = make_compound_id(store_id, product.id)
    topping_payload = _build_topping_payload(toppings) if toppings else []

    return [
        {
            "id": store_id,
            "place_at": "",
            "delivery_method": "delivery",
            "products": [
                {
                    "id": compound_id,
                    "product_id": product.id,
                    "name": product.name,
                    "description": product.name,
                    "comment": "",
                    "toppings": topping_payload,
                    "units": quantity,
                    "price": product.price,
                    "real_price": product.real_price or product.price,
                    "markup_price": product.price,
                    "sale_type": "U",
                    "sale_type_origin": "U",
                    "unit_type": "U",
                    "category_id": 0,
                    "category_name": "",
                    "pum": "0",
                    "is_sponsored": False,
                    "ad_provider_metadata": "",
                    "in_stock": True,
                }
            ],
        }
    ]


async def add_to_cart(
    client: RappiClient,
    store_id: int,
    product: Product,
    toppings: list[Topping] | None = None,
    quantity: int = 1,
    store_type: str = "restaurant",
) -> list[Cart]:
    """Add a product to the cart. Returns updated carts."""
    payload = _build_add_payload(store_id, product, toppings, quantity)
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
    compound_product_id: str,
    store_type: str = "restaurant",
) -> None:
    """Remove a product from the cart by its compound ID."""
    path = Endpoints.CART_REMOVE.format(
        store_type=store_type,
        compound_product_id=compound_product_id,
    )
    await client.delete(path)


async def recalculate_cart(
    client: RappiClient, store_type: str = "restaurant"
) -> Cart:
    """Recalculate cart totals."""
    path = Endpoints.CART_RECALCULATE.format(store_type=store_type)
    data = await client.post(path, json={})
    return Cart(**data)
