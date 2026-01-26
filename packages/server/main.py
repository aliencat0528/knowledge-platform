"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from .config import settings
from .storage.database import init_db, close_db, get_db
from .api.articles import router as articles_router
from .api.import_api import router as import_router
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
    yield
    # Shutdown
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


@app.get("/api/v1/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/v1/stats", tags=["System"])
async def get_stats():
    """Get system statistics."""
    db = await get_db()

    # Get article counts
    result = await db.fetchone(
        "SELECT COUNT(*) as total, SUM(CASE WHEN is_embedded THEN 1 ELSE 0 END) as embedded FROM articles"
    )

    return {
        "status": "ok",
        "articles_count": result["total"] if result else 0,
        "embedded_count": result["embedded"] if result else 0,
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
