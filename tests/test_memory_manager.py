"""Tests for rappi.memory.manager — MemoryManager facade methods."""

import pytest

from rappi.memory.manager import MemoryManager
from rappi.models.store import SearchStore, SearchProduct, Corridor, Product


class TestMemoryManagerLifecycle:
    async def test_context_manager(self, tmp_path):
        db_path = tmp_path / "test.db"
        async with MemoryManager(db_path=db_path) as mm:
            assert mm.orders is not None
            assert mm.products is not None
            assert mm.stores is not None
            assert mm.preferences is not None
            assert mm.search is not None
            assert mm.intelligence is not None


class TestRecordSearchResults:
    async def test_caches_stores_and_products(self, memory_manager):
        stores = [
            SearchStore(
                store_id=100, store_name="Burger Place", store_type="restaurant",
                products=[
                    SearchProduct(name="Burger", price=15000, product_id=1),
                    SearchProduct(name="Fries", price=8000, product_id=2),
                ],
            ),
        ]
        record_id = await memory_manager.record_search_results("burger", stores)
        assert record_id > 0

        # Store should be cached
        cached_store = await memory_manager.stores.get(100)
        assert cached_store is not None
        assert cached_store["name"] == "Burger Place"

        # Products should be cached
        cached_products = await memory_manager.products.get_by_store(100)
        assert cached_products is not None
        assert len(cached_products) == 2

    async def test_search_recorded_in_history(self, memory_manager):
        stores = [SearchStore(store_id=1, store_name="Test", products=[])]
        await memory_manager.record_search_results("pizza", stores)

        recent = await memory_manager.search.list_recent(1)
        assert len(recent) == 1
        assert recent[0]["query"] == "pizza"


class TestCacheStoreMenu:
    async def test_caches_corridor_products(self, memory_manager):
        corridors = [
            Corridor(
                id=1, name="Main",
                products=[
                    Product(id=10, name="Hamburger", price=18000, real_price=18000),
                    Product(id=11, name="Cheeseburger", price=20000, real_price=20000),
                ],
            ),
            Corridor(
                id=2, name="Drinks",
                products=[
                    Product(id=20, name="Cola", price=3000, real_price=3000),
                ],
            ),
        ]
        await memory_manager.cache_store_menu(100, corridors)

        cached = await memory_manager.products.get_by_store(100)
        assert cached is not None
        assert len(cached) == 3


class TestGetMemorySummary:
    async def test_empty_database(self, memory_manager):
        summary = await memory_manager.get_memory_summary()
        assert summary["order_count"] == 0
        assert summary["last_order"] is None
        assert summary["favorite_store_count"] == 0
        assert summary["default_tip"] is None
        assert summary["embeddings_enabled"] is False

    async def test_with_data(self, memory_manager):
        await memory_manager.orders.save(
            order_id=1, store_id=100, store_name="Test",
            store_type="r", total=30000, tip=3000,
            state="placed", placed_at="2025-01-15",
        )
        await memory_manager.preferences.set_default_tip(5000)
        await memory_manager.preferences.add_favorite_store(100)

        summary = await memory_manager.get_memory_summary()
        assert summary["order_count"] == 1
        assert summary["last_order"]["store"] == "Test"
        assert summary["default_tip"] == 5000
        assert summary["favorite_store_count"] == 1


class TestSmartSearch:
    async def test_sql_fallback(self, memory_manager):
        """Without embeddings, smart_search uses SQL LIKE."""
        # Populate product cache
        class FakeProduct:
            product_id = 1
            name = "Coca Cola"
            price = 3000
            real_price = 3000
            description = None
            category_name = "Drinks"
            has_toppings = False
            image = None
            presentation = None

        await memory_manager.products.upsert_many(100, [FakeProduct()])

        # Also cache the store so store_name shows up
        await memory_manager.stores.upsert(100, "Test Store")

        results = await memory_manager.smart_search("Coca")
        assert len(results) >= 1
        assert results[0]["text"] == "Coca Cola"
        assert results[0]["entity_type"] == "product"


class TestRecordOrderFromCart:
    async def test_records_full_order(self, memory_manager):
        from rappi.models.cart import CartStore, CartProduct

        cart_stores = [
            CartStore(
                id=100, name="Burger Place",
                products=[
                    CartProduct(id="100_1", name="Burger", units=2, price=15000, total=30000),
                ],
                total=30000,
            ),
        ]

        await memory_manager.record_order_from_cart(
            order_id=5001,
            cart_stores=cart_stores,
            tip=3000,
        )

        order = await memory_manager.orders.get_by_id(5001)
        assert order is not None
        assert order.store_id == 100
        assert order.total == 30000
        assert order.tip == 3000
        assert len(order.items) == 1
