"""Order tracking services."""

from rappi.client import RappiClient
from rappi.constants import Endpoints
from rappi.models.order import OrdersResponse


async def get_orders(client: RappiClient) -> OrdersResponse:
    """Get active and cancelled orders."""
    data = await client.get(Endpoints.GET_ORDERS)
    return OrdersResponse(**data)


async def get_order_resume(client: RappiClient, order_id: int) -> dict:
    """Get full order summary — products, totals, store, address."""
    path = Endpoints.ORDER_RESUME.format(order_id=order_id)
    return await client.get(path)


async def get_order_realtime_state(client: RappiClient, order_id: int) -> dict:
    """Get real-time order state — flow_key, timeline, ETA, map positions."""
    path = Endpoints.ORDER_REALTIME_STATE.format(order_id=order_id)
    return await client.get(path)


async def get_order_products(client: RappiClient, order_id: int) -> list[dict]:
    """Get order products detail."""
    path = Endpoints.ORDER_PRODUCTS.format(order_id=order_id)
    data = await client.get(path)
    if isinstance(data, list):
        return data
    return data.get("products", data.get("data", []))


async def get_order_cost_breakdown(client: RappiClient, order_id: int) -> dict:
    """Get full cost breakdown — subtotal, fees, discounts, tip."""
    path = Endpoints.ORDER_COST_BREAKDOWN.format(order_id=order_id)
    return await client.get(path)
