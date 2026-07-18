"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from .api.articles import router as articles_router
from .api.auth import verify_api_key
from .api.chat import router as chat_router
from .api.errors import (
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from .api.import_api import router as import_router
from .api.providers import router as providers_router
from .api.scheduler import router as scheduler_router
from .api.search import router as search_router
from .api.sync import router as sync_router
from .config import settings
from .services.scheduler_service import stop_scheduler
from .storage.database import close_db, get_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    settings.ensure_data_dir()
    await init_db()
    print("Starting Knowledge Platform Server v0.1.0")
    print(f"Environment: {settings.environment}")
    if settings.is_production:
        print("Database: [hidden in production]")
    else:
        print(f"Database: {settings.database_path}")
        print(f"Debug mode: {settings.debug}")
        print(f"API docs: http://{settings.host}:{settings.port}/docs")
    print("Scheduler: Use POST /api/v1/scheduler/start to enable")
    yield
    # Shutdown
    await stop_scheduler()
    await close_db()
    print("Shutting down...")


# Hide API schema/docs endpoints in production
app = FastAPI(
    title="Knowledge Platform API",
    description="個人知識管理平台 API - 整合多種來源的技術文章與筆記",
    version="0.1.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
    lifespan=lifespan,
)

# Exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# CORS middleware for extension
# allow_origins does exact string matching only, so wildcard entries like
# "chrome-extension://*" never match a real Origin; patterns must go through
# allow_origin_regex instead.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=(
        r"^(chrome-extension://.+"
        r"|https?://localhost(:\d+)?"
        r"|https?://127\.0\.0\.1(:\d+)?)$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (all behind API key auth; health endpoints below stay open)
protected = [Depends(verify_api_key)]
app.include_router(articles_router, prefix="/api/v1", dependencies=protected)
app.include_router(import_router, prefix="/api/v1", dependencies=protected)
app.include_router(search_router, prefix="/api/v1", dependencies=protected)
app.include_router(sync_router, prefix="/api/v1", dependencies=protected)
app.include_router(chat_router, prefix="/api/v1", dependencies=protected)
app.include_router(scheduler_router, prefix="/api/v1", dependencies=protected)
# Already has /api/v1/providers prefix
app.include_router(providers_router, dependencies=protected)


@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint.

    Returns simple status for basic alive check.
    """
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/v1/health/ready", tags=["Health"])
async def readiness_check():
    """Readiness check endpoint.

    Verifies that the service is ready to accept traffic:
    - Database connection is active
    - ChromaDB is accessible

    Used by orchestrators (Zeabur, K8s) to determine if traffic should be routed.
    """
    from .storage.vector import get_vector_store

    checks = {
        "database": {"status": "unknown", "message": ""},
        "chromadb": {"status": "unknown", "message": ""},
    }
    all_ready = True

    # Check database connection
    try:
        db = await get_db()
        result = await db.fetchone("SELECT 1 as ping")
        if result and result["ping"] == 1:
            checks["database"]["status"] = "ok"
            checks["database"]["message"] = "Connected"
        else:
            checks["database"]["status"] = "error"
            checks["database"]["message"] = "Query failed"
            all_ready = False
    except Exception as e:
        checks["database"]["status"] = "error"
        checks["database"]["message"] = str(e)
        all_ready = False

    # Check ChromaDB
    try:
        vector_store = get_vector_store()
        count = vector_store.count()
        checks["chromadb"]["status"] = "ok"
        checks["chromadb"]["message"] = f"Connected, {count} embeddings"
    except Exception as e:
        checks["chromadb"]["status"] = "error"
        checks["chromadb"]["message"] = str(e)
        all_ready = False

    status_code = 200 if all_ready else 503

    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_ready else "not_ready",
            "checks": checks,
        }
    )


@app.get("/api/v1/health/live", tags=["Health"])
async def liveness_check():
    """Liveness check endpoint.

    Simple check to verify the process is running and responding.
    Used by orchestrators to determine if the container should be restarted.

    This should always succeed if the server is running.
    """
    import time
    return {
        "status": "alive",
        "timestamp": int(time.time()),
    }


@app.get("/api/v1/stats", tags=["System"], dependencies=protected)
async def get_stats():
    """Get system statistics."""
    import os

    db = await get_db()

    # Get article counts
    article_result = await db.fetchone(
        "SELECT COUNT(*) as total, SUM(CASE WHEN is_embedded THEN 1 ELSE 0 END) as embedded FROM articles"
    )

    # Get conversation count
    conv_result = await db.fetchone("SELECT COUNT(*) as total FROM conversations")

    # Get database size
    db_size = "N/A"
    if os.path.exists(settings.database_path):
        size_bytes = os.path.getsize(settings.database_path)
        if size_bytes < 1024:
            db_size = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            db_size = f"{size_bytes / 1024:.1f} KB"
        else:
            db_size = f"{size_bytes / (1024 * 1024):.1f} MB"

    stats = {
        "status": "ok",
        "articles_count": article_result["total"] if article_result else 0,
        "embedded_count": article_result["embedded"] if article_result else 0,
        "conversations_count": conv_result["total"] if conv_result else 0,
        "database_size": db_size,
    }
    # Expose filesystem path only outside production
    if not settings.is_production:
        stats["database_path"] = settings.database_path
    return stats


def run():
    """Run the server using uvicorn."""
    import uvicorn

    uvicorn.run(
        "packages.server.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run()
