"""Product cache repository with TTL support."""

from __future__ import annotations

import aiosqlite


class ProductCacheRepository:
    def __init__(self, db: aiosqlite.Connection):
        self._db = db

    async def upsert_many(self, store_id: int, products: list) -> None:
        """Bulk upsert products for a store. Accepts Product or SearchProduct models."""
        for p in products:
            pid = getattr(p, "product_id", None) or getattr(p, "id", 0)
            await self._db.execute(
                """INSERT OR REPLACE INTO product_cache
                   (store_id, product_id, name, description, price, real_price,
                    category_name, has_toppings, image_url, cached_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                (
                    store_id,
                    str(pid),
                    getattr(p, "name", ""),
                    getattr(p, "description", None) or getattr(p, "presentation", None),
                    getattr(p, "price", 0),
                    getattr(p, "real_price", 0) or getattr(p, "price", 0),
                    getattr(p, "category_name", None),
                    1 if getattr(p, "has_toppings", False) else 0,
                    getattr(p, "image", None),
                ),
            )
        await self._db.commit()

    async def get_by_store(self, store_id: int, ttl_hours: int = 24) -> list[dict] | None:
        """Get cached products for a store. Returns None if expired or missing."""
        cursor = await self._db.execute(
            """SELECT * FROM product_cache
               WHERE store_id = ?
                 AND cached_at > datetime('now', ? || ' hours')
               ORDER BY category_name, name""",
            (store_id, f"-{ttl_hours}"),
        )
        rows = await cursor.fetchall()
        if not rows:
            return None
        return [dict(row) for row in rows]

    async def search_by_name(self, query: str, limit: int = 20) -> list[dict]:
        """Search across all cached products by name (LIKE match)."""
        cursor = await self._db.execute(
            """SELECT pc.*, sc.name as store_name
               FROM product_cache pc
               LEFT JOIN store_cache sc ON pc.store_id = sc.store_id
               WHERE pc.name LIKE ?
               ORDER BY pc.price ASC
               LIMIT ?""",
            (f"%{query}%", limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def invalidate(self, store_id: int) -> None:
        await self._db.execute("DELETE FROM product_cache WHERE store_id = ?", (store_id,))
        await self._db.commit()

    async def invalidate_expired(self, ttl_hours: int = 24) -> None:
        await self._db.execute(
            "DELETE FROM product_cache WHERE cached_at < datetime('now', ? || ' hours')",
            (f"-{ttl_hours}",),
        )
        await self._db.commit()
