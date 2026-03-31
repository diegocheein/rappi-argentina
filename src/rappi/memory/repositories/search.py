"""Search history repository."""

from __future__ import annotations

import aiosqlite


class SearchHistoryRepository:
    def __init__(self, db: aiosqlite.Connection):
        self._db = db

    async def record(
        self,
        query: str,
        result_count: int = 0,
        selected_store_id: int | None = None,
        selected_product_id: int | None = None,
    ) -> int:
        """Record a search query. Returns the record ID."""
        cursor = await self._db.execute(
            """INSERT INTO search_history (query, result_count, selected_store_id, selected_product_id)
               VALUES (?, ?, ?, ?)""",
            (query, result_count, selected_store_id, selected_product_id),
        )
        await self._db.commit()
        return cursor.lastrowid or 0

    async def update_selection(self, record_id: int, store_id: int | None = None, product_id: int | None = None) -> None:
        """Update a search record with the user's selection."""
        if store_id is not None:
            await self._db.execute(
                "UPDATE search_history SET selected_store_id = ? WHERE id = ?",
                (store_id, record_id),
            )
        if product_id is not None:
            await self._db.execute(
                "UPDATE search_history SET selected_product_id = ? WHERE id = ?",
                (product_id, record_id),
            )
        await self._db.commit()

    async def list_recent(self, limit: int = 20) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM search_history ORDER BY searched_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_suggestions(self, prefix: str, limit: int = 5) -> list[str]:
        """Autocomplete from past queries."""
        cursor = await self._db.execute(
            """SELECT DISTINCT query FROM search_history
               WHERE query LIKE ?
               ORDER BY searched_at DESC
               LIMIT ?""",
            (f"{prefix}%", limit),
        )
        rows = await cursor.fetchall()
        return [row["query"] for row in rows]

    async def get_popular_queries(self, limit: int = 10) -> list[dict]:
        cursor = await self._db.execute(
            """SELECT query, COUNT(*) as count, MAX(searched_at) as last_used
               FROM search_history
               GROUP BY query
               ORDER BY count DESC
               LIMIT ?""",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
