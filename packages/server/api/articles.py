"""Articles API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Any

from ..storage.database import Database, get_db
from ..storage.models import (
    ArticleCreate,
    ArticleBatchCreate,
    ArticleTreeCreate,
    ArticleResponse,
    ArticleListResponse,
    ImportResult,
    TreeImportResult,
    SourceType,
)
from ..services.import_service import ImportService

router = APIRouter(prefix="/articles", tags=["Articles"])


@router.post("", response_model=ImportResult, summary="Create a single article")
async def create_article(
    article: ArticleCreate,
    db: Database = Depends(get_db),
) -> ImportResult:
    """Create or update a single article.

    - If article doesn't exist: creates new (status: new)
    - If article exists with same content: skips (status: skipped)
    - If article exists with different content: updates (status: updated)
    """
    service = ImportService(db)
    result = await service.import_article(article)
    return ImportResult(
        success=True,
        results=[result],
        summary={result.status.value: 1},
    )


@router.post("/batch", response_model=ImportResult, summary="Create multiple articles")
async def create_articles_batch(
    batch: ArticleBatchCreate,
    db: Database = Depends(get_db),
) -> ImportResult:
    """Create or update multiple articles in batch.

    Each article is processed with the same deduplication logic.
    Returns summary with counts for new, updated, skipped, and error.
    """
    service = ImportService(db)
    return await service.import_batch(batch.articles, source="api")


@router.post("/tree", response_model=TreeImportResult, summary="Create article tree")
async def create_article_tree(
    tree: ArticleTreeCreate,
    db: Database = Depends(get_db),
) -> TreeImportResult:
    """Create article tree with parent-child hierarchy.

    Used for importing Notion pages with sub-pages.
    Preserves hierarchy in article_hierarchy table.
    """
    service = ImportService(db)
    return await service.import_tree(tree.root, source="api")


@router.get("", response_model=ArticleListResponse, summary="List articles")
async def list_articles(
    source_type: SourceType | None = None,
    q: str | None = Query(None, description="Search in title"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Database = Depends(get_db),
) -> ArticleListResponse:
    """List articles with optional filtering.

    - Filter by source_type
    - Search by title (partial match)
    - Paginated results
    """
    # Build query
    conditions = []
    params: list[Any] = []

    if source_type:
        conditions.append("source_type = ?")
        params.append(source_type.value)

    if q:
        conditions.append("title LIKE ?")
        params.append(f"%{q}%")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Get total count
    count_result = await db.fetchone(
        f"SELECT COUNT(*) as total FROM articles {where_clause}",
        tuple(params),
    )
    total = count_result["total"] if count_result else 0

    # Get articles
    params.extend([limit, offset])
    rows = await db.fetchall(
        f"""
        SELECT * FROM articles
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        tuple(params),
    )

    # Convert to response models
    articles = [_row_to_article(row) for row in rows]

    return ArticleListResponse(
        data=articles,
        meta={
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(articles) < total,
        },
    )


@router.get("/{article_id}", response_model=ArticleResponse, summary="Get article by ID")
async def get_article(
    article_id: int,
    db: Database = Depends(get_db),
) -> ArticleResponse:
    """Get a single article by ID."""
    row = await db.fetchone(
        "SELECT * FROM articles WHERE id = ?",
        (article_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail=f"Article {article_id} not found")

    return _row_to_article(row)


@router.delete("/{article_id}", summary="Delete article")
async def delete_article(
    article_id: int,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    """Delete an article by ID."""
    # Check exists
    existing = await db.fetchone(
        "SELECT id FROM articles WHERE id = ?",
        (article_id,),
    )
    if not existing:
        raise HTTPException(status_code=404, detail=f"Article {article_id} not found")

    # Delete (cascade will handle history and hierarchy)
    await db.execute("DELETE FROM articles WHERE id = ?", (article_id,))
    await db.commit()

    return {"success": True, "message": f"Article {article_id} deleted"}


def _row_to_article(row: dict[str, Any]) -> ArticleResponse:
    """Convert database row to ArticleResponse."""
    import json
    from datetime import datetime

    tags = []
    if row.get("tags"):
        try:
            tags = json.loads(row["tags"])
        except (json.JSONDecodeError, TypeError):
            tags = []

    return ArticleResponse(
        id=row["id"],
        source_type=row["source_type"],
        source_id=row["source_id"],
        title=row["title"],
        content=row["content"],
        content_hash=row["content_hash"],
        url=row.get("url"),
        author=row.get("author"),
        published_at=datetime.fromisoformat(row["published_at"])
        if row.get("published_at")
        else None,
        tags=tags,
        notion_page_id=row.get("notion_page_id"),
        notion_synced_at=datetime.fromisoformat(row["notion_synced_at"])
        if row.get("notion_synced_at")
        else None,
        is_embedded=bool(row.get("is_embedded")),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        version=row.get("version", 1),
    )
