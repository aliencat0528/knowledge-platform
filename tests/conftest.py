"""Shared pytest fixtures.

Each test gets an isolated on-disk SQLite database under pytest's tmp_path,
so tests never touch the real ./data/knowledge.db and can run in any order.
"""

import pytest_asyncio

from packages.server.services.import_service import ImportService
from packages.server.storage.database import Database


@pytest_asyncio.fixture
async def db(tmp_path):
    """Fresh database with schema applied, isolated per test."""
    database = Database(str(tmp_path / "test.db"))
    await database.connect()
    yield database
    await database.disconnect()


@pytest_asyncio.fixture
async def importer(db):
    """ImportService with auto-embed disabled.

    Embedding requires OPENAI_API_KEY and network access; deduplication logic
    is independent of it, so it stays off for these tests.
    """
    return ImportService(db, auto_embed=False)
