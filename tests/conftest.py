"""Shared fixtures for the Rappi CLI test suite."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rappi.config import ConfigManager, RappiConfig


# ---------------------------------------------------------------------------
# Config fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_config(tmp_path: Path) -> tuple[ConfigManager, Path]:
    """A ConfigManager backed by a temporary file."""
    config_file = tmp_path / "config.json"
    cm = ConfigManager(path=config_file)
    return cm, config_file


@pytest.fixture
def sample_config() -> RappiConfig:
    """A pre-populated RappiConfig for testing."""
    return RappiConfig(
        token="test-token-abc123",
        device_id="device-test-uuid",
        lat=4.624335,
        lng=-74.063644,
    )


# ---------------------------------------------------------------------------
# Mock HTTP client
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_http():
    """A mocked httpx.AsyncClient that returns configurable responses."""
    http = AsyncMock()
    return http


@pytest.fixture
def mock_client(sample_config: RappiConfig, tmp_config):
    """A RappiClient with mocked internals — no real HTTP."""
    from rappi.client import RappiClient

    cm, _ = tmp_config
    cm.save(sample_config)
    client = RappiClient(config=sample_config, config_manager=cm)
    # Pre-set an AsyncClient mock so no real connection is made
    client._http = AsyncMock()
    return client


# ---------------------------------------------------------------------------
# Memory / SQLite fixtures (in-memory)
# ---------------------------------------------------------------------------

@pytest.fixture
async def memory_db():
    """An in-memory SQLite connection with the full schema applied."""
    from rappi.memory.db import get_connection, migrate
    import aiosqlite

    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    await migrate(db)
    yield db
    await db.close()


@pytest.fixture
async def memory_manager(tmp_path: Path):
    """A MemoryManager backed by an in-memory SQLite database."""
    from rappi.memory.manager import MemoryManager

    db_path = tmp_path / "test_rappi.db"
    async with MemoryManager(db_path=db_path) as mm:
        yield mm
