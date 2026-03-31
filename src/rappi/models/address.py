"""Address and geocoding models."""

from pydantic import BaseModel


class City(BaseModel):
    id: int | None = None
    city: str | None = None


class Address(BaseModel):
    id: int
    address: str | None = None
    active: bool = False
    lat: float = 0.0
    lng: float = 0.0
    description: str | None = None
    tag: str | None = None
    city: City | None = None
    count_orders: int = 0
    instructions: str | None = None
    title: str | None = None
    subtitle: str | None = None


class AddressListResponse(BaseModel):
    addresses: list[Address] = []


class GeoLocation(BaseModel):
    original_text: str | None = None
    full_text: str | None = None
    full_text_to_show: str | None = None
    matched: bool = False
