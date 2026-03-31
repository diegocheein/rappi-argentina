"""Cart models."""

from pydantic import BaseModel


class CartTopping(BaseModel):
    id: int
    description: str = ""
    units: int = 1
    price: float = 0


class CartCharge(BaseModel):
    charge_type: str | None = None
    total: float = 0


class CartProduct(BaseModel):
    id: str  # compound: "storeId_productId"
    name: str | None = None
    units: int = 1
    price: float = 0
    total: float = 0
    available: bool = True
    toppings: list[CartTopping] = []


class CartStore(BaseModel):
    id: int
    name: str | None = None
    available: bool = True
    is_open: bool = True
    eta_label: str | None = None
    charge_total: float = 0
    product_total: float = 0
    total: float = 0
    valid: bool = True
    products: list[CartProduct] = []
    charges: list[CartCharge] = []


class Cart(BaseModel):
    id: str | None = None
    store_type: str | None = None
    stores: list[CartStore] = []
    product_total: float = 0
    shipping_total: float = 0
    sub_total: float = 0
