"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    settings.ensure_data_dir()
    print(f"Starting Knowledge Platform Server v0.1.0")
    print(f"Database: {settings.database_path}")
    print(f"Debug mode: {settings.debug}")
    yield
    # Shutdown
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


@app.get("/api/v1/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/v1/stats", tags=["System"])
async def get_stats():
    """Get system statistics."""
    # TODO: Implement actual stats from database
    return {
        "status": "ok",
        "articles_count": 0,
        "embedded_count": 0,
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
