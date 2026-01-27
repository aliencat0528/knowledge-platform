#!/usr/bin/env python3
"""Batch embedding script for vectorizing all articles."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add packages/server to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.server.config import settings
from packages.server.storage.database import Database


async def get_unembedded_articles(
    db: Database,
    limit: int | None = None,
    force: bool = False,
) -> list[dict]:
    """Get articles that haven't been embedded yet.

    Args:
        db: Database instance.
        limit: Maximum number of articles to return.
        force: If True, return all articles (including already embedded).

    Returns:
        List of article dicts.
    """
    query = "SELECT * FROM articles"
    if not force:
        query += " WHERE is_embedded = 0 OR is_embedded IS NULL"
    query += " ORDER BY created_at DESC"

    if limit:
        query += f" LIMIT {limit}"

    return await db.fetchall(query)


async def mark_as_embedded(db: Database, article_ids: list[int]) -> None:
    """Mark articles as embedded in the database.

    Args:
        db: Database instance.
        article_ids: List of article IDs to mark.
    """
    if not article_ids:
        return

    placeholders = ",".join(["?" for _ in article_ids])
    await db.execute(
        f"UPDATE articles SET is_embedded = 1 WHERE id IN ({placeholders})",
        tuple(article_ids),
    )
    await db.commit()


async def embed_articles(
    articles: list[dict],
    preview: bool = False,
    batch_size: int = 50,
) -> dict:
    """Embed articles and store in vector database.

    Args:
        articles: List of article dicts.
        preview: If True, only show what would be embedded.
        batch_size: Number of articles to embed per batch.

    Returns:
        Dict with success, error counts.
    """
    from packages.server.services.embed_service import EmbedService
    from packages.server.storage.vector import get_vector_store

    results = {"success": 0, "error": 0, "total": len(articles)}

    if preview:
        print(f"\n[Preview Mode] Would embed {len(articles)} articles:\n")
        for i, article in enumerate(articles[:10], 1):
            tags = []
            if article.get("tags"):
                try:
                    tags = json.loads(article["tags"])
                except (json.JSONDecodeError, TypeError):
                    pass
            print(f"  {i}. [{article['id']}] {article['title'][:60]}...")
            print(f"      Source: {article['source_type']}, Tags: {tags}")
        if len(articles) > 10:
            print(f"  ... and {len(articles) - 10} more")
        return results

    # Initialize services
    try:
        embed_service = EmbedService()
    except ValueError as e:
        print(f"Error: {e}")
        print("Please set OPENAI_API_KEY environment variable.")
        return results

    vector_store = get_vector_store()

    print(f"\nEmbedding {len(articles)} articles...\n")

    # Process in batches
    for i in range(0, len(articles), batch_size):
        batch = articles[i : i + batch_size]
        batch_start = i + 1
        batch_end = min(i + batch_size, len(articles))

        print(f"Processing batch {batch_start}-{batch_end} of {len(articles)}...")

        # Prepare texts
        texts = []
        valid_articles = []
        for article in batch:
            if not article.get("content"):
                results["error"] += 1
                continue
            text = f"{article.get('title', '')}\n\n{article['content']}"
            texts.append(text)
            valid_articles.append(article)

        if not texts:
            continue

        try:
            # Generate embeddings
            embeddings = await embed_service.embed_batch(texts)

            # Prepare data for vector store
            article_ids = []
            metadatas = []
            documents = []

            for j, article in enumerate(valid_articles):
                article_ids.append(article["id"])

                tags = []
                if article.get("tags"):
                    try:
                        tags = json.loads(article["tags"])
                    except (json.JSONDecodeError, TypeError):
                        pass

                metadatas.append({
                    "title": article.get("title", ""),
                    "source_type": article.get("source_type", ""),
                    "tags": tags,
                })
                documents.append(texts[j][:1000])

            # Store in vector database
            vector_store.add_batch(
                article_ids=article_ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents,
            )

            results["success"] += len(valid_articles)

            # Yield for progress
            print(f"  Embedded {len(valid_articles)} articles")

        except Exception as e:
            print(f"  Error processing batch: {e}")
            results["error"] += len(batch)

    return results


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Batch embed all articles in the knowledge base",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview mode: show what would be embedded without actually doing it",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-embed all articles, including those already embedded",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of articles to embed",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of articles per embedding API call (default: 50)",
    )

    args = parser.parse_args()

    # Initialize database
    db = Database()
    await db.connect()

    try:
        # Get articles to embed
        articles = await get_unembedded_articles(
            db,
            limit=args.limit,
            force=args.force,
        )

        if not articles:
            print("No articles to embed.")
            if not args.force:
                print("Use --force to re-embed already embedded articles.")
            return

        print(f"Found {len(articles)} articles to embed")

        # Check vector store stats
        if not args.preview:
            from packages.server.storage.vector import get_vector_store
            vector_store = get_vector_store()
            print(f"Current vector store count: {vector_store.count()}")

        # Embed articles
        results = await embed_articles(
            articles,
            preview=args.preview,
            batch_size=args.batch_size,
        )

        # Update database
        if not args.preview and results["success"] > 0:
            embedded_ids = [a["id"] for a in articles[: results["success"]]]
            await mark_as_embedded(db, embedded_ids)
            print(f"\nMarked {len(embedded_ids)} articles as embedded in database")

        # Print summary
        print("\n" + "=" * 50)
        print("Summary:")
        print(f"  Total articles:  {results['total']}")
        print(f"  Successful:      {results['success']}")
        print(f"  Errors:          {results['error']}")

        if not args.preview:
            from packages.server.storage.vector import get_vector_store
            vector_store = get_vector_store()
            print(f"\nVector store now contains: {vector_store.count()} embeddings")

    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
