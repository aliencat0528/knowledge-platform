"""Zip file import service for Notion Export files."""

import hashlib
import re
import zipfile
from pathlib import Path
from typing import Any

from ..storage.database import Database
from ..storage.models import ArticleCreate, ImportResult, SourceType
from .import_service import ImportService


class ZipImportService:
    """Service for importing Notion Export .zip files."""

    # Pattern to extract Notion page ID from filename
    PAGE_ID_PATTERN = re.compile(r"\s+([a-f0-9]{32})$", re.IGNORECASE)

    # File extensions to process
    SUPPORTED_EXTENSIONS = {".md", ".html", ".htm"}

    # Files/directories to skip
    SKIP_PATTERNS = [
        r"__MACOSX",
        r"\.DS_Store",
        r"thumbs\.db",
    ]

    def __init__(self, db: Database):
        """Initialize with database connection."""
        self.db = db
        self.import_service = ImportService(db)

    async def import_zip(
        self,
        zip_path: str | Path,
        source: str = "zip",
    ) -> ImportResult:
        """Import a Notion Export .zip file.

        Args:
            zip_path: Path to the .zip file.
            source: Import source identifier.

        Returns:
            ImportResult with statistics.
        """
        zip_path = Path(zip_path)

        if not zip_path.exists():
            raise FileNotFoundError(f"Zip file not found: {zip_path}")

        if not zip_path.suffix.lower() == ".zip":
            raise ValueError(f"Not a zip file: {zip_path}")

        articles = []
        hierarchy: dict[str, list[str]] = {}  # parent_path -> [child_paths]

        with zipfile.ZipFile(zip_path, "r") as zf:
            # Get all file names
            file_list = [
                name for name in zf.namelist()
                if not self._should_skip(name)
            ]

            # Process each file
            for file_name in file_list:
                # Skip directories
                if file_name.endswith("/"):
                    continue

                # Check extension
                file_path = Path(file_name)
                if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                    continue

                try:
                    # Read file content
                    content = zf.read(file_name).decode("utf-8")

                    # Skip empty files
                    if not content.strip():
                        continue

                    # Parse filename
                    parsed = self._parse_filename(file_path)

                    # Create article
                    article = ArticleCreate(
                        source_type=SourceType.NOTION,
                        source_id=parsed["source_id"],
                        title=parsed["title"],
                        content=content,
                        url=None,
                        tags=[],
                    )

                    articles.append({
                        "article": article,
                        "path": file_name,
                        "parent_path": str(file_path.parent) if file_path.parent != Path(".") else None,
                    })

                    # Track hierarchy
                    parent = str(file_path.parent)
                    if parent and parent != ".":
                        if parent not in hierarchy:
                            hierarchy[parent] = []
                        hierarchy[parent].append(file_name)

                except Exception as e:
                    print(f"Error processing {file_name}: {e}")
                    continue

        # Import all articles
        if not articles:
            return ImportResult(
                success=True,
                results=[],
                summary={"new": 0, "updated": 0, "skipped": 0, "error": 0},
            )

        # Batch import
        article_list = [a["article"] for a in articles]
        result = await self.import_service.import_batch(article_list, source=source)

        # TODO: Establish hierarchy relationships based on directory structure

        return result

    def _should_skip(self, file_name: str) -> bool:
        """Check if file should be skipped."""
        for pattern in self.SKIP_PATTERNS:
            if re.search(pattern, file_name, re.IGNORECASE):
                return True
        return False

    def _parse_filename(self, file_path: Path) -> dict[str, str]:
        """Parse Notion export filename to extract title and page ID.

        Notion exports files with format: "Title abc123def456...32chars.md"

        Args:
            file_path: Path object of the file.

        Returns:
            Dict with 'title' and 'source_id'.
        """
        stem = file_path.stem

        # Try to extract 32-char page ID from end of filename
        match = self.PAGE_ID_PATTERN.search(stem)

        if match:
            title = stem[: match.start()].strip()
            source_id = match.group(1).lower()
        else:
            title = stem
            # Generate source_id from title hash
            source_id = hashlib.md5(stem.encode("utf-8")).hexdigest()

        return {
            "title": title or "Untitled",
            "source_id": source_id,
        }

    async def get_import_preview(
        self,
        zip_path: str | Path,
    ) -> dict[str, Any]:
        """Preview contents of a zip file before importing.

        Args:
            zip_path: Path to the .zip file.

        Returns:
            Preview information including file count and structure.
        """
        zip_path = Path(zip_path)

        if not zip_path.exists():
            raise FileNotFoundError(f"Zip file not found: {zip_path}")

        files = []
        directories = set()

        with zipfile.ZipFile(zip_path, "r") as zf:
            for file_name in zf.namelist():
                if self._should_skip(file_name):
                    continue

                if file_name.endswith("/"):
                    directories.add(file_name)
                    continue

                file_path = Path(file_name)
                if file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    parsed = self._parse_filename(file_path)
                    files.append({
                        "path": file_name,
                        "title": parsed["title"],
                        "source_id": parsed["source_id"],
                    })

        return {
            "zip_path": str(zip_path),
            "total_files": len(files),
            "directories": len(directories),
            "files": files[:20],  # Preview first 20
            "has_more": len(files) > 20,
        }
