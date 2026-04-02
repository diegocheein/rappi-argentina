"""Tests for rappi.memory.db — schema creation and migrations."""

import pytest
import aiosqlite

from rappi.memory.db import get_connection, migrate, SCHEMA_VERSION


class TestSchemaCreation:
    async def test_fresh_database(self):
        """A fresh in-memory database gets the full schema."""
        db = await aiosqlite.connect(":memory:")
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys=ON")
        await migrate(db)

        # Check all expected tables exist
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        rows = await cursor.fetchall()
        table_names = {row["name"] for row in rows}

        expected_tables = {
            "schema_version", "orders", "order_items",
            "product_cache", "store_cache", "preferences",
            "search_history", "embeddings",
        }
        assert expected_tables.issubset(table_names)
        await db.close()

    async def test_schema_version_recorded(self):
        db = await aiosqlite.connect(":memory:")
        db.row_factory = aiosqlite.Row
        await migrate(db)

        cursor = await db.execute("SELECT MAX(version) as v FROM schema_version")
        row = await cursor.fetchone()
        assert row["v"] == SCHEMA_VERSION
        await db.close()

    async def test_migration_idempotent(self):
        """Running migrate twice should not fail or duplicate data."""
        db = await aiosqlite.connect(":memory:")
        db.row_factory = aiosqlite.Row
        await migrate(db)
        await migrate(db)  # Second run — should be a no-op

        cursor = await db.execute("SELECT COUNT(*) as c FROM schema_version")
        row = await cursor.fetchone()
        assert row["c"] >= 1
        await db.close()

    async def test_foreign_keys_enabled(self, memory_db):
        cursor = await memory_db.execute("PRAGMA foreign_keys")
        row = await cursor.fetchone()
        assert row[0] == 1


class TestGetConnection:
    async def test_creates_parent_directory(self, tmp_path):
        db_path = tmp_path / "sub" / "dir" / "test.db"
        db = await get_connection(db_path)
        assert db_path.parent.exists()
        await db.close()
