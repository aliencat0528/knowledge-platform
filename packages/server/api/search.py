"""Search API endpoints."""

from fastapi import APIRouter, Depends, Query
from typing import Any

from ..storage.database import Database, get_db
from ..storage.models import (
    SearchResult,
    SearchResultItem,
    ArticleResponse,
    SourceType,
)

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("", response_model=SearchResult, summary="Keyword search")
async def search_articles(
    q: str = Query(..., min_length=1, description="Search query"),
    source_type: SourceType | None = Query(None, description="Filter by source type"),
    tags: str | None = Query(None, description="Filter by tags (comma-separated)"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Database = Depends(get_db),
) -> SearchResult:
    """Search articles by keyword.

    Searches in title and content fields using SQLite FTS-like matching.
    Supports filtering by source_type and tags.

    Returns:
        SearchResult with matching articles and highlights.
    """
    # Build query conditions
    conditions = []
    params: list[Any] = []

    # Full-text search in title and content
    conditions.append("(title LIKE ? OR content LIKE ?)")
    search_pattern = f"%{q}%"
    params.extend([search_pattern, search_pattern])

    # Optional source_type filter
    if source_type:
        conditions.append("source_type = ?")
        params.append(source_type.value)

    # Optional tags filter (JSON contains)
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        for tag in tag_list:
            # SQLite JSON check
            conditions.append("tags LIKE ?")
            params.append(f'%"{tag}"%')

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Get total count
    count_result = await db.fetchone(
        f"SELECT COUNT(*) as total FROM articles WHERE {where_clause}",
        tuple(params),
    )
    total = count_result["total"] if count_result else 0

    # Get matching articles
    params.extend([limit, offset])
    rows = await db.fetchall(
        f"""
        SELECT * FROM articles
        WHERE {where_clause}
        ORDER BY
            CASE
                WHEN title LIKE ? THEN 0
                ELSE 1
            END,
            created_at DESC
        LIMIT ? OFFSET ?
        """,
        tuple(params[:-2] + [f"%{q}%"] + params[-2:]),
    )

    # Convert to search results with highlights
    results = []
    for row in rows:
        article = _row_to_article(row)

        # Generate highlights (simple snippet around match)
        highlights = _generate_highlights(row["content"], q)

        results.append(
            SearchResultItem(
                article=article,
                score=_calculate_score(row, q),
                highlights=highlights,
            )
        )

    return SearchResult(
        success=True,
        query=q,
        results=results,
        total=total,
        meta={
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(results) < total,
            "filters": {
                "source_type": source_type.value if source_type else None,
                "tags": tags,
            },
        },
    )


def _generate_highlights(content: str, query: str, max_highlights: int = 3) -> list[str]:
    """Generate text snippets around search matches.

    Args:
        content: Full article content.
        query: Search query.
        max_highlights: Maximum number of highlights to return.

    Returns:
        List of text snippets with matches.
    """
    if not content or not query:
        return []

    highlights = []
    content_lower = content.lower()
    query_lower = query.lower()

    # Find positions of query in content
    pos = 0
    while len(highlights) < max_highlights:
        pos = content_lower.find(query_lower, pos)
        if pos == -1:
            break

        # Extract snippet around match (80 chars before and after)
        start = max(0, pos - 80)
        end = min(len(content), pos + len(query) + 80)

        snippet = content[start:end]

        # Add ellipsis if truncated
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        highlights.append(snippet.strip())
        pos += len(query)

    return highlights


def _calculate_score(row: dict, query: str) -> float:
    """Calculate relevance score for a search result.

    Simple scoring based on:
    - Title match (higher weight)
    - Content match count
    - Recency

    Args:
        row: Database row.
        query: Search query.

    Returns:
        Relevance score (0-1).
    """
    score = 0.0
    query_lower = query.lower()

    # Title match (40% weight)
    title = (row.get("title") or "").lower()
    if query_lower in title:
        if title.startswith(query_lower):
            score += 0.4  # Exact prefix match
        else:
            score += 0.3  # Contains match

    # Content match density (40% weight)
    content = (row.get("content") or "").lower()
    if content:
        match_count = content.count(query_lower)
        content_len = len(content)
        if content_len > 0:
            density = min(match_count * 100 / content_len, 1.0)
            score += density * 0.4

    # Base score for any match (20% weight)
    if query_lower in title or query_lower in content:
        score += 0.2

    return round(min(score, 1.0), 3)


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
