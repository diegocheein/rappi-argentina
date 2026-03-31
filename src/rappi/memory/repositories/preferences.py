"""User preferences repository — key-value store with typed helpers."""

from __future__ import annotations

import json

import aiosqlite


class PreferencesRepository:
    def __init__(self, db: aiosqlite.Connection):
        self._db = db

    async def get(self, key: str, default=None):
        """Get a preference value (JSON-decoded)."""
        cursor = await self._db.execute(
            "SELECT value FROM preferences WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
        if not row:
            return default
        return json.loads(row["value"])

    async def set(self, key: str, value) -> None:
        """Set a preference value (JSON-encoded)."""
        await self._db.execute(
            """INSERT OR REPLACE INTO preferences (key, value, updated_at)
               VALUES (?, ?, datetime('now'))""",
            (key, json.dumps(value)),
        )
        await self._db.commit()

    async def delete(self, key: str) -> None:
        await self._db.execute("DELETE FROM preferences WHERE key = ?", (key,))
        await self._db.commit()

    async def get_all(self) -> dict:
        """Get all preferences as a dict."""
        cursor = await self._db.execute("SELECT key, value FROM preferences")
        rows = await cursor.fetchall()
        return {row["key"]: json.loads(row["value"]) for row in rows}

    # --- Typed convenience methods ---

    async def get_default_tip(self) -> int | None:
        return await self.get("default_tip")

    async def set_default_tip(self, amount: int) -> None:
        await self.set("default_tip", amount)

    async def get_dietary_restrictions(self) -> list[str]:
        return await self.get("dietary_restrictions", [])

    async def set_dietary_restrictions(self, restrictions: list[str]) -> None:
        await self.set("dietary_restrictions", restrictions)

    async def get_allergies(self) -> list[str]:
        return await self.get("allergies", [])

    async def set_allergies(self, allergies: list[str]) -> None:
        await self.set("allergies", allergies)

    async def get_favorite_store_ids(self) -> list[int]:
        return await self.get("favorite_store_ids", [])

    async def add_favorite_store(self, store_id: int) -> None:
        ids = await self.get_favorite_store_ids()
        if store_id not in ids:
            ids.append(store_id)
            await self.set("favorite_store_ids", ids)

    async def remove_favorite_store(self, store_id: int) -> None:
        ids = await self.get_favorite_store_ids()
        if store_id in ids:
            ids.remove(store_id)
            await self.set("favorite_store_ids", ids)

    async def get_favorite_products(self) -> list[dict]:
        """Returns list of {store_id, product_id} dicts."""
        return await self.get("favorite_products", [])

    async def add_favorite_product(self, store_id: int, product_id: int) -> None:
        products = await self.get_favorite_products()
        entry = {"store_id": store_id, "product_id": product_id}
        if entry not in products:
            products.append(entry)
            await self.set("favorite_products", products)

    async def remove_favorite_product(self, store_id: int, product_id: int) -> None:
        products = await self.get_favorite_products()
        entry = {"store_id": store_id, "product_id": product_id}
        if entry in products:
            products.remove(entry)
            await self.set("favorite_products", products)
