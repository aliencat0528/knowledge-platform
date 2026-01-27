"""Chat service with RAG (Retrieval-Augmented Generation)."""

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from openai import AsyncOpenAI

from ..config import settings
from ..storage.database import Database
from .embed_service import EmbedService

logger = logging.getLogger(__name__)


class ChatServiceError(Exception):
    """Exception raised when chat service fails."""

    def __init__(self, message: str, code: str = "CHAT_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


# System prompt for RAG
SYSTEM_PROMPT = """你是一個知識管理助手，專門幫助用戶查找和理解他們收藏的技術文章。

你的回答應該：
1. 基於提供的上下文內容回答問題
2. 如果上下文中沒有相關資訊，誠實說明
3. 引用來源時標註文章標題
4. 使用繁體中文回答
5. 保持回答簡潔、準確、有幫助

上下文格式：
每個文章會以 [文章標題] 開頭，後面是內容片段。
"""


class ChatService:
    """Service for RAG-based chat with knowledge base."""

    # Default settings
    DEFAULT_MODEL = "gpt-4o-mini"
    DEFAULT_MAX_TOKENS = 2000
    DEFAULT_TEMPERATURE = 0.7
    MAX_CONTEXT_ARTICLES = 5
    MAX_CONTEXT_LENGTH = 8000  # Characters

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        embed_service: EmbedService | None = None,
    ):
        """Initialize chat service.

        Args:
            api_key: OpenAI API key. Defaults to settings.openai_api_key.
            model: LLM model name. Defaults to settings.llm_model.
            embed_service: EmbedService for semantic search. Creates new if None.

        Raises:
            ValueError: If API key is not configured.
        """
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.llm_model or self.DEFAULT_MODEL

        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable."
            )

        self._client = AsyncOpenAI(api_key=self.api_key)
        self._embed_service = embed_service

    def _get_embed_service(self) -> EmbedService:
        """Get or create embed service."""
        if self._embed_service is None:
            self._embed_service = EmbedService(api_key=self.api_key)
        return self._embed_service

    async def search_context(
        self,
        query: str,
        db: Database,
        limit: int = MAX_CONTEXT_ARTICLES,
        threshold: float = 0.3,
    ) -> list[dict[str, Any]]:
        """Search for relevant context from knowledge base.

        Args:
            query: User question.
            db: Database connection.
            limit: Maximum number of articles to retrieve.
            threshold: Minimum similarity threshold.

        Returns:
            List of relevant articles with content.
        """
        embed_service = self._get_embed_service()

        # Semantic search
        results = await embed_service.search_similar(
            query=query,
            n_results=limit,
            threshold=threshold,
        )

        # Fetch full article details
        context = []
        for r in results:
            article_id = r.get("article_id")
            if not article_id:
                continue

            row = await db.fetchone(
                "SELECT id, title, content, url, source_type FROM articles WHERE id = ?",
                (article_id,),
            )
            if not row:
                continue

            context.append({
                "id": row["id"],
                "title": row["title"],
                "content": row["content"],
                "url": row.get("url"),
                "source_type": row["source_type"],
                "similarity": r.get("similarity", 0),
            })

        return context

    def build_context_prompt(
        self,
        context: list[dict[str, Any]],
        max_length: int = MAX_CONTEXT_LENGTH,
    ) -> str:
        """Build context string from retrieved articles.

        Args:
            context: List of article dicts.
            max_length: Maximum context length in characters.

        Returns:
            Formatted context string.
        """
        if not context:
            return "（沒有找到相關文章）"

        context_parts = []
        total_length = 0

        for article in context:
            title = article.get("title", "無標題")
            content = article.get("content", "")

            # Truncate content if needed
            remaining_space = max_length - total_length - len(title) - 20
            if remaining_space <= 100:
                break

            if len(content) > remaining_space:
                content = content[:remaining_space] + "..."

            part = f"[{title}]\n{content}\n"
            context_parts.append(part)
            total_length += len(part)

        return "\n---\n".join(context_parts)

    async def chat(
        self,
        query: str,
        db: Database,
        conversation_id: str | None = None,
        max_context: int = MAX_CONTEXT_ARTICLES,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> dict[str, Any]:
        """Execute RAG chat.

        Args:
            query: User question.
            db: Database connection.
            conversation_id: Optional conversation ID for multi-turn chat.
            max_context: Maximum number of context articles.
            temperature: LLM temperature.
            max_tokens: Maximum response tokens.

        Returns:
            Dict with answer, sources, usage, and conversation_id.
        """
        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        # Search for relevant context
        context = await self.search_context(query, db, limit=max_context)

        # Build context prompt
        context_prompt = self.build_context_prompt(context)

        # Build messages
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"根據以下知識庫內容回答問題：\n\n{context_prompt}\n\n問題：{query}",
            },
        ]

        # Load conversation history if exists
        history = await self._load_conversation_history(db, conversation_id)
        if history:
            # Insert history between system and current user message
            messages = (
                [messages[0]]
                + history
                + [messages[1]]
            )

        # Call LLM
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise ChatServiceError(
                f"Failed to generate response: {str(e)}",
                code="LLM_ERROR",
            )

        answer = response.choices[0].message.content or ""
        usage = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens": response.usage.total_tokens if response.usage else 0,
        }

        # Build sources list
        sources = [
            {
                "id": c["id"],
                "title": c["title"],
                "url": c.get("url"),
                "snippet": c["content"][:200] + "..." if len(c["content"]) > 200 else c["content"],
                "similarity": round(c.get("similarity", 0), 4),
            }
            for c in context
        ]

        # Save to conversation history
        await self._save_message(db, conversation_id, "user", query)
        await self._save_message(db, conversation_id, "assistant", answer, sources)

        return {
            "answer": answer,
            "sources": sources,
            "conversation_id": conversation_id,
            "usage": usage,
        }

    async def _load_conversation_history(
        self,
        db: Database,
        conversation_id: str,
        max_turns: int = 5,
    ) -> list[dict[str, str]]:
        """Load conversation history from database.

        Args:
            db: Database connection.
            conversation_id: Conversation ID.
            max_turns: Maximum number of turns to load.

        Returns:
            List of messages in OpenAI format.
        """
        rows = await db.fetchall(
            """
            SELECT role, content FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (conversation_id, max_turns * 2),
        )

        if not rows:
            return []

        # Reverse to get chronological order
        messages = []
        for row in reversed(rows):
            messages.append({
                "role": row["role"],
                "content": row["content"],
            })

        return messages

    async def _save_message(
        self,
        db: Database,
        conversation_id: str,
        role: str,
        content: str,
        sources: list[dict] | None = None,
    ) -> None:
        """Save a message to conversation history.

        Args:
            db: Database connection.
            conversation_id: Conversation ID.
            role: Message role (user/assistant).
            content: Message content.
            sources: Optional sources for assistant messages.
        """
        # Ensure conversation exists
        await db.execute(
            """
            INSERT OR IGNORE INTO conversations (id, title, created_at, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (conversation_id, content[:50] + "..." if len(content) > 50 else content),
        )

        # Update conversation timestamp
        await db.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,),
        )

        # Insert message
        sources_json = json.dumps(sources) if sources else None
        await db.execute(
            """
            INSERT INTO messages (conversation_id, role, content, sources)
            VALUES (?, ?, ?, ?)
            """,
            (conversation_id, role, content, sources_json),
        )

        await db.commit()

    async def get_conversation(
        self,
        db: Database,
        conversation_id: str,
    ) -> dict[str, Any] | None:
        """Get a conversation with all messages.

        Args:
            db: Database connection.
            conversation_id: Conversation ID.

        Returns:
            Conversation dict with messages, or None if not found.
        """
        conv = await db.fetchone(
            "SELECT * FROM conversations WHERE id = ?",
            (conversation_id,),
        )

        if not conv:
            return None

        messages = await db.fetchall(
            """
            SELECT id, role, content, sources, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            """,
            (conversation_id,),
        )

        return {
            "id": conv["id"],
            "title": conv["title"],
            "created_at": conv["created_at"],
            "updated_at": conv["updated_at"],
            "messages": [
                {
                    "id": m["id"],
                    "role": m["role"],
                    "content": m["content"],
                    "sources": json.loads(m["sources"]) if m["sources"] else None,
                    "created_at": m["created_at"],
                }
                for m in messages
            ],
        }

    async def list_conversations(
        self,
        db: Database,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List all conversations.

        Args:
            db: Database connection.
            limit: Maximum number of conversations.
            offset: Offset for pagination.

        Returns:
            List of conversation summaries.
        """
        rows = await db.fetchall(
            """
            SELECT c.id, c.title, c.created_at, c.updated_at,
                   COUNT(m.id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.id = m.conversation_id
            GROUP BY c.id
            ORDER BY c.updated_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )

        return [
            {
                "id": row["id"],
                "title": row["title"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "message_count": row["message_count"],
            }
            for row in rows
        ]

    async def delete_conversation(
        self,
        db: Database,
        conversation_id: str,
    ) -> bool:
        """Delete a conversation and all its messages.

        Args:
            db: Database connection.
            conversation_id: Conversation ID.

        Returns:
            True if deleted, False if not found.
        """
        result = await db.fetchone(
            "SELECT id FROM conversations WHERE id = ?",
            (conversation_id,),
        )

        if not result:
            return False

        # Delete messages first (FK cascade should handle this, but explicit is safer)
        await db.execute(
            "DELETE FROM messages WHERE conversation_id = ?",
            (conversation_id,),
        )

        # Delete conversation
        await db.execute(
            "DELETE FROM conversations WHERE id = ?",
            (conversation_id,),
        )

        await db.commit()
        return True


# Factory function
def create_chat_service(
    api_key: str | None = None,
    model: str | None = None,
) -> ChatService:
    """Create a chat service instance.

    Args:
        api_key: Optional OpenAI API key.
        model: Optional LLM model name.

    Returns:
        ChatService instance.
    """
    return ChatService(api_key=api_key, model=model)
