"""Checkout and payment services."""

from rappi.client import RappiClient
from rappi.constants import Endpoints, HEADERS_CHECKOUT
from rappi.models.order import CheckoutDetail


async def get_checkout_detail(
    client: RappiClient, store_type: str = "restaurant"
) -> CheckoutDetail:
    """Get checkout summary with price breakdown and return_key."""
    path = Endpoints.CHECKOUT_DETAIL.format(store_type=store_type)
    data = await client.get(path)
    return CheckoutDetail(**data)


async def get_tip_suggestions(client: RappiClient) -> dict:
    """Get suggested tip amounts based on current cart.

    Returns suggested amounts with labels (percentages) and absolute values.
    Example: {tips: [{key: "7%", price: 6500}, {key: "5%", price: 4600, default: true}]}
    """
    return await client.get(Endpoints.TIP_SUGGESTIONS)


async def set_tip(
    client: RappiClient, tip_amount: int, store_type: str = "restaurant"
) -> None:
    """Set the delivery tip amount then recalculate cart totals.

    tip_amount is an absolute value in COP (e.g., 2000 = $2,000 COP), not a percentage.
    Use 0 to remove tip. Always recalculates cart after setting tip.
    """
    path = Endpoints.SET_TIP.format(store_type=store_type)
    await client.put(path, json={"tip": tip_amount})
    # Recalculate cart totals so the tip is reflected in the checkout summary
    recalc_path = Endpoints.CART_RECALCULATE.format(store_type=store_type)
    await client.post(recalc_path, json={})


async def set_payment_method(
    client: RappiClient, payment_data: dict, store_type: str = "restaurant"
) -> None:
    """Set the payment method for checkout."""
    path = Endpoints.SET_PAYMENT_METHOD.format(store_type=store_type)
    await client.put(path, json=payment_data)


async def place_order(
    client: RappiClient, return_key: str, store_type: str = "restaurant"
) -> dict:
    """Place the order. Requires return_key from checkout detail."""
    path = Endpoints.PLACE_ORDER.format(store_type=store_type)
    return await client.post(path, json={"return_key": return_key})


async def get_payment_methods(client: RappiClient) -> dict:
    """Get available payment methods and saved cards."""
    try:
        return await client.get(
            Endpoints.DEFAULT_PAYMENT_METHOD,
            params={"origin": "DEBT", "store_type": ""},
            headers=HEADERS_CHECKOUT,
        )
    except Exception:
        return {"error": "Could not fetch payment methods."}
