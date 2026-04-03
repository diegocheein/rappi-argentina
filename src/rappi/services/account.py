"""Account services — favorites from API, credits, active orders."""

from rappi.client import RappiClient
from rappi.constants import Endpoints


async def get_favorite_stores_api(client: RappiClient) -> list[dict]:
    """Get favorite stores from Rappi's API (richer than local memory)."""
    try:
        data = await client.post(
            Endpoints.FAVORITE_STORES_API,
            json={"lat": client.config.lat, "lng": client.config.lng},
        )
        if isinstance(data, list):
            return data
        return data.get("stores", data.get("data", []))
    except Exception:
        # Endpoint may need additional params — fall back gracefully
        return []


async def get_rappi_credits(client: RappiClient) -> dict:
    """Get Rappi credits/wallet balance."""
    data = await client.get(Endpoints.RAPPI_CREDITS)
    return data


async def get_active_orders_v3(client: RappiClient) -> list[dict]:
    """Get active orders using the newer v3 endpoint."""
    data = await client.get(Endpoints.ACTIVE_ORDERS_V3)
    if isinstance(data, list):
        return data
    return data.get("orders", data.get("data", []))
