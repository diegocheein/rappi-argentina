"""Models for dynamic content — store aisles, categories, store info."""

from pydantic import BaseModel


class Aisle(BaseModel):
    """A category/aisle within a store."""
    id: int | str | None = None
    name: str | None = None
    image: str | None = None
    product_count: int = 0


class AisleProduct(BaseModel):
    """A product within an aisle."""
    id: int | str | None = None
    name: str | None = None
    price: float = 0
    real_price: float = 0
    image: str | None = None
    in_stock: bool = True
    has_toppings: bool = False
    description: str | None = None
    quantity_label: str | None = None
    brand: str | None = None
    category_name: str | None = None
