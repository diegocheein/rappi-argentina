"""Address management services."""

from rappi.client import RappiAPIError, RappiClient
from rappi.constants import Endpoints
from rappi.models.address import Address, AddressListResponse, GeoLocation


async def list_addresses(client: RappiClient) -> list[Address]:
    """Get all saved delivery addresses."""
    data = await client.get(Endpoints.LIST_ADDRESSES)
    response = AddressListResponse(**data)
    return response.addresses


async def set_active_address(client: RappiClient, address_id: int) -> None:
    """Set an address as the active delivery address and update config coordinates.

    The server-side activation endpoint differs by country (absent/404 on AR),
    so it's best-effort. The coordinate sync — which is what searches and the
    catalog actually depend on — always runs from the address list.
    """
    try:
        path = Endpoints.SET_ACTIVE_ADDRESS.format(address_id=address_id)
        await client.put(path, json={})
    except RappiAPIError:
        pass  # country without this endpoint — coordinates still sync below

    # Update local config with the address coordinates
    addresses = await list_addresses(client)
    for addr in addresses:
        if addr.id == address_id:
            client.config_manager.update(
                lat=addr.lat,
                lng=addr.lng,
                active_address_id=addr.id,
            )
            break


async def reverse_geocode(client: RappiClient, lat: float, lng: float) -> GeoLocation:
    """Get a human-readable address from coordinates."""
    data = await client.get(
        Endpoints.REVERSE_GEOCODE,
        params={"client": "locationservices", "lat": lat, "lng": lng},
    )
    return GeoLocation(**data)
