"""Tests for all Pydantic models in rappi.models.*"""

import pytest

from rappi.models.user import UserProfile, PrimeStatus, LoyaltyInfo
from rappi.models.address import Address, AddressListResponse, GeoLocation, City
from rappi.models.store import (
    SearchProduct,
    SearchStore,
    SearchResponse,
    CatalogStore,
    CatalogResponse,
    Product,
    Corridor,
    StoreDetail,
    StoreStatus,
    StoreBrand,
    Topping,
    ToppingCategory,
    ToppingsResponse,
)
from rappi.models.cart import Cart, CartProduct, CartStore, CartTopping, CartCharge
from rappi.models.order import (
    CheckoutDetail,
    CheckoutDetailItem,
    CheckoutSummary,
    CheckoutHeader,
    Order,
    OrderStore,
    OrdersResponse,
)
from rappi.models.intelligence import (
    TasteProfile,
    Recommendation,
    RecommendationSet,
    CategoryPreference,
    PriceRange,
    TimePattern,
    SpendingSummary,
    TopProduct,
    TopStore,
)


# ---------------------------------------------------------------------------
# User models (§1 Auth)
# ---------------------------------------------------------------------------

class TestUserProfile:
    def test_minimal(self):
        p = UserProfile(id=1)
        assert p.id == 1
        assert p.first_name is None
        assert p.vip is False

    def test_full(self):
        p = UserProfile(
            id=42, first_name="Gabriel", last_name="G",
            email="g@test.com", phone="555", vip=True,
            loyalty={"name": "Gold", "type": "premium"},
        )
        assert p.first_name == "Gabriel"
        assert p.loyalty.name == "Gold"


class TestPrimeStatus:
    def test_default_not_prime(self):
        assert PrimeStatus().is_prime is False

    def test_is_prime(self):
        assert PrimeStatus(is_prime=True).is_prime is True


# ---------------------------------------------------------------------------
# Address models (§2)
# ---------------------------------------------------------------------------

class TestAddress:
    def test_defaults(self):
        a = Address(id=1)
        assert a.active is False
        assert a.lat == 0.0

    def test_with_city(self):
        a = Address(id=1, city={"id": 10, "city": "Bogota"})
        assert a.city.city == "Bogota"


class TestAddressListResponse:
    def test_empty(self):
        r = AddressListResponse()
        assert r.addresses == []

    def test_with_addresses(self):
        r = AddressListResponse(addresses=[
            {"id": 1, "address": "Calle 1", "active": True},
            {"id": 2, "address": "Calle 2"},
        ])
        assert len(r.addresses) == 2
        assert r.addresses[0].active is True


# ---------------------------------------------------------------------------
# Search models (§3)
# ---------------------------------------------------------------------------

class TestSearchProduct:
    def test_price_normalization(self):
        sp = SearchProduct(name="Burger", price=15000)
        assert sp.real_price == 15000  # normalized from price

    def test_product_id_string_to_int(self):
        sp = SearchProduct(name="Pizza", product_id="12345")
        assert sp.product_id == 12345

    def test_image_resolution(self):
        sp = SearchProduct(name="Test", image="abc.jpg")
        assert sp.image is not None
        assert "abc.jpg" in sp.image


class TestSearchStore:
    def test_basic(self):
        s = SearchStore(store_id=100, store_name="Burger Place")
        assert s.store_id == 100
        assert s.products == []

    def test_with_products(self):
        s = SearchStore(
            store_id=100,
            store_name="Burger Place",
            products=[{"name": "Burger", "price": 15000, "product_id": 1}],
        )
        assert len(s.products) == 1
        assert s.products[0].name == "Burger"


class TestSearchResponse:
    def test_empty(self):
        r = SearchResponse()
        assert r.stores == []


# ---------------------------------------------------------------------------
# Product model (§4 — compound ID extraction)
# ---------------------------------------------------------------------------

class TestProduct:
    def test_compound_id_extraction(self):
        """Menu endpoint returns IDs like '123_456' — should extract product ID."""
        p = Product(id="100_200", name="Test")
        assert p.id == 200

    def test_string_id_to_int(self):
        p = Product(id="999", name="Test")
        assert p.id == 999

    def test_int_id_passthrough(self):
        p = Product(id=42, name="Test")
        assert p.id == 42

    def test_is_available_maps_to_in_stock(self):
        p = Product(id=1, name="Test", is_available=False)
        assert p.in_stock is False

    def test_default_in_stock(self):
        p = Product(id=1, name="Test")
        assert p.in_stock is True


# ---------------------------------------------------------------------------
# Store models (§4, §5)
# ---------------------------------------------------------------------------

class TestStoreDetail:
    def test_is_restaurant_default(self):
        s = StoreDetail(store_id=1)
        assert s.is_restaurant is True
        assert s.effective_store_type == "restaurant"

    def test_is_turbo_store(self):
        s = StoreDetail(store_id=1, store_type_id="turbo")
        assert s.is_restaurant is False
        assert s.effective_store_type == "turbo"

    def test_fallback_to_type_field(self):
        s = StoreDetail(store_id=1, type="market")
        assert s.effective_store_type == "market"

    def test_store_type_id_takes_precedence(self):
        s = StoreDetail(store_id=1, store_type_id="turbo", type="restaurant")
        assert s.effective_store_type == "turbo"


class TestCatalogStore:
    def test_defaults(self):
        s = CatalogStore(store_id=1)
        assert s.is_available is True
        assert s.shipping_cost == 0


# ---------------------------------------------------------------------------
# Topping models (§6)
# ---------------------------------------------------------------------------

class TestToppingCategory:
    def test_required_toppings(self):
        cat = ToppingCategory(
            id=1, description="Sauces",
            min_toppings_for_categories=1,
            max_toppings_for_categories=3,
            toppings=[{"id": 10, "description": "Ketchup", "price": 0}],
        )
        assert cat.min_toppings_for_categories == 1
        assert len(cat.toppings) == 1
        assert cat.toppings[0].description == "Ketchup"

    def test_optional_toppings(self):
        cat = ToppingCategory(id=2, description="Extras")
        assert cat.min_toppings_for_categories == 0


class TestToppingsResponse:
    def test_empty(self):
        r = ToppingsResponse()
        assert r.categories == []


# ---------------------------------------------------------------------------
# Cart models (§7, §8, §9)
# ---------------------------------------------------------------------------

class TestCartProduct:
    def test_compound_id(self):
        cp = CartProduct(id="100_200", name="Burger", price=15000)
        assert cp.id == "100_200"  # stays as string

    def test_toppings(self):
        cp = CartProduct(
            id="1_2", name="Test",
            toppings=[{"id": 10, "description": "Extra cheese", "price": 3000}],
        )
        assert len(cp.toppings) == 1
        assert cp.toppings[0].price == 3000


class TestCart:
    def test_empty(self):
        c = Cart()
        assert c.stores == []
        assert c.product_total == 0

    def test_with_stores(self):
        c = Cart(
            id="cart-1",
            store_type="restaurant",
            stores=[{
                "id": 100, "name": "Test Store",
                "products": [{"id": "100_1", "name": "Burger", "price": 15000}],
                "total": 15000,
            }],
        )
        assert len(c.stores) == 1
        assert c.stores[0].products[0].name == "Burger"


# ---------------------------------------------------------------------------
# Checkout / Order models (§10)
# ---------------------------------------------------------------------------

class TestCheckoutDetail:
    def test_strips_html_from_return_key(self):
        cd = CheckoutDetail(return_key="<b>abc123</b>")
        assert cd.return_key == "abc123"

    def test_none_return_key(self):
        cd = CheckoutDetail()
        assert cd.return_key is None

    def test_plain_return_key(self):
        cd = CheckoutDetail(return_key="plain-key")
        assert cd.return_key == "plain-key"


class TestOrdersResponse:
    def test_empty(self):
        r = OrdersResponse()
        assert r.active_orders == []
        assert r.cancel_orders == []

    def test_with_orders(self):
        r = OrdersResponse(
            active_orders=[{"id": 1, "total": 50000, "state": "in_progress"}],
            cancel_orders=[{"id": 2, "total": 30000, "state": "cancelled"}],
        )
        assert len(r.active_orders) == 1
        assert r.cancel_orders[0].state == "cancelled"


# ---------------------------------------------------------------------------
# Intelligence models (§16, §17)
# ---------------------------------------------------------------------------

class TestTasteProfile:
    def test_defaults(self):
        tp = TasteProfile()
        assert tp.category_preferences == []
        assert tp.spending.total_spent == 0
        assert tp.taste_vector is None

    def test_with_data(self):
        tp = TasteProfile(
            category_preferences=[
                {"category_name": "Burgers", "order_count": 5, "percentage": 50.0},
            ],
            spending={"total_spent": 100000, "order_count": 5, "avg_per_order": 20000},
        )
        assert tp.category_preferences[0].percentage == 50.0
        assert tp.spending.avg_per_order == 20000


class TestRecommendation:
    def test_creation(self):
        r = Recommendation(
            type="usual", title="Your usual",
            description="Burger from McDonald's",
            store_id=100, confidence=0.8,
        )
        assert r.type == "usual"
        assert r.confidence == 0.8


class TestRecommendationSet:
    def test_empty(self):
        rs = RecommendationSet()
        assert rs.recommendations == []
        assert rs.profile_summary == ""
