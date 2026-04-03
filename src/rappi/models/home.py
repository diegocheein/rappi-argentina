"""Models for homepage verticals and store type discovery."""

from pydantic import BaseModel


class Vertical(BaseModel):
    """A top-level category on the Rappi homepage."""
    store_type: str | None = None
    friendly_url: str | None = None
    description: str | None = None
    image: str | None = None
    is_main: bool = False
    order_index: int = 0


class StoreTypeInfo(BaseModel):
    """A store type from the hierarchy endpoint."""
    id: str | None = None
    friendly_url: str | None = None
    description: str | None = None
    parent_id: str | None = None
    home_type_id: str | None = None
    store_count: int = 0
    is_available: bool = True
