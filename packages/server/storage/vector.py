"""ChromaDB vector storage for semantic search."""

import chromadb
from chromadb.config import Settings as ChromaSettings
from pathlib import Path
from typing import Any

from ..config import settings


class VectorStore:
    """ChromaDB vector store wrapper for article embeddings."""

    COLLECTION_NAME = "knowledge_articles"

    def __init__(self, path: str | None = None):
        """Initialize ChromaDB client with persistent storage.

        Args:
            path: Path to ChromaDB storage directory. Defaults to settings.chroma_path.
        """
        self.path = path or settings.chroma_path
        self._client: chromadb.PersistentClient | None = None
        self._collection: chromadb.Collection | None = None

    def _ensure_dir(self) -> None:
        """Ensure storage directory exists."""
        Path(self.path).mkdir(parents=True, exist_ok=True)

    @property
    def client(self) -> chromadb.PersistentClient:
        """Get or create ChromaDB client."""
        if self._client is None:
            self._ensure_dir()
            self._client = chromadb.PersistentClient(
                path=self.path,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
        return self._client

    @property
    def collection(self) -> chromadb.Collection:
        """Get or create the articles collection."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},  # Use cosine similarity
            )
        return self._collection

    def add(
        self,
        article_id: int,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
        document: str | None = None,
    ) -> None:
        """Add an article embedding to the collection.

        Args:
            article_id: The article ID from SQLite.
            embedding: The embedding vector.
            metadata: Optional metadata (title, source_type, tags, etc.).
            document: Optional document text for retrieval.
        """
        doc_id = f"article_{article_id}"

        # Prepare metadata
        meta = metadata.copy() if metadata else {}
        meta["article_id"] = article_id

        # Convert list fields to strings for ChromaDB
        if "tags" in meta and isinstance(meta["tags"], list):
            meta["tags"] = ",".join(meta["tags"])

        self.collection.upsert(
            ids=[doc_id],
            embeddings=[embedding],
            metadatas=[meta] if meta else None,
            documents=[document] if document else None,
        )

    def add_batch(
        self,
        article_ids: list[int],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
        documents: list[str] | None = None,
    ) -> None:
        """Add multiple article embeddings in batch.

        Args:
            article_ids: List of article IDs.
            embeddings: List of embedding vectors.
            metadatas: Optional list of metadata dicts.
            documents: Optional list of document texts.
        """
        doc_ids = [f"article_{aid}" for aid in article_ids]

        # Prepare metadatas
        if metadatas:
            processed_metas = []
            for i, meta in enumerate(metadatas):
                m = meta.copy() if meta else {}
                m["article_id"] = article_ids[i]
                # Convert list fields to strings
                if "tags" in m and isinstance(m["tags"], list):
                    m["tags"] = ",".join(m["tags"])
                processed_metas.append(m)
        else:
            processed_metas = [{"article_id": aid} for aid in article_ids]

        self.collection.upsert(
            ids=doc_ids,
            embeddings=embeddings,
            metadatas=processed_metas,
            documents=documents,
        )

    def query(
        self,
        embedding: list[float],
        n_results: int = 5,
        where: dict[str, Any] | None = None,
        include_documents: bool = False,
    ) -> list[dict[str, Any]]:
        """Query for similar articles.

        Args:
            embedding: Query embedding vector.
            n_results: Number of results to return.
            where: Optional filter conditions.
            include_documents: Whether to include document text.

        Returns:
            List of results with id, article_id, similarity, and metadata.
        """
        include = ["metadatas", "distances"]
        if include_documents:
            include.append("documents")

        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            where=where,
            include=include,
        )

        # Format results
        formatted = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                result = {
                    "id": doc_id,
                    "article_id": results["metadatas"][0][i].get("article_id"),
                    # Convert distance to similarity (cosine distance -> similarity)
                    "similarity": 1 - results["distances"][0][i],
                    "metadata": results["metadatas"][0][i],
                }
                if include_documents and results.get("documents"):
                    result["document"] = results["documents"][0][i]
                formatted.append(result)

        return formatted

    def delete(self, article_id: int) -> None:
        """Delete an article's embedding.

        Args:
            article_id: The article ID to delete.
        """
        doc_id = f"article_{article_id}"
        self.collection.delete(ids=[doc_id])

    def delete_batch(self, article_ids: list[int]) -> None:
        """Delete multiple article embeddings.

        Args:
            article_ids: List of article IDs to delete.
        """
        doc_ids = [f"article_{aid}" for aid in article_ids]
        self.collection.delete(ids=doc_ids)

    def get(self, article_id: int) -> dict[str, Any] | None:
        """Get an article's embedding and metadata.

        Args:
            article_id: The article ID to retrieve.

        Returns:
            Dict with embedding, metadata, and document, or None if not found.
        """
        doc_id = f"article_{article_id}"
        results = self.collection.get(
            ids=[doc_id],
            include=["embeddings", "metadatas", "documents"],
        )

        if results["ids"]:
            return {
                "id": results["ids"][0],
                "embedding": results["embeddings"][0] if results["embeddings"] else None,
                "metadata": results["metadatas"][0] if results["metadatas"] else None,
                "document": results["documents"][0] if results["documents"] else None,
            }
        return None

    def exists(self, article_id: int) -> bool:
        """Check if an article has an embedding.

        Args:
            article_id: The article ID to check.

        Returns:
            True if embedding exists, False otherwise.
        """
        doc_id = f"article_{article_id}"
        results = self.collection.get(ids=[doc_id])
        return bool(results["ids"])

    def count(self) -> int:
        """Get the total number of embeddings in the collection.

        Returns:
            Number of embeddings.
        """
        return self.collection.count()

    def reset(self) -> None:
        """Reset the collection (delete all embeddings)."""
        self.client.delete_collection(self.COLLECTION_NAME)
        self._collection = None


# Global vector store instance
vector_store = VectorStore()


def get_vector_store() -> VectorStore:
    """Get the global vector store instance."""
    return vector_store
