"""Search services for products and stores."""

from rappi.client import RappiClient
from rappi.constants import Endpoints
from rappi.models.store import SearchResponse, SearchStore


async def search(
    client: RappiClient,
    query: str,
    store_id: int | None = None,
) -> list[SearchStore]:
    """Search for products and stores by keyword.

    Args:
        client: RappiClient instance
        query: Search term
        store_id: If provided, only return results from this store
    """
    data = await client.post(
        Endpoints.UNIFIED_SEARCH,
        params={"is_prime": "false"},
        json={
            "query": query,
            "lat": client.config.lat,
            "lng": client.config.lng,
        },
    )
    response = SearchResponse(**data)

    stores = response.stores
    if store_id is not None:
        stores = [s for s in stores if s.store_id == store_id]

    # Record to memory (best-effort)
    if client.memory:
        try:
            await client.memory.record_search_results(query, stores)
        except Exception:
            pass

    return stores
