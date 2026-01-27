"""Notion sync API endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..config import settings
from ..storage.database import Database, get_db
from ..services.notion_sync import NotionSync, NotionSyncError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])


# Request Models
class SyncArticleRequest(BaseModel):
    """Request model for syncing a single article."""

    article_id: int = Field(..., description="Article ID to sync")


class BatchSyncRequest(BaseModel):
    """Request model for batch syncing articles."""

    article_ids: list[int] | None = Field(
        default=None,
        description="Specific article IDs to sync. If not provided, syncs unsynced articles.",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of articles to sync",
    )


# Response Models
class SyncResultResponse(BaseModel):
    """Response model for sync result."""

    success: bool = True
    article_id: int
    notion_page_id: str
    notion_url: str
    synced_at: str


class SyncStatusResponse(BaseModel):
    """Response model for sync status."""

    success: bool = True
    configured: bool
    total_articles: int
    synced_count: int
    pending_count: int
    recent_syncs: list[dict[str, Any]] = Field(default_factory=list)
    database_id: str | None = None


class BatchSyncResultResponse(BaseModel):
    """Response model for batch sync result."""

    success: bool = True
    total: int
    synced: int
    failed: int
    results: dict[str, Any]


def get_notion_sync() -> NotionSync | None:
    """Get NotionSync instance if configured."""
    if not settings.notion_api_key or not settings.notion_database_id:
        return None
    try:
        return NotionSync()
    except ValueError:
        return None


@router.post("/notion", response_model=SyncResultResponse)
async def sync_to_notion(
    request: SyncArticleRequest,
    db: Database = Depends(get_db),
) -> SyncResultResponse:
    """Sync a single article to Notion.

    Creates a new page in the configured Notion database, or updates
    an existing page if the article was previously synced.

    Requires:
    - NOTION_API_KEY environment variable
    - NOTION_DATABASE_ID environment variable
    - Notion Integration has access to the database
    """
    notion_sync = get_notion_sync()
    if not notion_sync:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "NOTION_NOT_CONFIGURED",
                "message": "Notion API is not configured. Set NOTION_API_KEY and NOTION_DATABASE_ID.",
            },
        )

    try:
        result = await notion_sync.sync_article(db, request.article_id)
        return SyncResultResponse(
            success=True,
            article_id=request.article_id,
            notion_page_id=result["notion_page_id"],
            notion_url=result["notion_url"],
            synced_at=result["synced_at"],
        )
    except NotionSyncError as e:
        logger.error(f"Notion sync failed: {e.message}")
        raise HTTPException(
            status_code=400,
            detail={
                "code": e.code,
                "message": e.message,
            },
        )
    except Exception as e:
        logger.exception("Unexpected error during Notion sync")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": str(e),
            },
        )


@router.post("/notion/batch", response_model=BatchSyncResultResponse)
async def batch_sync_to_notion(
    request: BatchSyncRequest,
    db: Database = Depends(get_db),
) -> BatchSyncResultResponse:
    """Batch sync multiple articles to Notion.

    If article_ids is not provided, syncs unsynced articles up to the limit.
    """
    notion_sync = get_notion_sync()
    if not notion_sync:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "NOTION_NOT_CONFIGURED",
                "message": "Notion API is not configured. Set NOTION_API_KEY and NOTION_DATABASE_ID.",
            },
        )

    try:
        results = await notion_sync.batch_sync(
            db,
            article_ids=request.article_ids,
            limit=request.limit,
        )
        return BatchSyncResultResponse(
            success=True,
            total=results["total"],
            synced=len(results["success"]),
            failed=len(results["failed"]),
            results=results,
        )
    except Exception as e:
        logger.exception("Unexpected error during batch Notion sync")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": str(e),
            },
        )


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(
    db: Database = Depends(get_db),
) -> SyncStatusResponse:
    """Get Notion sync status and statistics.

    Returns:
    - Whether Notion is configured
    - Total articles count
    - Synced and pending counts
    - Recent sync history
    """
    notion_sync = get_notion_sync()

    if not notion_sync:
        # Return basic stats even if Notion is not configured
        total = await db.fetchone("SELECT COUNT(*) as count FROM articles")
        return SyncStatusResponse(
            success=True,
            configured=False,
            total_articles=total["count"] if total else 0,
            synced_count=0,
            pending_count=total["count"] if total else 0,
            database_id=None,
        )

    try:
        status = await notion_sync.get_sync_status(db)
        return SyncStatusResponse(
            success=True,
            configured=True,
            total_articles=status["total_articles"],
            synced_count=status["synced_count"],
            pending_count=status["pending_count"],
            recent_syncs=status["recent_syncs"],
            database_id=status["database_id"],
        )
    except Exception as e:
        logger.exception("Error getting sync status")
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": str(e),
            },
        )


@router.delete("/notion/{article_id}")
async def unsync_article(
    article_id: int,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    """Remove Notion sync info from an article.

    This does NOT delete the Notion page, only removes the local sync reference.
    """
    # Check if article exists
    article = await db.fetchone(
        "SELECT id, notion_page_id FROM articles WHERE id = ?",
        (article_id,),
    )

    if not article:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "ARTICLE_NOT_FOUND",
                "message": f"Article {article_id} not found",
            },
        )

    if not article["notion_page_id"]:
        return {
            "success": True,
            "message": "Article was not synced to Notion",
        }

    # Clear sync info
    await db.execute(
        """
        UPDATE articles
        SET notion_page_id = NULL, notion_synced_at = NULL
        WHERE id = ?
        """,
        (article_id,),
    )
    await db.commit()

    return {
        "success": True,
        "message": "Notion sync info removed",
        "previous_page_id": article["notion_page_id"],
    }
