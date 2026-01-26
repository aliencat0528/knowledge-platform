#!/usr/bin/env python3
"""Database setup script.

Usage:
    python scripts/setup_db.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from packages.server.storage.database import db, SCHEMA
from packages.server.config import settings


async def setup_database():
    """Initialize the database with schema."""
    print(f"Setting up database at: {settings.database_path}")

    # Ensure data directory exists
    settings.ensure_data_dir()

    # Connect and create schema
    await db.connect()

    # Verify tables exist
    tables = await db.fetchall(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    table_names = [t["name"] for t in tables]

    print(f"\nCreated tables:")
    for name in table_names:
        if not name.startswith("sqlite_"):
            # Get row count
            result = await db.fetchone(f"SELECT COUNT(*) as count FROM {name}")
            count = result["count"] if result else 0
            print(f"  - {name} ({count} rows)")

    # Verify indexes
    indexes = await db.fetchall(
        "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
    )
    print(f"\nCreated indexes:")
    for idx in indexes:
        print(f"  - {idx['name']}")

    await db.disconnect()
    print(f"\n✅ Database setup complete!")


if __name__ == "__main__":
    asyncio.run(setup_database())
