"""Order history repository."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import aiosqlite


@dataclass
class OrderRecord:
    id: int
    store_id: int
    store_name: str | None
    store_type: str | None
    total: float
    tip: float
    state: str | None
    placed_at: str
    items: list[dict] | None = None


class OrderRepository:
    def __init__(self, db: aiosqlite.Connection):
        self._db = db

    async def save(
        self,
        order_id: int,
        store_id: int,
        store_name: str | None,
        store_type: str | None,
        total: float,
        tip: float,
        state: str | None,
        placed_at: str,
        items: list[dict] | None = None,
        raw_json: str | None = None,
    ) -> None:
        """Save or update an order and its line items."""
        await self._db.execute(
            """INSERT OR REPLACE INTO orders
               (id, store_id, store_name, store_type, total, tip, state, placed_at, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (order_id, store_id, store_name, store_type, total, tip, state, placed_at, raw_json),
        )
        if items:
            # Clear old items and re-insert
            await self._db.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
            for item in items:
                await self._db.execute(
                    """INSERT INTO order_items
                       (order_id, product_id, product_name, quantity, unit_price, total_price, toppings_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        order_id,
                        str(item.get("product_id", item.get("id", ""))),
                        item.get("name", ""),
                        item.get("units", item.get("quantity", 1)),
                        item.get("price", 0),
                        item.get("total", item.get("price", 0)),
                        json.dumps(item.get("toppings", [])) if item.get("toppings") else None,
                    ),
                )
        await self._db.commit()

    async def get_by_id(self, order_id: int) -> OrderRecord | None:
        """Get a single order with its items."""
        cursor = await self._db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = await cursor.fetchone()
        if not row:
            return None
        record = OrderRecord(
            id=row["id"],
            store_id=row["store_id"],
            store_name=row["store_name"],
            store_type=row["store_type"],
            total=row["total"],
            tip=row["tip"],
            state=row["state"],
            placed_at=row["placed_at"],
        )
        record.items = await self._get_items(order_id)
        return record

    async def _get_items(self, order_id: int) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (order_id,)
        )
        rows = await cursor.fetchall()
        return [
            {
                "product_id": row["product_id"],
                "name": row["product_name"],
                "quantity": row["quantity"],
                "unit_price": row["unit_price"],
                "total_price": row["total_price"],
                "toppings": json.loads(row["toppings_json"]) if row["toppings_json"] else [],
            }
            for row in rows
        ]

    async def list_recent(self, limit: int = 20, offset: int = 0) -> list[OrderRecord]:
        """Get recent orders, newest first."""
        cursor = await self._db.execute(
            "SELECT * FROM orders ORDER BY placed_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            record = OrderRecord(
                id=row["id"],
                store_id=row["store_id"],
                store_name=row["store_name"],
                store_type=row["store_type"],
                total=row["total"],
                tip=row["tip"],
                state=row["state"],
                placed_at=row["placed_at"],
            )
            record.items = await self._get_items(row["id"])
            results.append(record)
        return results

    async def list_by_store(self, store_id: int, limit: int = 10) -> list[OrderRecord]:
        """Get orders from a specific store."""
        cursor = await self._db.execute(
            "SELECT * FROM orders WHERE store_id = ? ORDER BY placed_at DESC LIMIT ?",
            (store_id, limit),
        )
        rows = await cursor.fetchall()
        return [
            OrderRecord(
                id=row["id"],
                store_id=row["store_id"],
                store_name=row["store_name"],
                store_type=row["store_type"],
                total=row["total"],
                tip=row["tip"],
                state=row["state"],
                placed_at=row["placed_at"],
            )
            for row in rows
        ]

    async def get_frequent_stores(self, limit: int = 10) -> list[dict]:
        """Get stores ordered from most often."""
        cursor = await self._db.execute(
            """SELECT store_id, store_name, store_type, COUNT(*) as order_count,
                      MAX(placed_at) as last_ordered
               FROM orders
               GROUP BY store_id
               ORDER BY order_count DESC
               LIMIT ?""",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "store_id": row["store_id"],
                "store_name": row["store_name"],
                "store_type": row["store_type"],
                "order_count": row["order_count"],
                "last_ordered": row["last_ordered"],
            }
            for row in rows
        ]

    async def get_most_ordered_products(self, limit: int = 10) -> list[dict]:
        """Get products ordered most frequently across all orders."""
        cursor = await self._db.execute(
            """SELECT product_id, product_name, SUM(quantity) as total_qty,
                      COUNT(DISTINCT order_id) as order_count
               FROM order_items
               GROUP BY product_id
               ORDER BY total_qty DESC
               LIMIT ?""",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "product_id": row["product_id"],
                "name": row["product_name"],
                "total_quantity": row["total_qty"],
                "order_count": row["order_count"],
            }
            for row in rows
        ]

    async def count(self) -> int:
        cursor = await self._db.execute("SELECT COUNT(*) FROM orders")
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def get_last_order(self) -> OrderRecord | None:
        """Get the most recent order."""
        results = await self.list_recent(limit=1)
        return results[0] if results else None
