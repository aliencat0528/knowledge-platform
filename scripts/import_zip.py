#!/usr/bin/env python3
"""
Import Notion Export .zip file into Knowledge Platform.

Usage:
    python scripts/import_zip.py <path-to-zip>
    python scripts/import_zip.py export.zip --preview

Examples:
    # Import a zip file
    python scripts/import_zip.py ~/Downloads/Export.zip

    # Preview without importing
    python scripts/import_zip.py ~/Downloads/Export.zip --preview
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from packages.server.storage.database import init_db, close_db, get_db
from packages.server.services.zip_import_service import ZipImportService


async def main():
    parser = argparse.ArgumentParser(
        description="Import Notion Export .zip file into Knowledge Platform"
    )
    parser.add_argument(
        "zip_file",
        type=str,
        help="Path to the .zip file to import"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview contents without importing"
    )

    args = parser.parse_args()
    zip_path = Path(args.zip_file).expanduser().resolve()

    if not zip_path.exists():
        print(f"Error: File not found: {zip_path}")
        sys.exit(1)

    if not zip_path.suffix.lower() == ".zip":
        print(f"Error: Not a zip file: {zip_path}")
        sys.exit(1)

    print(f"{'=' * 50}")
    print(f"Knowledge Platform - Zip Import")
    print(f"{'=' * 50}")
    print(f"File: {zip_path}")
    print()

    # Initialize database
    await init_db()
    db = await get_db()

    try:
        service = ZipImportService(db)

        if args.preview:
            # Preview mode
            print("Previewing contents...")
            print()

            preview = await service.get_import_preview(zip_path)

            print(f"Total files: {preview['total_files']}")
            print(f"Directories: {preview['directories']}")
            print()

            if preview['files']:
                print("Files to import:")
                print("-" * 40)
                for f in preview['files']:
                    print(f"  - {f['title']}")
                    print(f"    ID: {f['source_id'][:8]}...")
                    print()

                if preview['has_more']:
                    remaining = preview['total_files'] - len(preview['files'])
                    print(f"  ... and {remaining} more files")

        else:
            # Import mode
            print("Importing...")
            print()

            result = await service.import_zip(zip_path, source="cli")

            # Show results
            summary = result.summary
            print("Import complete!")
            print("-" * 40)
            print(f"  New:     {summary.get('new', 0)}")
            print(f"  Updated: {summary.get('updated', 0)}")
            print(f"  Skipped: {summary.get('skipped', 0)}")
            print(f"  Errors:  {summary.get('error', 0)}")
            print()

            total = sum(summary.values())
            print(f"Total processed: {total}")

            # Show some results
            if result.results:
                print()
                print("Sample results:")
                for item in result.results[:5]:
                    status_icon = {
                        "new": "✨",
                        "updated": "🔄",
                        "skipped": "⏭️",
                        "error": "❌",
                    }.get(item.status.value, "❓")
                    print(f"  {status_icon} {item.title[:40]}... ({item.status.value})")

                if len(result.results) > 5:
                    print(f"  ... and {len(result.results) - 5} more")

    finally:
        await close_db()

    print()
    print(f"{'=' * 50}")
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
