"""Article import service with deduplication logic."""

import hashlib
import json
from datetime import datetime
from typing import Any

from ..storage.database import Database
from ..storage.models import (
    ArticleCreate,
    ArticleTreeNode,
    ImportResult,
    ImportResultItem,
    ImportStatus,
    TreeImportResult,
)


class ImportService:
    """Service for importing articles with deduplication."""

    def __init__(self, db: Database):
        """Initialize with database connection."""
        self.db = db

    @staticmethod
    def calculate_content_hash(content: str) -> str:
        """Calculate MD5 hash of content for deduplication.

        Args:
            content: Article content.

        Returns:
            MD5 hash string.
        """
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    async def check_duplicate(
        self, source_type: str, source_id: str
    ) -> dict[str, Any] | None:
        """Check if article already exists.

        Args:
            source_type: Source type (notion, web, etc.).
            source_id: Unique identifier from source.

        Returns:
            Existing article dict or None.
        """
        return await self.db.fetchone(
            """
            SELECT id, content_hash, version
            FROM articles
            WHERE source_type = ? AND source_id = ?
            """,
            (source_type, source_id),
        )

    async def import_article(self, article: ArticleCreate) -> ImportResultItem:
        """Import a single article with deduplication.

        Logic:
        - If not exists: INSERT (status: new)
        - If exists and same content_hash: SKIP (status: skipped)
        - If exists and different content_hash: UPDATE (status: updated)

        Args:
            article: Article data to import.

        Returns:
            ImportResultItem with status and article_id.
        """
        content_hash = self.calculate_content_hash(article.content)

        # Check for existing article
        existing = await self.check_duplicate(
            article.source_type.value, article.source_id
        )

        if existing is None:
            # New article - INSERT
            article_id = await self._insert_article(article, content_hash)
            return ImportResultItem(
                source_id=article.source_id,
                title=article.title,
                status=ImportStatus.NEW,
                article_id=article_id,
            )

        if existing["content_hash"] == content_hash:
            # Same content - SKIP
            return ImportResultItem(
                source_id=article.source_id,
                title=article.title,
                status=ImportStatus.SKIPPED,
                article_id=existing["id"],
                message="Content unchanged",
            )

        # Content changed - UPDATE
        article_id = await self._update_article(
            existing["id"],
            article,
            content_hash,
            existing["content_hash"],
            existing["version"],
        )
        return ImportResultItem(
            source_id=article.source_id,
            title=article.title,
            status=ImportStatus.UPDATED,
            article_id=article_id,
            message=f"Updated to version {existing['version'] + 1}",
        )

    async def import_batch(
        self, articles: list[ArticleCreate], source: str = "extension"
    ) -> ImportResult:
        """Import multiple articles in batch.

        Args:
            articles: List of articles to import.
            source: Import source (extension, cli, etc.).

        Returns:
            ImportResult with all results and summary.
        """
        results: list[ImportResultItem] = []
        summary = {
            ImportStatus.NEW.value: 0,
            ImportStatus.UPDATED.value: 0,
            ImportStatus.SKIPPED.value: 0,
            ImportStatus.ERROR.value: 0,
        }

        for article in articles:
            try:
                result = await self.import_article(article)
                results.append(result)
                summary[result.status.value] += 1
            except Exception as e:
                results.append(
                    ImportResultItem(
                        source_id=article.source_id,
                        title=article.title,
                        status=ImportStatus.ERROR,
                        message=str(e),
                    )
                )
                summary[ImportStatus.ERROR.value] += 1

        # Record batch
        batch_id = await self._record_batch(source, None, summary)

        await self.db.commit()

        return ImportResult(
            success=True,
            batch_id=batch_id,
            results=results,
            summary=summary,
        )

    async def import_tree(
        self, root: ArticleTreeNode, source: str = "extension"
    ) -> TreeImportResult:
        """Import article tree with hierarchy.

        Args:
            root: Root node of article tree.
            source: Import source.

        Returns:
            TreeImportResult with hierarchy info.
        """
        results: list[ImportResultItem] = []
        summary = {
            ImportStatus.NEW.value: 0,
            ImportStatus.UPDATED.value: 0,
            ImportStatus.SKIPPED.value: 0,
            ImportStatus.ERROR.value: 0,
        }
        hierarchy_count = 0

        # Import root
        root_article = ArticleCreate(
            source_type=root.source_type,
            source_id=root.source_id,
            title=root.title,
            content=root.content,
            url=root.url,
            author=root.author,
            published_at=root.published_at,
            tags=root.tags,
        )
        root_result = await self.import_article(root_article)
        results.append(root_result)
        summary[root_result.status.value] += 1

        root_id = root_result.article_id

        # Import children recursively
        async def import_children(
            parent_id: int | None, children: list[ArticleTreeNode]
        ) -> None:
            nonlocal hierarchy_count

            for child in children:
                child_article = ArticleCreate(
                    source_type=child.source_type,
                    source_id=child.source_id,
                    title=child.title,
                    content=child.content,
                    url=child.url,
                    author=child.author,
                    published_at=child.published_at,
                    tags=child.tags,
                )
                try:
                    child_result = await self.import_article(child_article)
                    results.append(child_result)
                    summary[child_result.status.value] += 1

                    # Record hierarchy
                    if parent_id and child_result.article_id:
                        await self._record_hierarchy(parent_id, child_result.article_id)
                        hierarchy_count += 1

                    # Recurse for grandchildren
                    if child.children and child_result.article_id:
                        await import_children(child_result.article_id, child.children)

                except Exception as e:
                    results.append(
                        ImportResultItem(
                            source_id=child.source_id,
                            title=child.title,
                            status=ImportStatus.ERROR,
                            message=str(e),
                        )
                    )
                    summary[ImportStatus.ERROR.value] += 1

        # Import all children
        await import_children(root_id, root.children)

        # Record batch
        batch_id = await self._record_batch(source, None, summary)

        await self.db.commit()

        return TreeImportResult(
            success=True,
            batch_id=batch_id,
            results=results,
            summary=summary,
            root_id=root_id,
            hierarchy_count=hierarchy_count,
        )

    async def _insert_article(
        self, article: ArticleCreate, content_hash: str
    ) -> int:
        """Insert new article into database."""
        tags_json = json.dumps(article.tags) if article.tags else "[]"

        cursor = await self.db.execute(
            """
            INSERT INTO articles (
                source_type, source_id, title, content, content_hash,
                url, author, published_at, tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                article.source_type.value,
                article.source_id,
                article.title,
                article.content,
                content_hash,
                article.url,
                article.author,
                article.published_at.isoformat() if article.published_at else None,
                tags_json,
            ),
        )
        await self.db.commit()
        return cursor.lastrowid

    async def _update_article(
        self,
        article_id: int,
        article: ArticleCreate,
        new_hash: str,
        old_hash: str,
        old_version: int,
    ) -> int:
        """Update existing article and record history."""
        # Get old content for history
        old_article = await self.db.fetchone(
            "SELECT content FROM articles WHERE id = ?", (article_id,)
        )

        # Record history
        await self.db.execute(
            """
            INSERT INTO article_history (
                article_id, version, old_content, new_content,
                old_content_hash, new_content_hash
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                article_id,
                old_version,
                old_article["content"] if old_article else None,
                article.content,
                old_hash,
                new_hash,
            ),
        )

        # Update article
        tags_json = json.dumps(article.tags) if article.tags else "[]"
        new_version = old_version + 1

        await self.db.execute(
            """
            UPDATE articles SET
                title = ?,
                content = ?,
                content_hash = ?,
                url = ?,
                author = ?,
                published_at = ?,
                tags = ?,
                version = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                article.title,
                article.content,
                new_hash,
                article.url,
                article.author,
                article.published_at.isoformat() if article.published_at else None,
                tags_json,
                new_version,
                article_id,
            ),
        )
        await self.db.commit()
        return article_id

    async def _record_hierarchy(self, parent_id: int, child_id: int) -> None:
        """Record parent-child relationship."""
        await self.db.execute(
            """
            INSERT OR IGNORE INTO article_hierarchy (parent_id, child_id)
            VALUES (?, ?)
            """,
            (parent_id, child_id),
        )

    async def _record_batch(
        self, source: str, file_name: str | None, summary: dict[str, int]
    ) -> int:
        """Record import batch."""
        cursor = await self.db.execute(
            """
            INSERT INTO import_batches (
                source, file_name, new_count, updated_count,
                skipped_count, error_count
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                source,
                file_name,
                summary.get("new", 0),
                summary.get("updated", 0),
                summary.get("skipped", 0),
                summary.get("error", 0),
            ),
        )
        return cursor.lastrowid
