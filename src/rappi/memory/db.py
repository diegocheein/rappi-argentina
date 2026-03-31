"""Database connection, migrations, and schema management."""

from __future__ import annotations

from pathlib import Path

import aiosqlite

DB_PATH = Path.home() / ".rappi" / "rappi.db"
SCHEMA_VERSION = 1

SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    store_id INTEGER NOT NULL,
    store_name TEXT,
    store_type TEXT,
    total REAL NOT NULL DEFAULT 0,
    tip REAL NOT NULL DEFAULT 0,
    state TEXT,
    delivery_method TEXT,
    placed_at TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    raw_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_orders_store_id ON orders(store_id);
CREATE INDEX IF NOT EXISTS idx_orders_placed_at ON orders(placed_at DESC);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id TEXT NOT NULL,
    product_name TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price REAL NOT NULL DEFAULT 0,
    total_price REAL NOT NULL DEFAULT 0,
    toppings_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);

CREATE TABLE IF NOT EXISTS product_cache (
    store_id INTEGER NOT NULL,
    product_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL DEFAULT 0,
    real_price REAL NOT NULL DEFAULT 0,
    category_name TEXT,
    has_toppings INTEGER NOT NULL DEFAULT 0,
    image_url TEXT,
    cached_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (store_id, product_id)
);
CREATE INDEX IF NOT EXISTS idx_product_cache_name ON product_cache(name);

CREATE TABLE IF NOT EXISTS store_cache (
    store_id INTEGER PRIMARY KEY,
    name TEXT,
    store_type TEXT,
    logo_url TEXT,
    address TEXT,
    lat REAL,
    lng REAL,
    cached_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    selected_store_id INTEGER,
    selected_product_id INTEGER,
    result_count INTEGER NOT NULL DEFAULT 0,
    searched_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_search_history_searched_at ON search_history(searched_at DESC);

CREATE TABLE IF NOT EXISTS embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    text_content TEXT NOT NULL,
    vector BLOB NOT NULL,
    model TEXT NOT NULL DEFAULT 'text-embedding-3-small',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(entity_type, entity_id, model)
);
CREATE INDEX IF NOT EXISTS idx_embeddings_entity ON embeddings(entity_type, entity_id);
"""


async def get_connection(path: Path = DB_PATH) -> aiosqlite.Connection:
    """Open a database connection with recommended pragmas."""
    path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(path))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def migrate(db: aiosqlite.Connection) -> None:
    """Run pending migrations."""
    # Check if schema_version table exists
    cursor = await db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
    )
    exists = await cursor.fetchone()

    if not exists:
        # Fresh database — apply full schema
        await db.executescript(SCHEMA_V1)
        await db.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        await db.commit()
        return

    # Check current version
    cursor = await db.execute("SELECT MAX(version) FROM schema_version")
    row = await cursor.fetchone()
    current = row[0] if row else 0

    # Apply migrations incrementally (future versions go here)
    if current < SCHEMA_VERSION:
        await db.executescript(SCHEMA_V1)
        await db.execute(
            "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
            (SCHEMA_VERSION,),
        )
        await db.commit()
