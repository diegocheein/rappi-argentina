"""Taste profile and recommendation models."""

from pydantic import BaseModel


class CategoryPreference(BaseModel):
    category_name: str
    order_count: int
    percentage: float


class StoreTypePreference(BaseModel):
    store_type: str
    order_count: int
    percentage: float


class PriceRange(BaseModel):
    avg_order_total: float = 0
    avg_item_price: float = 0
    min_order_total: float = 0
    max_order_total: float = 0


class TimePattern(BaseModel):
    hour_distribution: dict[str, int] = {}  # "morning": 5, "lunch": 12
    day_distribution: dict[str, int] = {}   # "monday": 3
    peak_hour_slot: str | None = None       # "lunch"
    peak_day: str | None = None             # "saturday"


class ToppingPreference(BaseModel):
    topping_description: str
    count: int


class TopProduct(BaseModel):
    product_id: str
    product_name: str
    total_quantity: int
    order_count: int
    store_name: str | None = None


class TopStore(BaseModel):
    store_id: int
    store_name: str | None = None
    store_type: str | None = None
    order_count: int
    last_ordered: str | None = None


class SpendingSummary(BaseModel):
    total_spent: float = 0
    order_count: int = 0
    avg_per_order: float = 0
    avg_tip: float = 0
    orders_per_week: float = 0


class TasteProfile(BaseModel):
    category_preferences: list[CategoryPreference] = []
    store_type_preferences: list[StoreTypePreference] = []
    price_range: PriceRange = PriceRange()
    time_patterns: TimePattern = TimePattern()
    topping_preferences: list[ToppingPreference] = []
    top_products: list[TopProduct] = []
    top_stores: list[TopStore] = []
    spending: SpendingSummary = SpendingSummary()
    taste_vector: list[float] | None = None
    dietary_restrictions: list[str] = []
    allergies: list[str] = []
    computed_at: str = ""


class Recommendation(BaseModel):
    type: str           # "usual", "time_based", "product", "new_store", "budget_alert"
    title: str
    description: str
    store_id: int | None = None
    store_name: str | None = None
    product_id: str | None = None
    product_name: str | None = None
    confidence: float = 0.0
    items: list[dict] | None = None


class RecommendationSet(BaseModel):
    recommendations: list[Recommendation] = []
    context: dict = {}
    profile_summary: str = ""
