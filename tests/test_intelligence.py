"""Tests for rappi.memory.intelligence — taste profile and recommendations."""

import pytest

from rappi.memory.intelligence import IntelligenceEngine
from rappi.memory.repositories.orders import OrderRepository
from rappi.memory.repositories.preferences import PreferencesRepository
from rappi.memory.repositories.products import ProductCacheRepository
from rappi.memory.repositories.stores import StoreCacheRepository


async def _seed_orders(db, count: int = 5):
    """Seed the database with test order data for intelligence testing."""
    repo = OrderRepository(db)
    store_repo = StoreCacheRepository(db)

    # Seed store cache
    await store_repo.upsert(100, "Burger Joint", "restaurant")
    await store_repo.upsert(200, "Pizza Palace", "restaurant")
    await store_repo.upsert(300, "Turbo Market", "turbo")

    # Seed product cache
    prod_repo = ProductCacheRepository(db)

    class P:
        def __init__(self, pid, name, price, category):
            self.product_id = pid
            self.name = name
            self.price = price
            self.real_price = price
            self.description = None
            self.category_name = category
            self.has_toppings = False
            self.image = None
            self.presentation = None

    await prod_repo.upsert_many(100, [
        P(1, "Classic Burger", 18000, "Burgers"),
        P(2, "Cheese Fries", 12000, "Sides"),
    ])
    await prod_repo.upsert_many(200, [
        P(10, "Margherita", 25000, "Pizzas"),
    ])

    # Seed orders
    for i in range(count):
        store_id = 100 if i < 3 else 200
        store_name = "Burger Joint" if i < 3 else "Pizza Palace"
        items = [
            {"id": "1", "name": "Classic Burger", "units": 1, "price": 18000, "total": 18000},
        ] if i < 3 else [
            {"id": "10", "name": "Margherita", "units": 1, "price": 25000, "total": 25000},
        ]
        total = 18000 if i < 3 else 25000
        # Spread across different hours and days
        hour = 12 + (i % 4)
        day = i + 1
        placed_at = f"2025-01-{day:02d}T{hour:02d}:30:00Z"

        await repo.save(
            order_id=i + 1, store_id=store_id, store_name=store_name,
            store_type="restaurant", total=total, tip=2000,
            state="delivered", placed_at=placed_at, items=items,
        )


class TestComputeTasteProfile:
    async def test_empty_history(self, memory_db):
        engine = IntelligenceEngine(memory_db)
        profile = await engine.compute_taste_profile()
        assert profile.spending.order_count == 0
        assert profile.category_preferences == []

    async def test_with_order_data(self, memory_db):
        await _seed_orders(memory_db, count=5)
        engine = IntelligenceEngine(memory_db)
        profile = await engine.compute_taste_profile()

        # Should have spending data
        assert profile.spending.order_count == 5
        assert profile.spending.total_spent > 0
        assert profile.spending.avg_per_order > 0

        # Should have top stores
        assert len(profile.top_stores) > 0
        # Burger Joint has 3 orders, should be first
        assert profile.top_stores[0].store_name == "Burger Joint"
        assert profile.top_stores[0].order_count == 3

        # Should have top products
        assert len(profile.top_products) > 0

    async def test_dietary_restrictions_included(self, memory_db):
        await _seed_orders(memory_db, count=3)
        engine = IntelligenceEngine(memory_db)
        profile = await engine.compute_taste_profile(
            dietary_restrictions=["vegetarian"],
            allergies=["peanuts"],
        )
        assert "vegetarian" in profile.dietary_restrictions
        assert "peanuts" in profile.allergies


class TestGetRecommendations:
    async def test_empty_history(self, memory_db):
        engine = IntelligenceEngine(memory_db)
        result = await engine.get_recommendations()
        assert result.recommendations == []

    async def test_usual_recommendation(self, memory_db):
        """A store ordered from 3+ times should produce a 'usual' recommendation."""
        await _seed_orders(memory_db, count=5)
        engine = IntelligenceEngine(memory_db)
        result = await engine.get_recommendations()

        usual_recs = [r for r in result.recommendations if r.type == "usual"]
        # Burger Joint has 3 orders → should appear as "the usual"
        assert len(usual_recs) > 0
        assert any("Burger" in r.title for r in usual_recs)

    async def test_profile_summary(self, memory_db):
        await _seed_orders(memory_db, count=5)
        engine = IntelligenceEngine(memory_db)
        result = await engine.get_recommendations()
        assert result.profile_summary != ""


class TestGetTasteSummary:
    async def test_empty(self, memory_db):
        engine = IntelligenceEngine(memory_db)
        summary = await engine.get_taste_summary()
        # Should return something even with no data
        assert isinstance(summary, str)

    async def test_with_data(self, memory_db):
        await _seed_orders(memory_db, count=5)
        engine = IntelligenceEngine(memory_db)
        summary = await engine.get_taste_summary()
        assert len(summary) > 0
