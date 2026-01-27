"""SQLite database operations using aiosqlite."""

import aiosqlite
from pathlib import Path
from typing import Any

from ..config import settings


# SQL schema for all tables
SCHEMA = """
-- Articles table: main content storage
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,  -- notion | medium | docs | web
    source_id TEXT NOT NULL,    -- unique identifier from source
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL, -- MD5 hash for deduplication
    url TEXT,
    author TEXT,
    published_at DATETIME,
    tags TEXT,                  -- JSON array
    notion_page_id TEXT,
    notion_synced_at DATETIME,
    is_embedded BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1,
    UNIQUE(source_type, source_id)
);

-- Article history table: version tracking
CREATE TABLE IF NOT EXISTS article_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    old_content TEXT,
    new_content TEXT,
    old_content_hash TEXT,
    new_content_hash TEXT,
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
);

-- Article hierarchy table: parent-child relationships
CREATE TABLE IF NOT EXISTS article_hierarchy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER NOT NULL,
    child_id INTEGER NOT NULL,
    FOREIGN KEY (parent_id) REFERENCES articles(id) ON DELETE CASCADE,
    FOREIGN KEY (child_id) REFERENCES articles(id) ON DELETE CASCADE,
    UNIQUE(parent_id, child_id)
);

-- Import batches table: batch import tracking
CREATE TABLE IF NOT EXISTS import_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,       -- extension | cli | scheduler | web
    file_name TEXT,
    new_count INTEGER DEFAULT 0,
    updated_count INTEGER DEFAULT 0,
    skipped_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Scheduled tasks table: for scheduled crawling
CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url_pattern TEXT NOT NULL,
    cron_expression TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_run_at DATETIME,
    next_run_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Conversations table: chat history management
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,           -- UUID
    title TEXT,                    -- Auto-generated from first message
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Messages table: individual chat messages
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,            -- user | assistant
    content TEXT NOT NULL,
    sources TEXT,                  -- JSON array of source references
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_articles_content_hash ON articles(content_hash);
CREATE INDEX IF NOT EXISTS idx_articles_created_at ON articles(created_at);
CREATE INDEX IF NOT EXISTS idx_articles_is_embedded ON articles(is_embedded);
CREATE INDEX IF NOT EXISTS idx_article_history_article_id ON article_history(article_id);
CREATE INDEX IF NOT EXISTS idx_article_hierarchy_parent ON article_hierarchy(parent_id);
CREATE INDEX IF NOT EXISTS idx_article_hierarchy_child ON article_hierarchy(child_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
"""


class Database:
    """Async SQLite database wrapper."""

    def __init__(self, db_path: str | None = None):
        """Initialize database with path."""
        self.db_path = db_path or settings.database_path
        self._connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Connect to database and ensure schema exists."""
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row

        # Enable foreign keys
        await self._connection.execute("PRAGMA foreign_keys = ON")

        # Create schema
        await self._connection.executescript(SCHEMA)
        await self._connection.commit()

    async def disconnect(self) -> None:
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None

    @property
    def connection(self) -> aiosqlite.Connection:
        """Get active connection."""
        if not self._connection:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._connection

    async def execute(
        self, query: str, params: tuple | dict | None = None
    ) -> aiosqlite.Cursor:
        """Execute a query."""
        if params:
            return await self.connection.execute(query, params)
        return await self.connection.execute(query)

    async def executemany(
        self, query: str, params_list: list[tuple | dict]
    ) -> aiosqlite.Cursor:
        """Execute a query with multiple parameter sets."""
        return await self.connection.executemany(query, params_list)

    async def fetchone(
        self, query: str, params: tuple | dict | None = None
    ) -> dict[str, Any] | None:
        """Fetch one row as dictionary."""
        cursor = await self.execute(query, params)
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def fetchall(
        self, query: str, params: tuple | dict | None = None
    ) -> list[dict[str, Any]]:
        """Fetch all rows as list of dictionaries."""
        cursor = await self.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def commit(self) -> None:
        """Commit transaction."""
        await self.connection.commit()

    async def rollback(self) -> None:
        """Rollback transaction."""
        await self.connection.rollback()


# Global database instance
db = Database()


async def get_db() -> Database:
    """Dependency for getting database instance."""
    if not db._connection:
        await db.connect()
    return db


async def init_db() -> None:
    """Initialize database connection."""
    await db.connect()


async def close_db() -> None:
    """Close database connection."""
    await db.disconnect()
