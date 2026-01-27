"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from .config import settings
from .storage.database import init_db, close_db, get_db
from .api.articles import router as articles_router
from .api.import_api import router as import_router
from .api.search import router as search_router
from .api.sync import router as sync_router
from .api.chat import router as chat_router
from .api.scheduler import router as scheduler_router
from .api.providers import router as providers_router
from .services.scheduler_service import start_scheduler, stop_scheduler
from .api.errors import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    settings.ensure_data_dir()
    await init_db()
    print(f"Starting Knowledge Platform Server v0.1.0")
    print(f"Database: {settings.database_path}")
    print(f"Debug mode: {settings.debug}")
    print(f"API docs: http://{settings.host}:{settings.port}/docs")
    print(f"Scheduler: Use POST /api/v1/scheduler/start to enable")
    yield
    # Shutdown
    await stop_scheduler()
    await close_db()
    print("Shutting down...")


app = FastAPI(
    title="Knowledge Platform API",
    description="個人知識管理平台 API - 整合多種來源的技術文章與筆記",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# CORS middleware for extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "chrome-extension://*",
        "http://localhost:*",
        "http://127.0.0.1:*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(articles_router, prefix="/api/v1")
app.include_router(import_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")
app.include_router(sync_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(scheduler_router, prefix="/api/v1")
app.include_router(providers_router)  # Already has /api/v1/providers prefix


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
    import os
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


@app.get("/api/v1/stats", tags=["System"])
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

    return {
        "status": "ok",
        "articles_count": article_result["total"] if article_result else 0,
        "embedded_count": article_result["embedded"] if article_result else 0,
        "conversations_count": conv_result["total"] if conv_result else 0,
        "database_size": db_size,
        "database_path": settings.database_path,
    }


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
