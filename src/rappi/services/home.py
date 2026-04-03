"""Homepage verticals and store type discovery."""

from rappi.client import RappiClient
from rappi.constants import Endpoints


async def get_home_verticals(client: RappiClient) -> list[dict]:
    """Get all available verticals for the user's location (Restaurants, Turbo, Markets, etc.)."""
    data = await client.get(
        Endpoints.HOME_VERTICALS,
        params={"lat": client.config.lat, "lng": client.config.lng, "source": "web"},
    )
    if isinstance(data, list):
        return data
    # Response is {body: [{content: [...verticals...]}], header, footer}
    body = data.get("body", [])
    if body and isinstance(body, list):
        content = body[0].get("content", [])
        if isinstance(content, list) and content:
            return content
    return data.get("verticals", data.get("data", []))


async def get_store_types(client: RappiClient) -> list[dict]:
    """Get the full store type hierarchy with suboptions."""
    data = await client.get(
        Endpoints.STORE_TYPE_HIERARCHY,
        params={"lat": client.config.lat, "lng": client.config.lng, "view": "web"},
    )
    if isinstance(data, list):
        return data
    return data.get("store_types", data.get("data", []))
