"""Store detail, menu, and catalog services."""

from rappi.client import RappiClient
from rappi.constants import Endpoints
from rappi.models.store import (
    CatalogResponse,
    CatalogStore,
    Corridor,
    Product,
    SearchStore,
    StoreDetail,
    ToppingsResponse,
)


async def get_restaurant_catalog(
    client: RappiClient, offset: int = 0, limit: int = 20
) -> list[CatalogStore]:
    """Browse nearby restaurants (paginated)."""
    data = await client.post(
        Endpoints.RESTAURANT_CATALOG,
        json={
            "lat": client.config.lat,
            "lng": client.config.lng,
            "store_type": "restaurant",
            "offset": offset,
            "limit": limit,
        },
    )
    response = CatalogResponse(**data)
    return response.stores


async def _fetch_menu(client: RappiClient, store_id: int) -> list[Corridor]:
    """Fetch menu corridors from the dedicated menu endpoint."""
    path = Endpoints.STORE_MENU.format(store_id=store_id)
    data = await client.get(path)
    raw_corridors = data.get("corridors", [])
    return [Corridor(**c) for c in raw_corridors]


def _search_results_to_corridors(search_store: SearchStore) -> list[Corridor]:
    """Convert search results into corridor format, grouped by category."""
    categories: dict[str, list[Product]] = {}
    for sp in search_store.products:
        cat_name = sp.category_name or "Products"
        if cat_name not in categories:
            categories[cat_name] = []
        categories[cat_name].append(Product(
            id=sp.product_id,
            name=sp.name,
            price=sp.price,
            real_price=sp.real_price or sp.price,
            image=sp.image,
            in_stock=sp.in_stock,
            has_toppings=sp.has_toppings,
            description=sp.presentation,
        ))
    return [
        Corridor(id=i, name=name, products=prods)
        for i, (name, prods) in enumerate(categories.items(), 1)
    ]


async def get_store_detail(client: RappiClient, store_id: int) -> StoreDetail:
    """Get a store's full info and menu.

    For restaurants: fetches menu from the dedicated menu endpoint.
    For other stores (turbo, markets): menu endpoint returns empty,
    corridors must be populated separately via search.
    """
    # Fetch store info
    path = Endpoints.STORE_DETAIL.format(store_id=store_id)
    data = await client.get(path)
    store = StoreDetail(**data)

    # Fetch menu from dedicated endpoint
    store.corridors = await _fetch_menu(client, store_id)

    # Cache store and menu products (best-effort)
    if client.memory:
        try:
            await client.memory.stores.upsert(
                store.store_id, store.name, store.effective_store_type,
                store.logo, store.address, store.lat, store.lng,
            )
            if store.corridors:
                await client.memory.cache_store_menu(store.store_id, store.corridors)
        except Exception:
            pass

    return store


async def search_store_products(
    client: RappiClient, store_id: int, query: str
) -> list[Corridor]:
    """Search for products within a specific store. Returns results grouped as corridors.

    This is the primary way to browse non-restaurant stores (Turbo, markets, pharmacies)
    which don't have a static menu endpoint.
    """
    from rappi.services.search import search

    stores = await search(client, query, store_id=store_id)
    if not stores:
        return []
    return _search_results_to_corridors(stores[0])


async def get_product_toppings(
    client: RappiClient, store_id: int, product_id: int
) -> ToppingsResponse:
    """Get customization options for a product."""
    path = Endpoints.PRODUCT_TOPPINGS.format(store_id=store_id, product_id=product_id)
    data = await client.get(path)
    return ToppingsResponse(**data)
