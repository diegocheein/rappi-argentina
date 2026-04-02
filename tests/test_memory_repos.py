"""Tests for all memory repositories — orders, preferences, products, search, stores."""

import pytest

from rappi.memory.repositories.orders import OrderRepository
from rappi.memory.repositories.preferences import PreferencesRepository
from rappi.memory.repositories.products import ProductCacheRepository
from rappi.memory.repositories.search import SearchHistoryRepository
from rappi.memory.repositories.stores import StoreCacheRepository


# ---------------------------------------------------------------------------
# OrderRepository (§12 — order history)
# ---------------------------------------------------------------------------

class TestOrderRepository:
    async def test_save_and_get(self, memory_db):
        repo = OrderRepository(memory_db)
        await repo.save(
            order_id=1001, store_id=100, store_name="Burger Place",
            store_type="restaurant", total=45000, tip=3000, state="placed",
            placed_at="2025-01-15T12:00:00Z",
            items=[
                {"id": "100_1", "name": "Burger", "units": 2, "price": 15000, "total": 30000},
                {"id": "100_2", "name": "Fries", "units": 1, "price": 8000, "total": 8000},
            ],
        )
        order = await repo.get_by_id(1001)
        assert order is not None
        assert order.store_name == "Burger Place"
        assert order.total == 45000
        assert order.tip == 3000
        assert len(order.items) == 2
        assert order.items[0]["name"] == "Burger"

    async def test_list_recent(self, memory_db):
        repo = OrderRepository(memory_db)
        for i in range(5):
            await repo.save(
                order_id=i, store_id=100, store_name="Store",
                store_type="restaurant", total=10000 * (i + 1), tip=0,
                state="placed", placed_at=f"2025-01-{15+i:02d}T12:00:00Z",
            )
        recent = await repo.list_recent(limit=3)
        assert len(recent) == 3
        # Most recent first
        assert recent[0].placed_at > recent[1].placed_at

    async def test_count(self, memory_db):
        repo = OrderRepository(memory_db)
        assert await repo.count() == 0
        await repo.save(order_id=1, store_id=1, store_name="S",
                        store_type="r", total=0, tip=0, state="p", placed_at="2025-01-01")
        assert await repo.count() == 1

    async def test_get_last_order(self, memory_db):
        repo = OrderRepository(memory_db)
        assert await repo.get_last_order() is None

        await repo.save(order_id=1, store_id=1, store_name="First",
                        store_type="r", total=10000, tip=0, state="p", placed_at="2025-01-01")
        await repo.save(order_id=2, store_id=2, store_name="Second",
                        store_type="r", total=20000, tip=0, state="p", placed_at="2025-01-02")

        last = await repo.get_last_order()
        assert last.store_name == "Second"

    async def test_get_frequent_stores(self, memory_db):
        repo = OrderRepository(memory_db)
        for i in range(3):
            await repo.save(order_id=i, store_id=100, store_name="Frequent",
                            store_type="r", total=10000, tip=0, state="p",
                            placed_at=f"2025-01-{i+1:02d}")
        await repo.save(order_id=10, store_id=200, store_name="Once",
                        store_type="r", total=5000, tip=0, state="p", placed_at="2025-01-10")

        frequent = await repo.get_frequent_stores()
        assert frequent[0]["store_name"] == "Frequent"
        assert frequent[0]["order_count"] == 3

    async def test_get_most_ordered_products(self, memory_db):
        repo = OrderRepository(memory_db)
        await repo.save(
            order_id=1, store_id=1, store_name="S", store_type="r",
            total=30000, tip=0, state="p", placed_at="2025-01-01",
            items=[{"id": "p1", "name": "Burger", "units": 3, "price": 10000, "total": 30000}],
        )
        await repo.save(
            order_id=2, store_id=1, store_name="S", store_type="r",
            total=10000, tip=0, state="p", placed_at="2025-01-02",
            items=[{"id": "p1", "name": "Burger", "units": 1, "price": 10000, "total": 10000}],
        )
        products = await repo.get_most_ordered_products()
        assert products[0]["name"] == "Burger"
        assert products[0]["total_quantity"] == 4

    async def test_list_by_store(self, memory_db):
        repo = OrderRepository(memory_db)
        await repo.save(order_id=1, store_id=100, store_name="A",
                        store_type="r", total=10000, tip=0, state="p", placed_at="2025-01-01")
        await repo.save(order_id=2, store_id=200, store_name="B",
                        store_type="r", total=20000, tip=0, state="p", placed_at="2025-01-02")

        store_orders = await repo.list_by_store(100)
        assert len(store_orders) == 1
        assert store_orders[0].store_name == "A"


# ---------------------------------------------------------------------------
# PreferencesRepository (§14 — preferences)
# ---------------------------------------------------------------------------

class TestPreferencesRepository:
    async def test_set_and_get(self, memory_db):
        repo = PreferencesRepository(memory_db)
        await repo.set("test_key", "test_value")
        assert await repo.get("test_key") == "test_value"

    async def test_get_missing_key_returns_default(self, memory_db):
        repo = PreferencesRepository(memory_db)
        assert await repo.get("missing", "fallback") == "fallback"

    async def test_get_missing_key_no_default(self, memory_db):
        repo = PreferencesRepository(memory_db)
        assert await repo.get("missing") is None

    async def test_delete(self, memory_db):
        repo = PreferencesRepository(memory_db)
        await repo.set("to_delete", True)
        assert await repo.get("to_delete") is True
        await repo.delete("to_delete")
        assert await repo.get("to_delete") is None

    async def test_get_all(self, memory_db):
        repo = PreferencesRepository(memory_db)
        await repo.set("a", 1)
        await repo.set("b", 2)
        all_prefs = await repo.get_all()
        assert all_prefs == {"a": 1, "b": 2}

    async def test_default_tip(self, memory_db):
        repo = PreferencesRepository(memory_db)
        assert await repo.get_default_tip() is None
        await repo.set_default_tip(5000)
        assert await repo.get_default_tip() == 5000

    async def test_dietary_restrictions(self, memory_db):
        repo = PreferencesRepository(memory_db)
        assert await repo.get_dietary_restrictions() == []
        await repo.set_dietary_restrictions(["vegetarian", "no-gluten"])
        assert await repo.get_dietary_restrictions() == ["vegetarian", "no-gluten"]

    async def test_allergies(self, memory_db):
        repo = PreferencesRepository(memory_db)
        await repo.set_allergies(["peanuts", "shellfish"])
        assert await repo.get_allergies() == ["peanuts", "shellfish"]

    async def test_favorite_stores(self, memory_db):
        repo = PreferencesRepository(memory_db)
        assert await repo.get_favorite_store_ids() == []

        await repo.add_favorite_store(100)
        await repo.add_favorite_store(200)
        assert await repo.get_favorite_store_ids() == [100, 200]

        # Idempotent — adding again doesn't duplicate
        await repo.add_favorite_store(100)
        assert await repo.get_favorite_store_ids() == [100, 200]

        await repo.remove_favorite_store(100)
        assert await repo.get_favorite_store_ids() == [200]

    async def test_favorite_products(self, memory_db):
        repo = PreferencesRepository(memory_db)
        await repo.add_favorite_product(100, 1)
        await repo.add_favorite_product(100, 2)
        products = await repo.get_favorite_products()
        assert len(products) == 2

        await repo.remove_favorite_product(100, 1)
        assert len(await repo.get_favorite_products()) == 1

    async def test_overwrite(self, memory_db):
        repo = PreferencesRepository(memory_db)
        await repo.set("k", "v1")
        await repo.set("k", "v2")
        assert await repo.get("k") == "v2"


# ---------------------------------------------------------------------------
# ProductCacheRepository (§3 — search result caching)
# ---------------------------------------------------------------------------

class TestProductCacheRepository:
    async def test_upsert_and_get(self, memory_db):
        repo = ProductCacheRepository(memory_db)

        class FakeProduct:
            product_id = 1
            name = "Burger"
            description = "Delicious"
            price = 15000
            real_price = 15000
            category_name = "Burgers"
            has_toppings = True
            image = "burger.jpg"
            presentation = None

        await repo.upsert_many(100, [FakeProduct()])
        products = await repo.get_by_store(100)
        assert products is not None
        assert len(products) == 1
        assert products[0]["name"] == "Burger"

    async def test_search_by_name(self, memory_db):
        repo = ProductCacheRepository(memory_db)

        class P:
            def __init__(self, pid, name, price):
                self.product_id = pid
                self.name = name
                self.price = price
                self.real_price = price
                self.description = None
                self.category_name = None
                self.has_toppings = False
                self.image = None
                self.presentation = None

        await repo.upsert_many(1, [P(1, "Coca Cola", 3000), P(2, "Pepsi", 2800)])
        await repo.upsert_many(2, [P(3, "Coca Cola Zero", 3200)])

        results = await repo.search_by_name("Coca")
        assert len(results) == 2

    async def test_invalidate(self, memory_db):
        repo = ProductCacheRepository(memory_db)

        class P:
            product_id = 1
            name = "Test"
            price = 1000
            real_price = 1000
            description = None
            category_name = None
            has_toppings = False
            image = None
            presentation = None

        await repo.upsert_many(100, [P()])
        assert await repo.get_by_store(100) is not None

        await repo.invalidate(100)
        assert await repo.get_by_store(100) is None


# ---------------------------------------------------------------------------
# SearchHistoryRepository (§3 — search history)
# ---------------------------------------------------------------------------

class TestSearchHistoryRepository:
    async def test_record_and_list(self, memory_db):
        repo = SearchHistoryRepository(memory_db)
        record_id = await repo.record("hamburguesa", result_count=5)
        assert record_id > 0

        recent = await repo.list_recent()
        assert len(recent) == 1
        assert recent[0]["query"] == "hamburguesa"
        assert recent[0]["result_count"] == 5

    async def test_suggestions(self, memory_db):
        repo = SearchHistoryRepository(memory_db)
        await repo.record("hamburguesa")
        await repo.record("hamburguesa doble")
        await repo.record("pizza")

        suggestions = await repo.get_suggestions("ham")
        assert len(suggestions) == 2
        assert all("ham" in s for s in suggestions)

    async def test_popular_queries(self, memory_db):
        repo = SearchHistoryRepository(memory_db)
        await repo.record("pizza")
        await repo.record("pizza")
        await repo.record("pizza")
        await repo.record("burger")

        popular = await repo.get_popular_queries()
        assert popular[0]["query"] == "pizza"
        assert popular[0]["count"] == 3

    async def test_update_selection(self, memory_db):
        repo = SearchHistoryRepository(memory_db)
        record_id = await repo.record("test")
        await repo.update_selection(record_id, store_id=100, product_id=200)

        recent = await repo.list_recent()
        assert recent[0]["selected_store_id"] == 100
        assert recent[0]["selected_product_id"] == 200


# ---------------------------------------------------------------------------
# StoreCacheRepository
# ---------------------------------------------------------------------------

class TestStoreCacheRepository:
    async def test_upsert_and_get(self, memory_db):
        repo = StoreCacheRepository(memory_db)
        await repo.upsert(100, "Burger Place", "restaurant")

        store = await repo.get(100)
        assert store is not None
        assert store["name"] == "Burger Place"
        assert store["store_type"] == "restaurant"

    async def test_search_by_name(self, memory_db):
        repo = StoreCacheRepository(memory_db)
        await repo.upsert(1, "McDonald's")
        await repo.upsert(2, "Burger King")
        await repo.upsert(3, "Pizza Hut")

        results = await repo.search_by_name("Burger")
        assert len(results) == 1
        assert results[0]["name"] == "Burger King"

    async def test_get_missing(self, memory_db):
        repo = StoreCacheRepository(memory_db)
        assert await repo.get(999) is None
