"""Store cache repository."""

from __future__ import annotations

import aiosqlite


class StoreCacheRepository:
    def __init__(self, db: aiosqlite.Connection):
        self._db = db

    async def upsert(
        self,
        store_id: int,
        name: str | None = None,
        store_type: str | None = None,
        logo_url: str | None = None,
        address: str | None = None,
        lat: float | None = None,
        lng: float | None = None,
    ) -> None:
        await self._db.execute(
            """INSERT OR REPLACE INTO store_cache
               (store_id, name, store_type, logo_url, address, lat, lng, cached_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (store_id, name, store_type, logo_url, address, lat, lng),
        )
        await self._db.commit()

    async def get(self, store_id: int, ttl_hours: int = 168) -> dict | None:
        """Get a cached store (default 7 day TTL)."""
        cursor = await self._db.execute(
            """SELECT * FROM store_cache
               WHERE store_id = ?
                 AND cached_at > datetime('now', ? || ' hours')""",
            (store_id, f"-{ttl_hours}"),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def search_by_name(self, query: str, limit: int = 10) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM store_cache WHERE name LIKE ? LIMIT ?",
            (f"%{query}%", limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
