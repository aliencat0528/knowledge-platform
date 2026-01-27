#!/usr/bin/env python3
"""
Restore script for Knowledge Platform.

Restores SQLite database and ChromaDB vector store from a backup archive.

Usage:
    python scripts/restore.py <backup_archive>

Examples:
    # Restore from backup
    python scripts/restore.py backups/knowledge_backup_20240126_120000.tar.gz

    # Preview restore without making changes
    python scripts/restore.py backups/knowledge_backup_20240126_120000.tar.gz --preview

    # Force restore without confirmation
    python scripts/restore.py backups/knowledge_backup_20240126_120000.tar.gz --force
"""

import argparse
import os
import shutil
import sys
import tarfile
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.server.config import settings


def list_archive_contents(archive_path: Path) -> list[str]:
    """List contents of backup archive.

    Args:
        archive_path: Path to the backup archive.

    Returns:
        List of member names in the archive.
    """
    with tarfile.open(archive_path, "r:gz") as tar:
        return tar.getnames()


def extract_archive(archive_path: Path, extract_dir: Path) -> list[Path]:
    """Extract backup archive to temporary directory.

    Args:
        archive_path: Path to the backup archive.
        extract_dir: Directory to extract files to.

    Returns:
        List of extracted file/directory paths.
    """
    extract_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(extract_dir)

    return list(extract_dir.iterdir())


def backup_current_data(backup_dir: Path) -> dict[str, Path | None]:
    """Create backup of current data before restore.

    Args:
        backup_dir: Directory to store current data backup.

    Returns:
        Dictionary mapping data type to backup path.
    """
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backups: dict[str, Path | None] = {}

    # Backup current database
    db_path = Path(settings.database_path)
    if db_path.exists():
        db_backup = backup_dir / f"knowledge_pre_restore_{timestamp}.db"
        shutil.copy2(db_path, db_backup)
        backups["database"] = db_backup
        print(f"  [OK] Current database backed up: {db_backup.name}")
    else:
        backups["database"] = None

    # Backup current ChromaDB
    chroma_path = Path(settings.chroma_path)
    if chroma_path.exists():
        chroma_backup = backup_dir / f"chroma_pre_restore_{timestamp}"
        shutil.copytree(chroma_path, chroma_backup)
        backups["chromadb"] = chroma_backup
        print(f"  [OK] Current ChromaDB backed up: {chroma_backup.name}")
    else:
        backups["chromadb"] = None

    return backups


def restore_database(extracted_dir: Path) -> bool:
    """Restore SQLite database from extracted backup.

    Args:
        extracted_dir: Directory containing extracted backup files.

    Returns:
        True if restore succeeded, False otherwise.
    """
    # Find database file in extracted backup
    db_files = list(extracted_dir.glob("knowledge_*.db"))

    if not db_files:
        print("  [SKIP] No database file found in backup")
        return False

    source_db = db_files[0]
    dest_db = Path(settings.database_path)

    # Ensure destination directory exists
    dest_db.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing database
    if dest_db.exists():
        dest_db.unlink()

    # Copy restored database
    shutil.copy2(source_db, dest_db)

    size_mb = dest_db.stat().st_size / (1024 * 1024)
    print(f"  [OK] Database restored: {dest_db} ({size_mb:.2f} MB)")
    return True


def restore_chromadb(extracted_dir: Path) -> bool:
    """Restore ChromaDB directory from extracted backup.

    Args:
        extracted_dir: Directory containing extracted backup files.

    Returns:
        True if restore succeeded, False otherwise.
    """
    # Find ChromaDB directory in extracted backup
    chroma_dirs = [d for d in extracted_dir.iterdir() if d.is_dir() and d.name.startswith("chroma_")]

    if not chroma_dirs:
        print("  [SKIP] No ChromaDB directory found in backup")
        return False

    source_chroma = chroma_dirs[0]
    dest_chroma = Path(settings.chroma_path)

    # Ensure parent directory exists
    dest_chroma.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing ChromaDB
    if dest_chroma.exists():
        shutil.rmtree(dest_chroma)

    # Copy restored ChromaDB
    shutil.copytree(source_chroma, dest_chroma)

    # Calculate size
    total_size = sum(f.stat().st_size for f in dest_chroma.rglob("*") if f.is_file())
    size_mb = total_size / (1024 * 1024)
    print(f"  [OK] ChromaDB restored: {dest_chroma} ({size_mb:.2f} MB)")
    return True


def verify_restore() -> dict[str, dict]:
    """Verify restored data is accessible.

    Returns:
        Dictionary with verification results.
    """
    results = {
        "database": {"status": "unknown", "message": ""},
        "chromadb": {"status": "unknown", "message": ""},
    }

    # Verify database
    db_path = Path(settings.database_path)
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cursor = conn.execute("SELECT COUNT(*) FROM articles")
            count = cursor.fetchone()[0]
            conn.close()
            results["database"]["status"] = "ok"
            results["database"]["message"] = f"{count} articles found"
        except Exception as e:
            results["database"]["status"] = "error"
            results["database"]["message"] = str(e)
    else:
        results["database"]["status"] = "missing"
        results["database"]["message"] = "Database file not found"

    # Verify ChromaDB
    chroma_path = Path(settings.chroma_path)
    if chroma_path.exists():
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(chroma_path))
            collections = client.list_collections()
            results["chromadb"]["status"] = "ok"
            results["chromadb"]["message"] = f"{len(collections)} collections found"
        except Exception as e:
            results["chromadb"]["status"] = "error"
            results["chromadb"]["message"] = str(e)
    else:
        results["chromadb"]["status"] = "missing"
        results["chromadb"]["message"] = "ChromaDB directory not found"

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Restore Knowledge Platform data from backup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "archive",
        type=str,
        help="Path to backup archive (.tar.gz)",
    )
    parser.add_argument(
        "--preview",
        "-p",
        action="store_true",
        help="Preview restore without making changes",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force restore without confirmation",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip backing up current data before restore",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip verification after restore",
    )

    args = parser.parse_args()

    archive_path = Path(args.archive)

    if not archive_path.exists():
        print(f"[ERROR] Archive not found: {archive_path}")
        sys.exit(1)

    print("=" * 60)
    print("Knowledge Platform Restore")
    print("=" * 60)

    print(f"\nArchive: {archive_path.absolute()}")
    print(f"Archive size: {archive_path.stat().st_size / (1024 * 1024):.2f} MB")

    # List archive contents
    print(f"\nArchive contents:")
    contents = list_archive_contents(archive_path)
    for item in contents:
        print(f"  - {item}")

    print(f"\nTarget paths:")
    print(f"  Database: {settings.database_path}")
    print(f"  ChromaDB: {settings.chroma_path}")

    # Preview mode - exit here
    if args.preview:
        print("\n[PREVIEW MODE] No changes made.")
        sys.exit(0)

    # Confirmation
    if not args.force:
        print("\n" + "-" * 60)
        print("WARNING: This will overwrite existing data!")
        print("-" * 60)
        response = input("\nProceed with restore? (yes/no): ").strip().lower()
        if response != "yes":
            print("\nRestore cancelled.")
            sys.exit(0)

    # Backup current data
    if not args.no_backup:
        print(f"\nBacking up current data...")
        backup_dir = Path("./backups/pre_restore")
        current_backups = backup_current_data(backup_dir)
        if any(current_backups.values()):
            print(f"  Pre-restore backups saved to: {backup_dir.absolute()}")

    # Extract archive
    print(f"\nExtracting archive...")
    temp_dir = Path(f"./backups/temp_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

    try:
        extracted_files = extract_archive(archive_path, temp_dir)
        print(f"  [OK] Extracted {len(extracted_files)} items")

        # Restore
        print(f"\nRestoring data...")
        db_restored = restore_database(temp_dir)
        chroma_restored = restore_chromadb(temp_dir)

        if not db_restored and not chroma_restored:
            print("\n[ERROR] No data was restored. Check archive contents.")
            sys.exit(1)

        # Verify
        if not args.no_verify:
            print(f"\nVerifying restored data...")
            results = verify_restore()
            for name, result in results.items():
                status = result["status"]
                msg = result["message"]
                icon = "[OK]" if status == "ok" else "[!]"
                print(f"  {icon} {name}: {msg}")

    finally:
        # Cleanup temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    print("\n" + "=" * 60)
    print("Restore completed successfully!")
    print("=" * 60)
    print("\nRestart the server to apply changes:")
    print("  uvicorn packages.server.main:app --reload")


if __name__ == "__main__":
    main()
