#!/usr/bin/env python3
"""
Backup script for Knowledge Platform.

Backs up SQLite database and ChromaDB vector store to a timestamped archive.

Usage:
    python scripts/backup.py [--output-dir DIR]

Examples:
    # Backup to default directory (./backups/)
    python scripts/backup.py

    # Backup to specific directory
    python scripts/backup.py --output-dir /path/to/backups
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


def get_timestamp() -> str:
    """Get formatted timestamp for backup filename."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def get_backup_name(timestamp: str) -> str:
    """Generate backup archive name."""
    return f"knowledge_backup_{timestamp}.tar.gz"


def backup_database(backup_dir: Path, timestamp: str) -> Path | None:
    """Backup SQLite database.

    Args:
        backup_dir: Directory to store backup files.
        timestamp: Timestamp string for naming.

    Returns:
        Path to backed up file, or None if source doesn't exist.
    """
    db_path = Path(settings.database_path)

    if not db_path.exists():
        print(f"  [SKIP] Database not found: {db_path}")
        return None

    dest = backup_dir / f"knowledge_{timestamp}.db"
    shutil.copy2(db_path, dest)

    size_mb = dest.stat().st_size / (1024 * 1024)
    print(f"  [OK] Database backed up: {dest.name} ({size_mb:.2f} MB)")
    return dest


def backup_chromadb(backup_dir: Path, timestamp: str) -> Path | None:
    """Backup ChromaDB directory.

    Args:
        backup_dir: Directory to store backup files.
        timestamp: Timestamp string for naming.

    Returns:
        Path to backed up directory, or None if source doesn't exist.
    """
    chroma_path = Path(settings.chroma_path)

    if not chroma_path.exists():
        print(f"  [SKIP] ChromaDB not found: {chroma_path}")
        return None

    dest = backup_dir / f"chroma_{timestamp}"
    shutil.copytree(chroma_path, dest)

    # Calculate total size
    total_size = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file())
    size_mb = total_size / (1024 * 1024)
    print(f"  [OK] ChromaDB backed up: {dest.name} ({size_mb:.2f} MB)")
    return dest


def create_archive(backup_dir: Path, archive_path: Path, files: list[Path]) -> None:
    """Create tar.gz archive from backup files.

    Args:
        backup_dir: Directory containing backup files.
        archive_path: Path for the output archive.
        files: List of files/directories to include.
    """
    with tarfile.open(archive_path, "w:gz") as tar:
        for file_path in files:
            # Use relative path in archive
            arcname = file_path.name
            tar.add(file_path, arcname=arcname)

    size_mb = archive_path.stat().st_size / (1024 * 1024)
    print(f"\n  Archive created: {archive_path}")
    print(f"  Archive size: {size_mb:.2f} MB")


def cleanup_temp_files(files: list[Path]) -> None:
    """Remove temporary backup files after archiving.

    Args:
        files: List of files/directories to remove.
    """
    for file_path in files:
        if file_path.is_dir():
            shutil.rmtree(file_path)
        elif file_path.exists():
            file_path.unlink()


def verify_backup(archive_path: Path) -> bool:
    """Verify backup archive integrity.

    Args:
        archive_path: Path to the backup archive.

    Returns:
        True if archive is valid, False otherwise.
    """
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            members = tar.getnames()
            print(f"\n  Archive contents:")
            for member in members:
                print(f"    - {member}")
            return len(members) > 0
    except Exception as e:
        print(f"  [ERROR] Archive verification failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Backup Knowledge Platform data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default="./backups",
        help="Output directory for backups (default: ./backups)",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip archive verification",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep temporary files after archiving",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Knowledge Platform Backup")
    print("=" * 60)

    # Setup
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = get_timestamp()
    temp_dir = output_dir / f"temp_{timestamp}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nTimestamp: {timestamp}")
    print(f"Output directory: {output_dir.absolute()}")
    print(f"\nSource paths:")
    print(f"  Database: {settings.database_path}")
    print(f"  ChromaDB: {settings.chroma_path}")

    # Backup files
    print(f"\nBacking up...")
    backed_up_files: list[Path] = []

    db_backup = backup_database(temp_dir, timestamp)
    if db_backup:
        backed_up_files.append(db_backup)

    chroma_backup = backup_chromadb(temp_dir, timestamp)
    if chroma_backup:
        backed_up_files.append(chroma_backup)

    if not backed_up_files:
        print("\n[ERROR] No files to backup. Exiting.")
        shutil.rmtree(temp_dir)
        sys.exit(1)

    # Create archive
    print(f"\nCreating archive...")
    archive_name = get_backup_name(timestamp)
    archive_path = output_dir / archive_name

    create_archive(temp_dir, archive_path, backed_up_files)

    # Verify
    if not args.no_verify:
        print(f"\nVerifying archive...")
        if verify_backup(archive_path):
            print("  [OK] Archive verified successfully")
        else:
            print("  [WARNING] Archive verification failed")

    # Cleanup
    if not args.keep_temp:
        shutil.rmtree(temp_dir)

    print("\n" + "=" * 60)
    print("Backup completed successfully!")
    print(f"Archive: {archive_path.absolute()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
