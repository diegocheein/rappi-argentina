"""MemoryManager — single entry point for all persistence operations."""

from __future__ import annotations

from pathlib import Path

import aiosqlite

from rappi.memory.db import DB_PATH, get_connection, migrate
from rappi.memory.repositories.orders import OrderRepository
from rappi.memory.repositories.preferences import PreferencesRepository
from rappi.memory.repositories.products import ProductCacheRepository
from rappi.memory.repositories.search import SearchHistoryRepository
from rappi.memory.repositories.stores import StoreCacheRepository


class MemoryManager:
    """Facade for all memory/persistence operations.

    Usage:
        async with MemoryManager() as memory:
            await memory.orders.list_recent()
    """

    def __init__(self, db_path: Path = DB_PATH):
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None
        self.orders: OrderRepository
        self.products: ProductCacheRepository
        self.stores: StoreCacheRepository
        self.preferences: PreferencesRepository
        self.search: SearchHistoryRepository

    async def __aenter__(self) -> MemoryManager:
        self._db = await get_connection(self._db_path)
        await migrate(self._db)
        self.orders = OrderRepository(self._db)
        self.products = ProductCacheRepository(self._db)
        self.stores = StoreCacheRepository(self._db)
        self.preferences = PreferencesRepository(self._db)
        self.search = SearchHistoryRepository(self._db)
        return self

    async def __aexit__(self, *exc) -> None:
        if self._db:
            await self._db.close()

    # --- High-level convenience methods ---

    async def record_order_from_cart(
        self,
        order_id: int,
        cart_stores: list,
        tip: float = 0,
        placed_at: str | None = None,
    ) -> None:
        """Record an order from cart store data after successful placement."""
        from datetime import datetime, timezone

        placed_at = placed_at or datetime.now(timezone.utc).isoformat()

        for store in cart_stores:
            items = []
            for p in store.products:
                items.append({
                    "id": p.id,
                    "name": p.name,
                    "units": p.units,
                    "price": p.price,
                    "total": p.total,
                    "toppings": [
                        {"id": t.id, "description": t.description}
                        for t in (p.toppings or [])
                    ],
                })

            await self.orders.save(
                order_id=order_id,
                store_id=store.id,
                store_name=store.name,
                store_type=None,
                total=store.total,
                tip=tip,
                state="placed",
                placed_at=placed_at,
                items=items,
            )

            # Also cache the store
            try:
                await self.stores.upsert(store.id, store.name)
            except Exception:
                pass

    async def record_search_results(self, query: str, stores: list) -> int:
        """Record a search and cache the resulting stores/products."""
        record_id = await self.search.record(query, result_count=len(stores))

        for store in stores:
            store_id = getattr(store, "store_id", 0)
            store_name = getattr(store, "store_name", None) or getattr(store, "name", None)
            store_type = getattr(store, "store_type", None)

            try:
                await self.stores.upsert(store_id, store_name, store_type)
            except Exception:
                pass

            products = getattr(store, "products", [])
            if products:
                try:
                    await self.products.upsert_many(store_id, products)
                except Exception:
                    pass

        return record_id

    async def cache_store_menu(self, store_id: int, corridors: list) -> None:
        """Cache all products from a store's menu corridors."""
        for corridor in corridors:
            if corridor.products:
                try:
                    await self.products.upsert_many(store_id, corridor.products)
                except Exception:
                    pass

    async def smart_search(self, query: str, limit: int = 10) -> list[dict]:
        """Search across cached products using embeddings (if enabled) or SQL LIKE."""
        embeddings_enabled = await self.preferences.get("embeddings.enabled", False)

        if embeddings_enabled:
            try:
                from rappi.memory.embeddings import EmbeddingStore, OpenAIEmbeddingProvider
                provider = OpenAIEmbeddingProvider()
                store = EmbeddingStore(self._db, provider)
                return await store.search(query, entity_type="product", limit=limit)
            except Exception:
                pass  # Fall through to SQL search

        # Fallback: SQL LIKE search across cached products
        results = await self.products.search_by_name(query, limit=limit)
        return [
            {
                "entity_type": "product",
                "entity_id": f"{r['store_id']}:{r['product_id']}",
                "text": r["name"],
                "store_name": r.get("store_name"),
                "price": r["price"],
                "score": 1.0,  # exact match
            }
            for r in results
        ]

    async def generate_embeddings_for_cached_products(self) -> int:
        """Generate embeddings for all cached products that don't have them yet.
        Returns number of products embedded. Only works if embeddings are enabled."""
        embeddings_enabled = await self.preferences.get("embeddings.enabled", False)
        if not embeddings_enabled:
            return 0

        try:
            from rappi.memory.embeddings import EmbeddingStore, OpenAIEmbeddingProvider
            provider = OpenAIEmbeddingProvider()
            store = EmbeddingStore(self._db, provider)

            # Find products without embeddings
            cursor = await self._db.execute(
                """SELECT pc.store_id, pc.product_id, pc.name, pc.description, pc.category_name
                   FROM product_cache pc
                   LEFT JOIN embeddings e
                     ON e.entity_type = 'product'
                     AND e.entity_id = (pc.store_id || ':' || pc.product_id)
                   WHERE e.id IS NULL
                   LIMIT 100"""
            )
            rows = await cursor.fetchall()
            if not rows:
                return 0

            items = []
            for row in rows:
                entity_id = f"{row['store_id']}:{row['product_id']}"
                text = row["name"]
                if row["description"]:
                    text += f" - {row['description']}"
                if row["category_name"]:
                    text += f" ({row['category_name']})"
                items.append((entity_id, text))

            await store.store_embeddings("product", items)
            return len(items)
        except Exception:
            return 0

    async def get_memory_summary(self) -> dict:
        """Get a quick summary of what's in memory — useful for MCP context."""
        order_count = await self.orders.count()
        last_order = await self.orders.get_last_order()
        fav_stores = await self.preferences.get_favorite_store_ids()
        default_tip = await self.preferences.get_default_tip()

        embeddings_enabled = await self.preferences.get("embeddings.enabled", False)

        return {
            "order_count": order_count,
            "last_order": {
                "store": last_order.store_name,
                "total": last_order.total,
                "date": last_order.placed_at,
            } if last_order else None,
            "favorite_store_count": len(fav_stores),
            "default_tip": default_tip,
            "has_preferences": default_tip is not None,
            "embeddings_enabled": embeddings_enabled,
        }
