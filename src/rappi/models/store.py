"""Store, product, menu, and topping models."""

from pydantic import BaseModel, model_validator

from rappi.constants import resolve_image_url


class SearchProduct(BaseModel):
    name: str
    price: float = 0
    product_id: int | str = 0
    store_id: int = 0
    image: str | None = None
    in_stock: bool = True
    has_toppings: bool = False
    discount: float = 0
    sale_type: str | None = None
    real_price: float = 0
    unit_type: str | None = None
    category_name: str | None = None
    presentation: str | None = None

    @model_validator(mode="after")
    def _normalize(self):
        self.image = resolve_image_url(self.image, "products")
        if not self.real_price:
            self.real_price = self.price
        # Ensure product_id is int for consistency
        if isinstance(self.product_id, str):
            try:
                self.product_id = int(self.product_id)
            except ValueError:
                pass
        return self


class SearchStore(BaseModel):
    store_id: int
    store_name: str | None = None
    store_type: str | None = None
    logo: str | None = None
    eta: str | None = None
    eta_value: int | None = None
    shipping_cost: float = 0
    products: list[SearchProduct] = []

    @model_validator(mode="after")
    def _resolve_logo(self):
        self.logo = resolve_image_url(self.logo, "restaurants_logo")
        return self


class SearchResponse(BaseModel):
    stores: list[SearchStore] = []


class CatalogStore(BaseModel):
    store_id: int
    name: str | None = None
    logo: str | None = None
    eta: str | None = None
    score: float | None = None
    shipping_cost: float = 0
    is_available: bool = True

    @model_validator(mode="after")
    def _resolve_logo(self):
        self.logo = resolve_image_url(self.logo, "restaurants_logo")
        return self


class CatalogResponse(BaseModel):
    stores: list[CatalogStore] = []


class Product(BaseModel):
    id: int | str  # can be int or compound "storeId_productId" from menu endpoint
    name: str
    description: str | None = None
    price: float = 0
    real_price: float = 0
    image: str | None = None
    in_stock: bool = True
    has_toppings: bool = False
    is_available: bool | None = None  # menu endpoint uses this instead of in_stock

    @model_validator(mode="after")
    def _normalize(self):
        self.image = resolve_image_url(self.image, "products")
        # Menu endpoint uses is_available; normalize to in_stock
        if self.is_available is not None:
            self.in_stock = self.is_available
        # Menu endpoint returns compound ID as string; extract numeric product_id
        if isinstance(self.id, str) and "_" in self.id:
            self.id = int(self.id.split("_", 1)[1])
        elif isinstance(self.id, str):
            self.id = int(self.id)
        return self


class Corridor(BaseModel):
    id: int
    name: str
    products: list[Product] = []


class StoreStatus(BaseModel):
    status: str | None = None


class StoreBrand(BaseModel):
    id: int | None = None
    name: str | None = None


class StoreDetail(BaseModel):
    store_id: int
    name: str | None = None
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    logo: str | None = None
    background: str | None = None
    status: StoreStatus | None = None
    store_type_id: str | None = None  # "restaurant", "turbo", etc.
    type: str | None = None
    min_cooking_time: int | None = None
    max_cooking_time: int | None = None
    brand: StoreBrand | None = None
    corridors: list[Corridor] = []

    @property
    def is_restaurant(self) -> bool:
        return (self.store_type_id or self.type or "restaurant") == "restaurant"

    @property
    def effective_store_type(self) -> str:
        return self.store_type_id or self.type or "restaurant"

    @model_validator(mode="after")
    def _resolve_images(self):
        self.logo = resolve_image_url(self.logo, "restaurants_logo")
        self.background = resolve_image_url(self.background, "restaurants_background")
        return self


class Topping(BaseModel):
    id: int
    description: str | None = None
    price: float = 0
    is_available: bool = True
    image: str | None = None


class ToppingCategory(BaseModel):
    id: int
    description: str | None = None
    topping_type_id: str | None = None
    min_toppings_for_categories: int = 0
    max_toppings_for_categories: int = 0
    toppings: list[Topping] = []


class ToppingsResponse(BaseModel):
    categories: list[ToppingCategory] = []
