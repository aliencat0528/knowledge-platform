"""Pydantic models for API request/response."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, ConfigDict


# Enums
class SourceType(str, Enum):
    """Article source types."""

    NOTION = "notion"
    MEDIUM = "medium"
    DOCS = "docs"
    WEB = "web"


class ImportStatus(str, Enum):
    """Import result status."""

    NEW = "new"
    UPDATED = "updated"
    SKIPPED = "skipped"
    ERROR = "error"


# Base Models
class ArticleBase(BaseModel):
    """Base article model with common fields."""

    source_type: SourceType
    source_id: str = Field(..., min_length=1, description="Unique identifier from source")
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    url: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)


# Request Models
class ArticleCreate(ArticleBase):
    """Model for creating a single article."""

    pass


class ArticleBatchCreate(BaseModel):
    """Model for batch article creation."""

    articles: list[ArticleCreate] = Field(..., min_length=1, max_length=100)


class ArticleTreeNode(ArticleBase):
    """Model for a node in article tree."""

    children: list["ArticleTreeNode"] = Field(default_factory=list)


class ArticleTreeCreate(BaseModel):
    """Model for creating article tree (Notion hierarchy)."""

    root: ArticleTreeNode


class ArticleUpdate(BaseModel):
    """Model for updating an article."""

    title: str | None = None
    content: str | None = None
    url: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    tags: list[str] | None = None


# Response Models
class ArticleResponse(ArticleBase):
    """Model for article response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    content_hash: str
    notion_page_id: str | None = None
    notion_synced_at: datetime | None = None
    is_embedded: bool = False
    created_at: datetime
    updated_at: datetime
    version: int = 1


class ArticleListResponse(BaseModel):
    """Model for paginated article list."""

    success: bool = True
    data: list[ArticleResponse]
    meta: dict[str, Any] = Field(default_factory=dict)


class ImportResultItem(BaseModel):
    """Single item import result."""

    source_id: str
    title: str
    status: ImportStatus
    article_id: int | None = None
    message: str | None = None


class ImportResult(BaseModel):
    """Model for import operation result."""

    success: bool = True
    batch_id: int | None = None
    results: list[ImportResultItem] = Field(default_factory=list)
    summary: dict[str, int] = Field(default_factory=dict)


class TreeImportResult(ImportResult):
    """Model for tree import result with hierarchy info."""

    root_id: int | None = None
    hierarchy_count: int = 0


# Search Models
class SearchQuery(BaseModel):
    """Model for search query."""

    q: str = Field(..., min_length=1, description="Search query")
    source_type: SourceType | None = None
    tags: list[str] | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class SemanticSearchQuery(BaseModel):
    """Model for semantic search query."""

    query: str = Field(..., min_length=1)
    limit: int = Field(default=5, ge=1, le=20)
    threshold: float = Field(default=0.7, ge=0, le=1)


class SearchResultItem(BaseModel):
    """Single search result item."""

    article: ArticleResponse
    score: float | None = None
    highlights: list[str] = Field(default_factory=list)


class SearchResult(BaseModel):
    """Model for search results."""

    success: bool = True
    query: str
    results: list[SearchResultItem]
    total: int
    meta: dict[str, Any] = Field(default_factory=dict)


# Error Models
class ErrorDetail(BaseModel):
    """Error detail model."""

    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    success: bool = False
    error: ErrorDetail


# System Models
class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str


class StatsResponse(BaseModel):
    """System statistics response."""

    status: str = "ok"
    articles_count: int
    embedded_count: int
    database_path: str


# Rebuild forward references for recursive models
ArticleTreeNode.model_rebuild()
