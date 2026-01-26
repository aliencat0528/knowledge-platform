"""Import API endpoints for batch and zip imports."""

import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Body
from pydantic import BaseModel, Field

from ..storage.database import Database, get_db
from ..storage.models import ImportResult
from ..services.zip_import_service import ZipImportService
from ..services.chat_import_service import ChatImportService

router = APIRouter(prefix="/import", tags=["Import"])


# Request models for chat import
class ChatImportRequest(BaseModel):
    """Request model for chat import."""

    source: Literal["claude-code", "cursor", "markdown", "auto"] = Field(
        default="auto",
        description="Source type: claude-code, cursor, markdown, or auto-detect"
    )
    content: str | None = Field(
        default=None,
        description="Markdown content (required for source='markdown')"
    )
    title: str | None = Field(
        default=None,
        description="Optional title for markdown import"
    )
    path: str | None = Field(
        default=None,
        description="Server-side path to import from (for CLI/local use)"
    )


@router.post("/zip", response_model=ImportResult, summary="Import Notion Export zip file")
async def import_zip_file(
    file: UploadFile = File(..., description="Notion Export .zip file"),
    db: Database = Depends(get_db),
) -> ImportResult:
    """Import articles from a Notion Export .zip file.

    - Extracts all .md and .html files
    - Parses Notion page IDs from filenames
    - Preserves directory structure as hierarchy
    - Applies standard deduplication logic
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="File must be a .zip file"
        )

    # Save to temp file
    try:
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)

        # Import
        service = ZipImportService(db)
        result = await service.import_zip(tmp_path, source="api-upload")

        return result

    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
    finally:
        # Cleanup temp file
        if tmp_path.exists():
            tmp_path.unlink()


@router.post("/zip/preview", summary="Preview zip file contents")
async def preview_zip_file(
    file: UploadFile = File(..., description="Notion Export .zip file"),
    db: Database = Depends(get_db),
) -> dict:
    """Preview contents of a zip file before importing.

    Returns:
    - Total file count
    - List of files with parsed titles and IDs
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="File must be a .zip file"
        )

    try:
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)

        service = ZipImportService(db)
        preview = await service.get_import_preview(tmp_path)

        return {
            "success": True,
            "data": preview,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@router.post("/chat", response_model=ImportResult, summary="Import AI chat conversations")
async def import_chat(
    request: ChatImportRequest,
    db: Database = Depends(get_db),
) -> ImportResult:
    """Import AI editor chat conversations.

    Supported sources:
    - **claude-code**: Claude Code CLI JSONL files (~/.claude/projects/)
    - **cursor**: Cursor AI SQLite database
    - **markdown**: Manually copied chat content
    - **auto**: Auto-detect format from path

    For markdown import, provide `content` field.
    For file-based import, provide `path` field (server-side path).
    """
    service = ChatImportService(db)

    try:
        if request.source == "markdown":
            if not request.content:
                raise HTTPException(
                    status_code=400,
                    detail="Content is required for markdown import"
                )
            return await service.import_markdown(
                content=request.content,
                title=request.title,
                source="api-markdown"
            )

        elif request.path:
            path = Path(request.path).expanduser()

            if not path.exists():
                raise HTTPException(
                    status_code=400,
                    detail=f"Path not found: {request.path}"
                )

            if request.source == "claude-code":
                return await service.import_claude_code(path, source="api-claude-code")
            elif request.source == "cursor":
                return await service.import_cursor(path, source="api-cursor")
            else:  # auto
                return await service.auto_import(path, source="api-auto")

        else:
            raise HTTPException(
                status_code=400,
                detail="Either 'content' (for markdown) or 'path' (for file-based) is required"
            )

    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.post("/chat/preview", summary="Preview chat import")
async def preview_chat_import(
    path: str = Body(..., embed=True, description="Path to preview"),
    db: Database = Depends(get_db),
) -> dict:
    """Preview AI chat files before importing.

    Returns:
    - Detected format
    - File list
    - Total conversation count
    - Sample titles
    """
    service = ChatImportService(db)

    try:
        preview = await service.get_import_preview(path)
        return {
            "success": True,
            "data": preview,
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


@router.get("/chat/sources", summary="List supported chat sources")
async def list_chat_sources() -> dict:
    """List all supported AI chat sources and their details."""
    return {
        "success": True,
        "sources": ChatImportService.SOURCES,
    }
