"""Notion sync service for syncing articles to Notion database."""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Any

from notion_client import AsyncClient
from notion_client.errors import APIResponseError, HTTPResponseError

from ..config import settings
from ..storage.database import Database

logger = logging.getLogger(__name__)


class NotionSyncError(Exception):
    """Exception raised when Notion sync fails."""

    def __init__(self, message: str, code: str = "NOTION_SYNC_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class NotionSync:
    """Service for syncing articles to Notion database."""

    # Retry settings for rate limiting
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # seconds

    def __init__(
        self,
        api_key: str | None = None,
        database_id: str | None = None,
    ):
        """Initialize Notion sync service.

        Args:
            api_key: Notion API key. Defaults to settings.notion_api_key.
            database_id: Notion database ID. Defaults to settings.notion_database_id.

        Raises:
            ValueError: If API key or database ID is not provided.
        """
        self.api_key = api_key or settings.notion_api_key
        self.database_id = database_id or settings.notion_database_id

        if not self.api_key:
            raise ValueError(
                "Notion API key not configured. "
                "Set NOTION_API_KEY environment variable."
            )
        if not self.database_id:
            raise ValueError(
                "Notion database ID not configured. "
                "Set NOTION_DATABASE_ID environment variable."
            )

        self.client = AsyncClient(auth=self.api_key)

    async def sync_article(
        self,
        db: Database,
        article_id: int,
    ) -> dict[str, Any]:
        """Sync an article to Notion.

        If the article has a notion_page_id, update the existing page.
        Otherwise, create a new page.

        Args:
            db: Database connection.
            article_id: Article ID to sync.

        Returns:
            Dict with notion_page_id, notion_url, and synced_at.

        Raises:
            NotionSyncError: If sync fails.
        """
        # Fetch article from database
        article = await db.fetchone(
            """
            SELECT id, source_type, source_id, title, content, url, author,
                   published_at, tags, notion_page_id, created_at
            FROM articles WHERE id = ?
            """,
            (article_id,),
        )

        if not article:
            raise NotionSyncError(
                f"Article {article_id} not found",
                code="ARTICLE_NOT_FOUND",
            )

        # Parse tags from JSON
        tags = []
        if article["tags"]:
            try:
                tags = json.loads(article["tags"])
            except (json.JSONDecodeError, TypeError):
                pass

        # Build article data dict
        article_data = {
            "id": article["id"],
            "source_type": article["source_type"],
            "source_id": article["source_id"],
            "title": article["title"],
            "content": article["content"],
            "url": article["url"],
            "author": article["author"],
            "published_at": article["published_at"],
            "tags": tags,
            "created_at": article["created_at"],
        }

        # Sync to Notion
        if article["notion_page_id"]:
            # Update existing page
            result = await self._update_page(
                article["notion_page_id"],
                article_data,
            )
        else:
            # Create new page
            result = await self._create_page(article_data)

        # Update database with sync info
        await db.execute(
            """
            UPDATE articles
            SET notion_page_id = ?, notion_synced_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (result["notion_page_id"], article_id),
        )
        await db.commit()

        return result

    async def _create_page(self, article: dict[str, Any]) -> dict[str, Any]:
        """Create a new Notion page for the article.

        Args:
            article: Article data dict.

        Returns:
            Dict with notion_page_id, notion_url, and synced_at.
        """
        properties = self._build_properties(article)
        children = self._markdown_to_blocks(article["content"])

        for attempt in range(self.MAX_RETRIES):
            try:
                response = await self.client.pages.create(
                    parent={"database_id": self.database_id},
                    properties=properties,
                    children=children[:100],  # Notion limits to 100 blocks per request
                )

                # If there are more blocks, append them in batches
                if len(children) > 100:
                    await self._append_remaining_blocks(
                        response["id"],
                        children[100:],
                    )

                return {
                    "notion_page_id": response["id"],
                    "notion_url": response["url"],
                    "synced_at": datetime.now().isoformat(),
                }

            except HTTPResponseError as e:
                if e.status == 429:  # Rate limited
                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                        continue
                raise NotionSyncError(
                    f"Notion API error: {e.message}",
                    code="NOTION_API_ERROR",
                )
            except APIResponseError as e:
                raise NotionSyncError(
                    f"Notion API error: {str(e)}",
                    code="NOTION_API_ERROR",
                )

    async def _update_page(
        self,
        page_id: str,
        article: dict[str, Any],
    ) -> dict[str, Any]:
        """Update an existing Notion page.

        Args:
            page_id: Notion page ID.
            article: Article data dict.

        Returns:
            Dict with notion_page_id, notion_url, and synced_at.
        """
        properties = self._build_properties(article)

        for attempt in range(self.MAX_RETRIES):
            try:
                # Update properties
                response = await self.client.pages.update(
                    page_id=page_id,
                    properties=properties,
                )

                # For content update, we need to delete existing blocks and add new ones
                # First, get existing blocks
                existing_blocks = await self.client.blocks.children.list(
                    block_id=page_id,
                )

                # Delete existing blocks
                for block in existing_blocks.get("results", []):
                    try:
                        await self.client.blocks.delete(block_id=block["id"])
                    except Exception:
                        pass  # Ignore errors when deleting blocks

                # Add new content blocks
                children = self._markdown_to_blocks(article["content"])
                if children:
                    await self._append_remaining_blocks(page_id, children)

                return {
                    "notion_page_id": response["id"],
                    "notion_url": response["url"],
                    "synced_at": datetime.now().isoformat(),
                }

            except HTTPResponseError as e:
                if e.status == 429:  # Rate limited
                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                        continue
                raise NotionSyncError(
                    f"Notion API error: {e.message}",
                    code="NOTION_API_ERROR",
                )
            except APIResponseError as e:
                raise NotionSyncError(
                    f"Notion API error: {str(e)}",
                    code="NOTION_API_ERROR",
                )

    async def _append_remaining_blocks(
        self,
        page_id: str,
        blocks: list[dict],
    ) -> None:
        """Append blocks to a page in batches.

        Args:
            page_id: Notion page ID.
            blocks: List of block objects.
        """
        batch_size = 100
        for i in range(0, len(blocks), batch_size):
            batch = blocks[i : i + batch_size]
            for attempt in range(self.MAX_RETRIES):
                try:
                    await self.client.blocks.children.append(
                        block_id=page_id,
                        children=batch,
                    )
                    break
                except HTTPResponseError as e:
                    if e.status == 429 and attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(self.RETRY_DELAY * (attempt + 1))
                        continue
                    raise

    def _build_properties(self, article: dict[str, Any]) -> dict[str, Any]:
        """Build Notion page properties from article data.

        Notion Database Schema Expected:
        - Name (title): Article title
        - URL (url): Article URL
        - Source Type (select): notion, medium, docs, web
        - Tags (multi_select): Article tags
        - Author (rich_text): Author name
        - Published (date): Published date
        - Saved At (date): When saved locally
        - Local ID (number): Local article ID

        Args:
            article: Article data dict.

        Returns:
            Notion properties dict.
        """
        properties: dict[str, Any] = {
            "Name": {
                "title": [{"text": {"content": article["title"][:2000]}}],
            },
            "Source Type": {
                "select": {"name": article["source_type"]},
            },
            "Local ID": {
                "number": article["id"],
            },
        }

        # Optional URL
        if article.get("url"):
            properties["URL"] = {"url": article["url"]}

        # Optional Author
        if article.get("author"):
            properties["Author"] = {
                "rich_text": [{"text": {"content": article["author"][:2000]}}],
            }

        # Optional Tags
        if article.get("tags"):
            properties["Tags"] = {
                "multi_select": [{"name": tag[:100]} for tag in article["tags"][:10]],
            }

        # Optional Published date
        if article.get("published_at"):
            try:
                if isinstance(article["published_at"], str):
                    date_str = article["published_at"][:10]  # YYYY-MM-DD
                else:
                    date_str = article["published_at"].strftime("%Y-%m-%d")
                properties["Published"] = {"date": {"start": date_str}}
            except (ValueError, AttributeError):
                pass

        # Saved At (created_at)
        if article.get("created_at"):
            try:
                if isinstance(article["created_at"], str):
                    date_str = article["created_at"][:10]
                else:
                    date_str = article["created_at"].strftime("%Y-%m-%d")
                properties["Saved At"] = {"date": {"start": date_str}}
            except (ValueError, AttributeError):
                pass

        return properties

    def _markdown_to_blocks(self, content: str) -> list[dict[str, Any]]:
        """Convert Markdown content to Notion blocks.

        Supports:
        - Headings (h1, h2, h3)
        - Paragraphs
        - Code blocks
        - Bullet lists
        - Numbered lists
        - Blockquotes
        - Horizontal rules

        Args:
            content: Markdown content.

        Returns:
            List of Notion block objects.
        """
        if not content:
            return []

        blocks: list[dict[str, Any]] = []
        lines = content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]

            # Skip empty lines
            if not line.strip():
                i += 1
                continue

            # Code blocks (```)
            if line.strip().startswith("```"):
                language = line.strip()[3:].strip() or "plain text"
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code_lines.append(lines[i])
                    i += 1
                code_content = "\n".join(code_lines)
                blocks.append(self._create_code_block(code_content, language))
                i += 1
                continue

            # Headings
            if line.startswith("# "):
                blocks.append(self._create_heading_block(line[2:], 1))
                i += 1
                continue
            if line.startswith("## "):
                blocks.append(self._create_heading_block(line[3:], 2))
                i += 1
                continue
            if line.startswith("### "):
                blocks.append(self._create_heading_block(line[4:], 3))
                i += 1
                continue

            # Horizontal rule
            if line.strip() in ("---", "***", "___"):
                blocks.append({"type": "divider", "divider": {}})
                i += 1
                continue

            # Blockquote
            if line.startswith("> "):
                quote_lines = [line[2:]]
                i += 1
                while i < len(lines) and lines[i].startswith("> "):
                    quote_lines.append(lines[i][2:])
                    i += 1
                blocks.append(self._create_quote_block("\n".join(quote_lines)))
                continue

            # Bullet list
            if line.strip().startswith("- ") or line.strip().startswith("* "):
                list_items = []
                while i < len(lines) and (
                    lines[i].strip().startswith("- ")
                    or lines[i].strip().startswith("* ")
                ):
                    item_text = lines[i].strip()[2:]
                    list_items.append(self._create_bullet_item(item_text))
                    i += 1
                blocks.extend(list_items)
                continue

            # Numbered list
            if re.match(r"^\d+\.\s", line.strip()):
                list_items = []
                while i < len(lines) and re.match(r"^\d+\.\s", lines[i].strip()):
                    item_text = re.sub(r"^\d+\.\s", "", lines[i].strip())
                    list_items.append(self._create_numbered_item(item_text))
                    i += 1
                blocks.extend(list_items)
                continue

            # Default: paragraph
            blocks.append(self._create_paragraph_block(line))
            i += 1

        return blocks

    def _create_heading_block(self, text: str, level: int) -> dict[str, Any]:
        """Create a heading block."""
        heading_type = f"heading_{level}"
        return {
            "type": heading_type,
            heading_type: {
                "rich_text": self._parse_rich_text(text),
            },
        }

    def _create_paragraph_block(self, text: str) -> dict[str, Any]:
        """Create a paragraph block."""
        return {
            "type": "paragraph",
            "paragraph": {
                "rich_text": self._parse_rich_text(text),
            },
        }

    def _create_code_block(self, code: str, language: str) -> dict[str, Any]:
        """Create a code block."""
        # Notion limits code block text to 2000 characters
        code = code[:2000]
        return {
            "type": "code",
            "code": {
                "rich_text": [{"type": "text", "text": {"content": code}}],
                "language": self._normalize_language(language),
            },
        }

    def _create_quote_block(self, text: str) -> dict[str, Any]:
        """Create a quote block."""
        return {
            "type": "quote",
            "quote": {
                "rich_text": self._parse_rich_text(text),
            },
        }

    def _create_bullet_item(self, text: str) -> dict[str, Any]:
        """Create a bulleted list item."""
        return {
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": self._parse_rich_text(text),
            },
        }

    def _create_numbered_item(self, text: str) -> dict[str, Any]:
        """Create a numbered list item."""
        return {
            "type": "numbered_list_item",
            "numbered_list_item": {
                "rich_text": self._parse_rich_text(text),
            },
        }

    def _parse_rich_text(self, text: str) -> list[dict[str, Any]]:
        """Parse text with inline formatting to Notion rich text.

        Supports:
        - Bold: **text** or __text__
        - Italic: *text* or _text_
        - Code: `code`
        - Links: [text](url)

        Args:
            text: Text to parse.

        Returns:
            List of rich text objects.
        """
        if not text:
            return []

        # Notion limits rich text to 2000 characters
        text = text[:2000]

        rich_text: list[dict[str, Any]] = []

        # Pattern for inline formatting
        # Order matters: check longer patterns first
        patterns = [
            # Bold
            (r"\*\*(.+?)\*\*", {"bold": True}),
            (r"__(.+?)__", {"bold": True}),
            # Italic
            (r"\*(.+?)\*", {"italic": True}),
            (r"_(.+?)_", {"italic": True}),
            # Code
            (r"`(.+?)`", {"code": True}),
            # Links
            (r"\[(.+?)\]\((.+?)\)", "link"),
        ]

        # Simple approach: if no inline formatting, return plain text
        has_formatting = any(
            re.search(p[0], text) for p in patterns if p[1] != "link"
        ) or re.search(r"\[.+?\]\(.+?\)", text)

        if not has_formatting:
            return [{"type": "text", "text": {"content": text}}]

        # Parse with inline formatting
        current_pos = 0
        remaining = text

        while remaining:
            earliest_match = None
            earliest_pos = len(remaining)
            match_pattern = None

            # Find earliest match
            for pattern, annotation in patterns:
                match = re.search(pattern, remaining)
                if match and match.start() < earliest_pos:
                    earliest_match = match
                    earliest_pos = match.start()
                    match_pattern = (pattern, annotation)

            if not earliest_match:
                # No more matches, add remaining as plain text
                if remaining:
                    rich_text.append(
                        {"type": "text", "text": {"content": remaining}}
                    )
                break

            # Add text before match
            if earliest_pos > 0:
                rich_text.append(
                    {"type": "text", "text": {"content": remaining[:earliest_pos]}}
                )

            # Add formatted text
            pattern, annotation = match_pattern
            if annotation == "link":
                link_text = earliest_match.group(1)
                link_url = earliest_match.group(2)
                rich_text.append(
                    {
                        "type": "text",
                        "text": {"content": link_text, "link": {"url": link_url}},
                    }
                )
            else:
                matched_text = earliest_match.group(1)
                rich_text.append(
                    {
                        "type": "text",
                        "text": {"content": matched_text},
                        "annotations": annotation,
                    }
                )

            # Move past the match
            remaining = remaining[earliest_match.end() :]

        return rich_text if rich_text else [{"type": "text", "text": {"content": text}}]

    def _normalize_language(self, language: str) -> str:
        """Normalize programming language name for Notion.

        Args:
            language: Language name from markdown.

        Returns:
            Notion-compatible language name.
        """
        language_map = {
            "js": "javascript",
            "ts": "typescript",
            "py": "python",
            "rb": "ruby",
            "sh": "bash",
            "shell": "bash",
            "yml": "yaml",
            "md": "markdown",
            "": "plain text",
        }
        return language_map.get(language.lower(), language.lower())

    async def get_sync_status(self, db: Database) -> dict[str, Any]:
        """Get overall sync status.

        Args:
            db: Database connection.

        Returns:
            Dict with sync statistics.
        """
        total = await db.fetchone("SELECT COUNT(*) as count FROM articles")
        synced = await db.fetchone(
            "SELECT COUNT(*) as count FROM articles WHERE notion_page_id IS NOT NULL"
        )
        pending = await db.fetchone(
            "SELECT COUNT(*) as count FROM articles WHERE notion_page_id IS NULL"
        )
        recent = await db.fetchall(
            """
            SELECT id, title, notion_page_id, notion_synced_at
            FROM articles
            WHERE notion_page_id IS NOT NULL
            ORDER BY notion_synced_at DESC
            LIMIT 5
            """
        )

        return {
            "total_articles": total["count"] if total else 0,
            "synced_count": synced["count"] if synced else 0,
            "pending_count": pending["count"] if pending else 0,
            "recent_syncs": recent,
            "database_id": self.database_id,
        }

    async def batch_sync(
        self,
        db: Database,
        article_ids: list[int] | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Batch sync multiple articles.

        Args:
            db: Database connection.
            article_ids: Specific article IDs to sync. If None, sync unsynced articles.
            limit: Maximum number of articles to sync.

        Returns:
            Dict with sync results.
        """
        if article_ids:
            # Sync specific articles
            ids_to_sync = article_ids[:limit]
        else:
            # Get unsynced articles
            rows = await db.fetchall(
                """
                SELECT id FROM articles
                WHERE notion_page_id IS NULL
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            ids_to_sync = [row["id"] for row in rows]

        results = {
            "success": [],
            "failed": [],
            "total": len(ids_to_sync),
        }

        for article_id in ids_to_sync:
            try:
                result = await self.sync_article(db, article_id)
                results["success"].append(
                    {
                        "article_id": article_id,
                        "notion_page_id": result["notion_page_id"],
                    }
                )
            except NotionSyncError as e:
                results["failed"].append(
                    {
                        "article_id": article_id,
                        "error": e.message,
                        "code": e.code,
                    }
                )
            except Exception as e:
                results["failed"].append(
                    {
                        "article_id": article_id,
                        "error": str(e),
                        "code": "UNKNOWN_ERROR",
                    }
                )

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.3)

        return results
