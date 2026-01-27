"""Embedding service for converting text to vectors."""

import asyncio
from typing import Any, Callable

from openai import AsyncOpenAI

from ..config import settings
from ..storage.vector import VectorStore, get_vector_store
from ..storage.database import Database, get_db


class EmbedService:
    """Service for generating and managing text embeddings."""

    # OpenAI embedding dimensions
    MODEL_DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    # Max tokens for embedding models
    MAX_TOKENS = 8191

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        vector_store: VectorStore | None = None,
    ):
        """Initialize the embedding service.

        Args:
            api_key: OpenAI API key. Defaults to settings.openai_api_key.
            model: Embedding model name. Defaults to settings.embedding_model.
            vector_store: VectorStore instance. Defaults to global instance.
        """
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.embedding_model
        self.vector_store = vector_store or get_vector_store()

        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")

        self._client = AsyncOpenAI(api_key=self.api_key)

    @property
    def dimensions(self) -> int:
        """Get the embedding dimensions for the current model."""
        return self.MODEL_DIMENSIONS.get(self.model, 1536)

    async def embed_text(self, text: str) -> list[float]:
        """Convert text to embedding vector.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector as list of floats.
        """
        # Truncate if too long (rough estimate: 4 chars per token)
        max_chars = self.MAX_TOKENS * 4
        if len(text) > max_chars:
            text = text[:max_chars]

        response = await self._client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding

    async def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 100,
    ) -> list[list[float]]:
        """Convert multiple texts to embeddings in batches.

        Args:
            texts: List of texts to embed.
            batch_size: Number of texts per API call (max 2048).

        Returns:
            List of embedding vectors.
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            # Truncate each text if too long
            max_chars = self.MAX_TOKENS * 4
            batch = [t[:max_chars] if len(t) > max_chars else t for t in batch]

            response = await self._client.embeddings.create(
                model=self.model,
                input=batch,
            )

            # Sort by index to maintain order
            sorted_data = sorted(response.data, key=lambda x: x.index)
            all_embeddings.extend([d.embedding for d in sorted_data])

        return all_embeddings

    def chunk_content(
        self,
        content: str,
        max_tokens: int = 8000,
        overlap_tokens: int = 200,
    ) -> list[str]:
        """Split long content into chunks suitable for embedding.

        Args:
            content: Content to split.
            max_tokens: Maximum tokens per chunk.
            overlap_tokens: Number of tokens to overlap between chunks.

        Returns:
            List of content chunks.
        """
        # Rough estimate: 4 chars per token
        max_chars = max_tokens * 4
        overlap_chars = overlap_tokens * 4

        if len(content) <= max_chars:
            return [content]

        chunks = []
        start = 0

        while start < len(content):
            end = start + max_chars

            # Try to break at a paragraph or sentence boundary
            if end < len(content):
                # Look for paragraph break
                para_break = content.rfind("\n\n", start, end)
                if para_break > start + max_chars // 2:
                    end = para_break + 2
                else:
                    # Look for sentence break
                    for sep in [". ", "。", "! ", "? "]:
                        sent_break = content.rfind(sep, start, end)
                        if sent_break > start + max_chars // 2:
                            end = sent_break + len(sep)
                            break

            chunks.append(content[start:end].strip())
            start = end - overlap_chars

        return [c for c in chunks if c]  # Remove empty chunks

    async def embed_article(
        self,
        article_id: int,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Embed an article and store in vector database.

        Args:
            article_id: Article ID from SQLite.
            title: Article title.
            content: Article content in markdown.
            metadata: Additional metadata to store.

        Returns:
            True if successful, False otherwise.
        """
        # Combine title and content for embedding
        text = f"{title}\n\n{content}"

        # Generate embedding
        embedding = await self.embed_text(text)

        # Prepare metadata
        meta = metadata.copy() if metadata else {}
        meta["title"] = title

        # Store in vector database
        self.vector_store.add(
            article_id=article_id,
            embedding=embedding,
            metadata=meta,
            document=text[:1000],  # Store first 1000 chars for retrieval
        )

        return True

    async def embed_articles_batch(
        self,
        articles: list[dict[str, Any]],
        on_progress: Callable | None = None,
    ) -> dict[str, int]:
        """Embed multiple articles in batch.

        Args:
            articles: List of article dicts with id, title, content, and optional metadata.
            on_progress: Optional callback(current, total) for progress updates.

        Returns:
            Dict with success, skipped, and error counts.
        """
        results = {"success": 0, "skipped": 0, "error": 0}
        total = len(articles)

        # Prepare texts
        texts = []
        valid_articles = []
        for article in articles:
            if not article.get("content"):
                results["skipped"] += 1
                continue
            text = f"{article.get('title', '')}\n\n{article['content']}"
            texts.append(text)
            valid_articles.append(article)

        if not texts:
            return results

        # Generate embeddings in batch
        try:
            embeddings = await self.embed_batch(texts)
        except Exception as e:
            results["error"] = len(texts)
            raise e

        # Store embeddings
        article_ids = []
        metadatas = []
        documents = []

        for i, article in enumerate(valid_articles):
            article_ids.append(article["id"])
            meta = {
                "title": article.get("title", ""),
                "source_type": article.get("source_type", ""),
                "tags": article.get("tags", []),
            }
            metadatas.append(meta)
            documents.append(texts[i][:1000])

            if on_progress:
                on_progress(i + 1, total)

        self.vector_store.add_batch(
            article_ids=article_ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )

        results["success"] = len(valid_articles)
        return results

    async def search_similar(
        self,
        query: str,
        n_results: int = 5,
        threshold: float = 0.0,
        source_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar articles using semantic search.

        Args:
            query: Search query text.
            n_results: Number of results to return.
            threshold: Minimum similarity threshold (0-1).
            source_type: Optional filter by source type.

        Returns:
            List of results with article_id, similarity, and metadata.
        """
        # Generate query embedding
        query_embedding = await self.embed_text(query)

        # Build filter
        where = None
        if source_type:
            where = {"source_type": source_type}

        # Query vector store
        results = self.vector_store.query(
            embedding=query_embedding,
            n_results=n_results,
            where=where,
            include_documents=True,
        )

        # Filter by threshold
        if threshold > 0:
            results = [r for r in results if r["similarity"] >= threshold]

        return results

    def is_embedded(self, article_id: int) -> bool:
        """Check if an article has been embedded.

        Args:
            article_id: Article ID to check.

        Returns:
            True if embedded, False otherwise.
        """
        return self.vector_store.exists(article_id)

    def delete_embedding(self, article_id: int) -> None:
        """Delete an article's embedding.

        Args:
            article_id: Article ID to delete.
        """
        self.vector_store.delete(article_id)


# Factory function for creating embed service
def create_embed_service(
    api_key: str | None = None,
    model: str | None = None,
) -> EmbedService:
    """Create an embed service instance.

    Args:
        api_key: Optional OpenAI API key.
        model: Optional embedding model name.

    Returns:
        EmbedService instance.
    """
    return EmbedService(api_key=api_key, model=model)
