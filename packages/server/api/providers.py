"""Provider configuration API endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel

from ..config import settings

router = APIRouter(prefix="/api/v1/providers", tags=["Providers"])


class ProviderInfo(BaseModel):
    """Provider information."""

    provider: str
    model: str
    status: str = "unknown"


class CurrentProviders(BaseModel):
    """Current provider configuration."""

    llm: ProviderInfo
    embedding: ProviderInfo


class ProviderUpdateRequest(BaseModel):
    """Request to update provider configuration."""

    llm_provider: str | None = None
    llm_model: str | None = None
    embedding_provider: str | None = None
    embedding_model: str | None = None


class ProviderTestRequest(BaseModel):
    """Request to test a provider."""

    provider_type: str  # "llm" or "embedding"
    provider: str
    model: str | None = None


# Available providers and models
LLM_PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        "requires_key": "openai_api_key",
    },
    "anthropic": {
        "name": "Anthropic",
        "models": [
            "claude-opus-4-5-20251101",
            "claude-sonnet-4-20250514",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
        ],
        "requires_key": "anthropic_api_key",
    },
    "ollama": {
        "name": "Ollama (本地)",
        "models": ["llama3.2", "llama3.1", "mistral", "codellama", "phi3"],
        "requires_key": None,
    },
}

EMBEDDING_PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "models": ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"],
        "requires_key": "openai_api_key",
    },
    "ollama": {
        "name": "Ollama (本地)",
        "models": ["nomic-embed-text", "mxbai-embed-large", "all-minilm"],
        "requires_key": None,
    },
}


@router.get("")
async def list_providers():
    """List available providers."""
    return {
        "llm": list(LLM_PROVIDERS.keys()),
        "embedding": list(EMBEDDING_PROVIDERS.keys()),
    }


@router.get("/{provider_type}/models")
async def get_provider_models(provider_type: str, provider: str | None = None):
    """Get available models for a provider."""
    if provider_type == "llm":
        providers = LLM_PROVIDERS
    elif provider_type == "embedding":
        providers = EMBEDDING_PROVIDERS
    else:
        return {"error": f"Unknown provider type: {provider_type}"}

    if provider:
        if provider not in providers:
            return {"error": f"Unknown provider: {provider}"}
        return {
            "provider": provider,
            "models": providers[provider]["models"],
        }

    return {
        "providers": {
            name: info["models"] for name, info in providers.items()
        }
    }


@router.get("/current")
async def get_current_providers():
    """Get current provider configuration."""

    def check_provider_status(provider: str, provider_type: str) -> str:
        """Check if provider is configured."""
        if provider_type == "llm":
            providers = LLM_PROVIDERS
        else:
            providers = EMBEDDING_PROVIDERS

        if provider not in providers:
            return "unknown"

        requires_key = providers[provider].get("requires_key")
        if requires_key is None:
            return "available"  # Ollama doesn't need API key

        key_value = getattr(settings, requires_key, None)
        if key_value:
            return "configured"
        return "not_configured"

    return {
        "llm": {
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "status": check_provider_status(settings.llm_provider, "llm"),
        },
        "embedding": {
            "provider": settings.embedding_provider,
            "model": settings.embedding_model,
            "status": check_provider_status(settings.embedding_provider, "embedding"),
        },
    }


@router.put("/current")
async def update_providers(request: ProviderUpdateRequest):
    """Update provider configuration.

    Note: This only validates the request. Actual configuration
    changes require updating environment variables or .env file.
    """
    errors = []

    if request.llm_provider:
        if request.llm_provider not in LLM_PROVIDERS:
            errors.append(f"Invalid LLM provider: {request.llm_provider}")
        elif request.llm_model:
            if request.llm_model not in LLM_PROVIDERS[request.llm_provider]["models"]:
                errors.append(f"Invalid model for {request.llm_provider}: {request.llm_model}")

    if request.embedding_provider:
        if request.embedding_provider not in EMBEDDING_PROVIDERS:
            errors.append(f"Invalid embedding provider: {request.embedding_provider}")
        elif request.embedding_model:
            if request.embedding_model not in EMBEDDING_PROVIDERS[request.embedding_provider]["models"]:
                errors.append(f"Invalid model for {request.embedding_provider}: {request.embedding_model}")

    if errors:
        return {"success": False, "errors": errors}

    # In a real implementation, this would update the .env file or database
    # For now, return instructions
    return {
        "success": True,
        "message": "設定已驗證。請在伺服器的 .env 檔案中更新對應設定並重啟伺服器。",
        "env_updates": {
            k: v
            for k, v in {
                "LLM_PROVIDER": request.llm_provider,
                "LLM_MODEL": request.llm_model,
                "EMBEDDING_PROVIDER": request.embedding_provider,
                "EMBEDDING_MODEL": request.embedding_model,
            }.items()
            if v is not None
        },
    }


@router.post("/test")
async def test_provider(request: ProviderTestRequest):
    """Test provider connectivity."""
    import time

    start_time = time.time()

    try:
        if request.provider_type == "llm":
            if request.provider not in LLM_PROVIDERS:
                return {"status": "error", "error": f"Unknown provider: {request.provider}"}

            # Test LLM provider
            if request.provider == "openai":
                if not settings.openai_api_key:
                    return {"status": "error", "error": "OpenAI API key not configured"}

                from openai import AsyncOpenAI

                client = AsyncOpenAI(api_key=settings.openai_api_key)
                await client.models.list()

            elif request.provider == "anthropic":
                if not settings.anthropic_api_key:
                    return {"status": "error", "error": "Anthropic API key not configured"}

                from anthropic import AsyncAnthropic

                client = AsyncAnthropic(api_key=settings.anthropic_api_key)
                # Simple test - list models or make a minimal request
                await client.messages.create(
                    model=request.model or "claude-3-5-haiku-20241022",
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Hi"}],
                )

            elif request.provider == "ollama":
                import httpx

                async with httpx.AsyncClient(
                    base_url=settings.ollama_base_url, timeout=10.0
                ) as client:
                    response = await client.get("/api/tags")
                    response.raise_for_status()

        elif request.provider_type == "embedding":
            if request.provider not in EMBEDDING_PROVIDERS:
                return {"status": "error", "error": f"Unknown provider: {request.provider}"}

            if request.provider == "openai":
                if not settings.openai_api_key:
                    return {"status": "error", "error": "OpenAI API key not configured"}

                from openai import AsyncOpenAI

                client = AsyncOpenAI(api_key=settings.openai_api_key)
                await client.embeddings.create(
                    model=request.model or "text-embedding-3-small",
                    input="test",
                )

            elif request.provider == "ollama":
                import httpx

                async with httpx.AsyncClient(
                    base_url=settings.ollama_base_url, timeout=30.0
                ) as client:
                    response = await client.post(
                        "/api/embeddings",
                        json={"model": request.model or "nomic-embed-text", "prompt": "test"},
                    )
                    response.raise_for_status()

        else:
            return {"status": "error", "error": f"Unknown provider type: {request.provider_type}"}

        latency_ms = int((time.time() - start_time) * 1000)
        return {
            "status": "ok",
            "provider": request.provider,
            "latency_ms": latency_ms,
        }

    except ImportError as e:
        return {"status": "error", "error": f"Missing dependency: {e}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
