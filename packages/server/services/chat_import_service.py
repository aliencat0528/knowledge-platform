"""AI Chat import service for Claude Code, Cursor, and other AI editors."""

import hashlib
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from ..storage.database import Database
from ..storage.models import ArticleCreate, ImportResult, SourceType
from .import_service import ImportService


class ChatImportService:
    """Service for importing AI editor chat conversations."""

    # Supported source types
    SOURCES = {
        "claude-code": {
            "format": "jsonl",
            "description": "Claude Code CLI conversations",
            "path_hints": [
                "~/.claude/projects/",
                "~/.claude/history.jsonl",
            ],
        },
        "cursor": {
            "format": "sqlite",
            "description": "Cursor AI chat history",
            "path_hints": [
                "~/Library/Application Support/Cursor/User/workspaceStorage/",
            ],
        },
        "markdown": {
            "format": "markdown",
            "description": "Manually copied chat (markdown format)",
            "path_hints": [],
        },
    }

    def __init__(self, db: Database):
        """Initialize with database connection."""
        self.db = db
        self.import_service = ImportService(db)

    async def import_claude_code(
        self,
        path: str | Path,
        source: str = "claude-code",
    ) -> ImportResult:
        """Import Claude Code JSONL conversation file.

        Args:
            path: Path to JSONL file or project directory.
            source: Import source identifier.

        Returns:
            ImportResult with statistics.
        """
        path = Path(path).expanduser().resolve()

        # Find JSONL files
        jsonl_files = []
        if path.is_file() and path.suffix == ".jsonl":
            jsonl_files = [path]
        elif path.is_dir():
            # Search for JSONL files in directory
            jsonl_files = list(path.glob("*.jsonl"))
            if not jsonl_files:
                jsonl_files = list(path.glob("**/*.jsonl"))

        if not jsonl_files:
            raise FileNotFoundError(f"No JSONL files found in {path}")

        all_articles = []

        for jsonl_file in jsonl_files:
            articles = self._parse_claude_code_jsonl(jsonl_file)
            all_articles.extend(articles)

        if not all_articles:
            return ImportResult(
                success=True,
                results=[],
                summary={"new": 0, "updated": 0, "skipped": 0, "error": 0},
            )

        return await self.import_service.import_batch(all_articles, source=source)

    def _parse_claude_code_jsonl(self, file_path: Path) -> list[ArticleCreate]:
        """Parse Claude Code JSONL file into articles.

        Groups messages into conversations and creates one article per session.
        """
        articles = []
        conversations: dict[str, list[dict]] = {}  # session_id -> messages

        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Skip non-message entries
                entry_type = entry.get("type")
                if entry_type not in ("user", "assistant"):
                    continue

                session_id = entry.get("sessionId", "unknown")
                if session_id not in conversations:
                    conversations[session_id] = []

                # Extract message content
                message = entry.get("message", {})
                role = message.get("role", entry_type)
                content = message.get("content", "")

                # Handle assistant messages with array content
                if isinstance(content, list):
                    text_parts = []
                    for part in content:
                        if isinstance(part, dict):
                            if part.get("type") == "text":
                                text_parts.append(part.get("text", ""))
                            # Skip thinking blocks
                        elif isinstance(part, str):
                            text_parts.append(part)
                    content = "\n".join(text_parts)

                if content:
                    conversations[session_id].append({
                        "role": role,
                        "content": content,
                        "timestamp": entry.get("timestamp"),
                        "cwd": entry.get("cwd"),
                        "git_branch": entry.get("gitBranch"),
                    })

        # Convert conversations to articles
        for session_id, messages in conversations.items():
            if not messages:
                continue

            # Build markdown content
            content_parts = []
            first_timestamp = messages[0].get("timestamp", "")
            cwd = messages[0].get("cwd", "")
            git_branch = messages[0].get("git_branch", "")

            # Add metadata header
            content_parts.append(f"# Claude Code Session\n")
            if cwd:
                content_parts.append(f"**Project**: `{cwd}`\n")
            if git_branch:
                content_parts.append(f"**Branch**: `{git_branch}`\n")
            if first_timestamp:
                content_parts.append(f"**Date**: {first_timestamp[:10]}\n")
            content_parts.append("\n---\n")

            # Add messages
            for msg in messages:
                role_label = "**User**" if msg["role"] == "user" else "**Assistant**"
                content_parts.append(f"\n{role_label}:\n\n{msg['content']}\n")

            content = "\n".join(content_parts)

            # Generate title from first user message
            first_user_msg = next(
                (m["content"] for m in messages if m["role"] == "user"),
                "Chat Session"
            )
            title = first_user_msg[:100].strip()
            if len(first_user_msg) > 100:
                title += "..."

            # Create article
            articles.append(ArticleCreate(
                source_type=SourceType.WEB,  # Use 'web' for now, could add 'chat' type later
                source_id=f"claude-code-{session_id}",
                title=f"[Claude Code] {title}",
                content=content,
                url=None,
                tags=["claude-code", "ai-chat"],
            ))

        return articles

    async def import_cursor(
        self,
        path: str | Path,
        source: str = "cursor",
    ) -> ImportResult:
        """Import Cursor SQLite chat history.

        Args:
            path: Path to Cursor workspaceStorage directory.
            source: Import source identifier.

        Returns:
            ImportResult with statistics.
        """
        path = Path(path).expanduser().resolve()

        # Find state.vscdb files
        vscdb_files = []
        if path.is_file() and path.suffix == ".vscdb":
            vscdb_files = [path]
        elif path.is_dir():
            vscdb_files = list(path.glob("**/state.vscdb"))

        if not vscdb_files:
            raise FileNotFoundError(f"No state.vscdb files found in {path}")

        all_articles = []

        for vscdb_file in vscdb_files:
            try:
                articles = self._parse_cursor_sqlite(vscdb_file)
                all_articles.extend(articles)
            except Exception as e:
                print(f"Error parsing {vscdb_file}: {e}")
                continue

        if not all_articles:
            return ImportResult(
                success=True,
                results=[],
                summary={"new": 0, "updated": 0, "skipped": 0, "error": 0},
            )

        return await self.import_service.import_batch(all_articles, source=source)

    def _parse_cursor_sqlite(self, file_path: Path) -> list[ArticleCreate]:
        """Parse Cursor state.vscdb SQLite file."""
        articles = []

        try:
            conn = sqlite3.connect(str(file_path))
            cursor = conn.cursor()

            # Try to find chat-related tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            # Look for ItemTable which stores VS Code state
            if "ItemTable" in tables:
                cursor.execute("SELECT key, value FROM ItemTable WHERE key LIKE '%chat%' OR key LIKE '%conversation%'")
                rows = cursor.fetchall()

                for key, value in rows:
                    try:
                        data = json.loads(value) if isinstance(value, str) else value
                        # Process chat data based on structure
                        if isinstance(data, dict) and "messages" in data:
                            article = self._cursor_chat_to_article(key, data)
                            if article:
                                articles.append(article)
                    except (json.JSONDecodeError, TypeError):
                        continue

            conn.close()
        except sqlite3.Error as e:
            print(f"SQLite error: {e}")

        return articles

    def _cursor_chat_to_article(self, key: str, data: dict) -> ArticleCreate | None:
        """Convert Cursor chat data to article."""
        messages = data.get("messages", [])
        if not messages:
            return None

        # Build content
        content_parts = ["# Cursor Chat Session\n\n---\n"]

        for msg in messages:
            role = msg.get("role", "unknown")
            text = msg.get("content", msg.get("text", ""))
            if text:
                role_label = "**User**" if role == "user" else "**Assistant**"
                content_parts.append(f"\n{role_label}:\n\n{text}\n")

        content = "\n".join(content_parts)

        # Generate title
        first_user = next(
            (m.get("content", m.get("text", "")) for m in messages if m.get("role") == "user"),
            "Chat"
        )
        title = first_user[:100].strip()

        # Generate unique ID
        source_id = f"cursor-{hashlib.md5(key.encode()).hexdigest()[:16]}"

        return ArticleCreate(
            source_type=SourceType.WEB,
            source_id=source_id,
            title=f"[Cursor] {title}",
            content=content,
            url=None,
            tags=["cursor", "ai-chat"],
        )

    async def import_markdown(
        self,
        content: str,
        title: str | None = None,
        source: str = "markdown",
    ) -> ImportResult:
        """Import markdown-formatted chat content.

        Args:
            content: Markdown content (e.g., copied from chat).
            title: Optional title for the article.
            source: Import source identifier.

        Returns:
            ImportResult with statistics.
        """
        if not content.strip():
            raise ValueError("Content cannot be empty")

        # Generate title if not provided
        if not title:
            # Try to extract from first line or first user message
            lines = content.strip().split("\n")
            first_line = lines[0].strip()
            if first_line.startswith("#"):
                title = first_line.lstrip("#").strip()
            else:
                title = first_line[:100]
                if len(first_line) > 100:
                    title += "..."

        # Generate unique source_id from content hash
        content_hash = hashlib.md5(content.encode()).hexdigest()
        source_id = f"chat-md-{content_hash[:16]}"

        article = ArticleCreate(
            source_type=SourceType.WEB,
            source_id=source_id,
            title=f"[Chat] {title}",
            content=content,
            url=None,
            tags=["ai-chat", "markdown"],
        )

        return await self.import_service.import_batch([article], source=source)

    async def auto_import(
        self,
        path: str | Path,
        source: str = "auto",
    ) -> ImportResult:
        """Auto-detect format and import.

        Args:
            path: Path to file or directory.
            source: Import source identifier.

        Returns:
            ImportResult with statistics.
        """
        path = Path(path).expanduser().resolve()

        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        # Detect format
        if path.is_file():
            if path.suffix == ".jsonl":
                return await self.import_claude_code(path, source or "claude-code")
            elif path.suffix == ".vscdb":
                return await self.import_cursor(path, source or "cursor")
            elif path.suffix in (".md", ".txt"):
                content = path.read_text(encoding="utf-8")
                return await self.import_markdown(content, path.stem, source or "markdown")
        elif path.is_dir():
            # Check for Claude Code project structure
            jsonl_files = list(path.glob("*.jsonl"))
            if jsonl_files:
                return await self.import_claude_code(path, source or "claude-code")

            # Check for Cursor structure
            vscdb_files = list(path.glob("**/state.vscdb"))
            if vscdb_files:
                return await self.import_cursor(path, source or "cursor")

        raise ValueError(f"Could not detect format for: {path}")

    async def get_import_preview(
        self,
        path: str | Path,
    ) -> dict[str, Any]:
        """Preview contents before importing.

        Args:
            path: Path to file or directory.

        Returns:
            Preview information.
        """
        path = Path(path).expanduser().resolve()

        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        preview = {
            "path": str(path),
            "format": "unknown",
            "files": [],
            "total_conversations": 0,
            "sample_titles": [],
        }

        # Detect and preview
        if path.is_file():
            if path.suffix == ".jsonl":
                preview["format"] = "claude-code"
                articles = self._parse_claude_code_jsonl(path)
                preview["files"] = [str(path)]
                preview["total_conversations"] = len(articles)
                preview["sample_titles"] = [a.title for a in articles[:5]]

            elif path.suffix == ".vscdb":
                preview["format"] = "cursor"
                articles = self._parse_cursor_sqlite(path)
                preview["files"] = [str(path)]
                preview["total_conversations"] = len(articles)
                preview["sample_titles"] = [a.title for a in articles[:5]]

            elif path.suffix in (".md", ".txt"):
                preview["format"] = "markdown"
                preview["files"] = [str(path)]
                preview["total_conversations"] = 1

        elif path.is_dir():
            jsonl_files = list(path.glob("*.jsonl"))
            if jsonl_files:
                preview["format"] = "claude-code"
                preview["files"] = [str(f) for f in jsonl_files[:10]]
                total = 0
                titles = []
                for f in jsonl_files[:3]:
                    articles = self._parse_claude_code_jsonl(f)
                    total += len(articles)
                    titles.extend([a.title for a in articles[:2]])
                preview["total_conversations"] = total
                preview["sample_titles"] = titles[:5]

            else:
                vscdb_files = list(path.glob("**/state.vscdb"))
                if vscdb_files:
                    preview["format"] = "cursor"
                    preview["files"] = [str(f) for f in vscdb_files[:10]]

        return preview
