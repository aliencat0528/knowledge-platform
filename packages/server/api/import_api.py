"""Import API endpoints for batch and zip imports."""

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException

from ..storage.database import Database, get_db
from ..storage.models import ImportResult
from ..services.zip_import_service import ZipImportService

router = APIRouter(prefix="/import", tags=["Import"])


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
