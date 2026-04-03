"""Dynamic content service — store aisles, categories, store info.

All calls go to a single endpoint with different `context` values.
"""

from rappi.client import RappiClient
from rappi.constants import Endpoints, HEADERS_BROWSE


async def _fetch_dynamic_content(
    client: RappiClient, context: str, state: dict
) -> dict:
    """Core POST to the dynamic content endpoint."""
    # The API expects all state values as strings (including lists → comma-separated)
    str_state = {}
    for k, v in state.items():
        if isinstance(v, list):
            str_state[k] = ",".join(str(item) for item in v)
        else:
            str_state[k] = str(v) if not isinstance(v, str) else v

    payload = {
        "context": context,
        "state": {
            "lat": str(client.config.lat),
            "lng": str(client.config.lng),
            **str_state,
        },
    }
    return await client.post(Endpoints.DYNAMIC_CONTENT, json=payload, headers=HEADERS_BROWSE)


def _extract_components(data: dict) -> list[dict]:
    """Extract the components array from the dynamic content response."""
    if isinstance(data, list):
        return data
    # Response is {data: {components: [...], context_info: {...}}}
    inner = data.get("data", data)
    if isinstance(inner, dict):
        return inner.get("components", inner.get("content", []))
    return []


def _extract_context_info(data: dict) -> dict:
    """Extract context_info (store availability, etc.) from the response."""
    inner = data.get("data", data)
    if isinstance(inner, dict):
        return inner.get("context_info", {})
    return {}


async def get_store_aisles(
    client: RappiClient, store_id: int, store_type: str = "turbo", parent_store_type: str = "turbo_home"
) -> list[dict]:
    """Get aisles/categories for a store (store_home context)."""
    data = await _fetch_dynamic_content(client, "store_home", {
        "store_type": store_type,
        "parent_store_type": parent_store_type,
        "stores": [store_id],
    })
    components = _extract_components(data)
    aisles = []
    for comp in components:
        if not isinstance(comp, dict):
            continue
        # Look for aisle/category data in various possible response shapes
        comp_type = comp.get("type", comp.get("component_type", ""))
        if "aisle" in str(comp_type).lower() or "corridor" in str(comp_type).lower() or "category" in str(comp_type).lower():
            items = comp.get("data", comp.get("items", comp.get("aisles", [])))
            if isinstance(items, list):
                aisles.extend(items)
        # Some responses nest aisles in a "resource" key
        resource = comp.get("resource", {})
        if isinstance(resource, dict) and "aisles" in resource:
            aisles.extend(resource["aisles"])
    # If no aisles found, include context info (store may be closed)
    if not aisles and not components:
        ctx = _extract_context_info(data)
        store = ctx.get("store", {})
        return [{"_store_status": {
            "is_available": store.get("is_available"),
            "eta": store.get("eta_value"),
            "hint": "Store may be closed — aisles only load when the store is active.",
        }}]
    return aisles if aisles else components


async def get_aisle_products(
    client: RappiClient, store_id: int, aisle_id: int | str,
    store_type: str = "turbo", parent_store_type: str = "turbo_home"
) -> list[dict]:
    """Get products within a specific aisle (sub_aisles context)."""
    data = await _fetch_dynamic_content(client, "sub_aisles", {
        "store_type": store_type,
        "parent_store_type": parent_store_type,
        "stores": [store_id],
        "aisle_id": aisle_id,
        "parent_id": aisle_id,
    })
    components = _extract_components(data)
    products = []
    for comp in components:
        if not isinstance(comp, dict):
            continue
        # Look for product data
        items = comp.get("data", comp.get("items", comp.get("products", [])))
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and ("name" in item or "product_name" in item):
                    products.append(item)
        resource = comp.get("resource", {})
        if isinstance(resource, dict) and "products" in resource:
            products.extend(resource["products"])
    return products if products else components


async def get_store_information(
    client: RappiClient, store_id: int, parent_store_type: str = "turbo_home"
) -> dict:
    """Get store details — hours, charges, address (store_information context)."""
    data = await _fetch_dynamic_content(client, "store_information", {
        "parent_store_type": parent_store_type,
        "stores": [store_id],
    })
    components = _extract_components(data)
    # Return the first meaningful component or the full response
    for comp in components:
        if isinstance(comp, dict) and ("name" in comp or "address" in comp or "resource" in comp):
            return comp.get("resource", comp)
    return data


async def get_market_categories(
    client: RappiClient, parent_store_type: str = "market"
) -> list[dict]:
    """Get market landing categories (cpgs_landing context)."""
    data = await _fetch_dynamic_content(client, "cpgs_landing", {
        "parent_store_type": parent_store_type,
    })
    components = _extract_components(data)
    categories = []
    for comp in components:
        if isinstance(comp, dict):
            items = comp.get("data", comp.get("items", comp.get("categories", [])))
            if isinstance(items, list):
                categories.extend(items)
    return categories if categories else components
