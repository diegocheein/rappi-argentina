"""Order tracking services."""

from rappi.client import RappiClient
from rappi.constants import Endpoints
from rappi.models.order import OrdersResponse


async def get_orders(client: RappiClient) -> OrdersResponse:
    """Get active and cancelled orders."""
    data = await client.get(Endpoints.GET_ORDERS)
    return OrdersResponse(**data)
