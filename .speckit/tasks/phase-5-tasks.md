# Phase 5 Tasks - 多 Provider 支援

> Phase 5 實作 LLM 和 Embedding 的多 Provider 抽象層，支援 OpenAI、Anthropic、本地模型等。

---

## 完成狀態總覽

| Task | 功能 | 分支 | 狀態 |
|------|------|------|------|
| 5.1 | Provider 抽象基類 | `feature/multi-provider-thirteenth` | 📋 待開始 |
| 5.2 | OpenAI Provider 重構 | `feature/multi-provider-thirteenth` | 📋 待開始 |
| 5.3 | Anthropic Provider | `feature/multi-provider-thirteenth` | 📋 待開始 |
| 5.4 | Ollama Provider (本地) | `feature/multi-provider-thirteenth` | 📋 待開始 |
| 5.5 | Provider 工廠與設定 | `feature/multi-provider-thirteenth` | 📋 待開始 |
| 5.6 | Service 層重構 | `feature/multi-provider-thirteenth` | 📋 待開始 |
| 5.7 | Web UI Provider 設定 | `feature/multi-provider-thirteenth` | 📋 待開始 |
| 5.8 | Provider 健康檢查 API | `feature/multi-provider-thirteenth` | 📋 待開始 |

---

# feature/multi-provider-thirteenth 分支任務

## Task 5.1: Provider 抽象基類

### 描述
定義 LLM 和 Embedding Provider 的抽象基類，建立統一介面

### 輸出
- `providers/__init__.py`
- `providers/base.py`

### 程式碼設計

```python
# providers/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncIterator


class ProviderType(Enum):
    """Provider 類型"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    LOCAL = "local"


@dataclass
class LLMResponse:
    """LLM 回應結構"""
    content: str
    model: str
    usage: dict[str, int]  # prompt_tokens, completion_tokens, total_tokens
    finish_reason: str | None = None


@dataclass
class EmbeddingResponse:
    """Embedding 回應結構"""
    embedding: list[float]
    model: str
    dimensions: int
    usage: dict[str, int]  # total_tokens


class BaseLLMProvider(ABC):
    """LLM Provider 抽象基類"""

    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Provider 類型"""
        pass

    @property
    @abstractmethod
    def available_models(self) -> list[str]:
        """可用模型列表"""
        pass

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> LLMResponse:
        """執行對話"""
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> AsyncIterator[str]:
        """串流對話"""
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """健康檢查"""
        pass


class BaseEmbeddingProvider(ABC):
    """Embedding Provider 抽象基類"""

    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Provider 類型"""
        pass

    @property
    @abstractmethod
    def available_models(self) -> list[str]:
        """可用模型列表"""
        pass

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """向量維度"""
        pass

    @abstractmethod
    async def embed(self, text: str) -> EmbeddingResponse:
        """單一文字向量化"""
        pass

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResponse]:
        """批量向量化"""
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """健康檢查"""
        pass
```

### 驗證
```python
from packages.server.providers.base import BaseLLMProvider, BaseEmbeddingProvider

# 應該是抽象類，無法直接實例化
# BaseLLMProvider()  # TypeError
```

### 相依
- 無

---

## Task 5.2: OpenAI Provider 重構

### 描述
將現有 OpenAI 邏輯重構為 Provider 實作

### 輸出
- `providers/openai_provider.py`

### 程式碼設計

```python
# providers/openai_provider.py
from openai import AsyncOpenAI
from .base import (
    BaseLLMProvider, BaseEmbeddingProvider,
    ProviderType, LLMResponse, EmbeddingResponse,
)


class OpenAILLMProvider(BaseLLMProvider):
    """OpenAI LLM Provider"""

    MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
    ]

    def __init__(self, api_key: str, default_model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.default_model = default_model
        self._client = AsyncOpenAI(api_key=api_key)

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OPENAI

    @property
    def available_models(self) -> list[str]:
        return self.MODELS

    async def chat(self, messages, model=None, temperature=0.7, max_tokens=2000, **kwargs):
        response = await self._client.chat.completions.create(
            model=model or self.default_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            finish_reason=response.choices[0].finish_reason,
        )

    async def chat_stream(self, messages, model=None, temperature=0.7, max_tokens=2000, **kwargs):
        stream = await self._client.chat.completions.create(
            model=model or self.default_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def health_check(self):
        try:
            response = await self._client.models.list()
            return {"status": "ok", "provider": "openai", "models": len(response.data)}
        except Exception as e:
            return {"status": "error", "provider": "openai", "error": str(e)}


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI Embedding Provider"""

    MODELS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(self, api_key: str, default_model: str = "text-embedding-3-small"):
        self.api_key = api_key
        self.default_model = default_model
        self._client = AsyncOpenAI(api_key=api_key)

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OPENAI

    @property
    def available_models(self) -> list[str]:
        return list(self.MODELS.keys())

    @property
    def dimensions(self) -> int:
        return self.MODELS.get(self.default_model, 1536)

    async def embed(self, text: str) -> EmbeddingResponse:
        response = await self._client.embeddings.create(
            model=self.default_model,
            input=text,
        )
        return EmbeddingResponse(
            embedding=response.data[0].embedding,
            model=response.model,
            dimensions=len(response.data[0].embedding),
            usage={"total_tokens": response.usage.total_tokens},
        )

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResponse]:
        response = await self._client.embeddings.create(
            model=self.default_model,
            input=texts,
        )
        return [
            EmbeddingResponse(
                embedding=data.embedding,
                model=response.model,
                dimensions=len(data.embedding),
                usage={"total_tokens": response.usage.total_tokens // len(texts)},
            )
            for data in sorted(response.data, key=lambda x: x.index)
        ]

    async def health_check(self):
        try:
            await self.embed("test")
            return {"status": "ok", "provider": "openai", "model": self.default_model}
        except Exception as e:
            return {"status": "error", "provider": "openai", "error": str(e)}
```

### 驗證
```python
from packages.server.providers.openai_provider import OpenAILLMProvider

provider = OpenAILLMProvider(api_key="sk-...")
response = await provider.chat([{"role": "user", "content": "Hello"}])
print(response.content)
```

### 相依
- Task 5.1

---

## Task 5.3: Anthropic Provider

### 描述
實作 Anthropic Claude Provider

### 輸出
- `providers/anthropic_provider.py`

### 程式碼設計

```python
# providers/anthropic_provider.py
from anthropic import AsyncAnthropic
from .base import BaseLLMProvider, ProviderType, LLMResponse


class AnthropicLLMProvider(BaseLLMProvider):
    """Anthropic Claude LLM Provider"""

    MODELS = [
        "claude-opus-4-5-20251101",
        "claude-sonnet-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
    ]

    def __init__(self, api_key: str, default_model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.default_model = default_model
        self._client = AsyncAnthropic(api_key=api_key)

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.ANTHROPIC

    @property
    def available_models(self) -> list[str]:
        return self.MODELS

    async def chat(self, messages, model=None, temperature=0.7, max_tokens=2000, **kwargs):
        # 轉換 OpenAI 格式到 Anthropic 格式
        system_message = None
        anthropic_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

        response = await self._client.messages.create(
            model=model or self.default_model,
            messages=anthropic_messages,
            system=system_message,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            finish_reason=response.stop_reason,
        )

    async def chat_stream(self, messages, model=None, temperature=0.7, max_tokens=2000, **kwargs):
        system_message = None
        anthropic_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

        async with self._client.messages.stream(
            model=model or self.default_model,
            messages=anthropic_messages,
            system=system_message,
            temperature=temperature,
            max_tokens=max_tokens,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def health_check(self):
        try:
            # Simple health check with minimal tokens
            await self.chat(
                [{"role": "user", "content": "Hi"}],
                max_tokens=10,
            )
            return {"status": "ok", "provider": "anthropic", "model": self.default_model}
        except Exception as e:
            return {"status": "error", "provider": "anthropic", "error": str(e)}
```

### 驗證
```python
from packages.server.providers.anthropic_provider import AnthropicLLMProvider

provider = AnthropicLLMProvider(api_key="sk-ant-...")
response = await provider.chat([{"role": "user", "content": "Hello"}])
print(response.content)
```

### 相依
- Task 5.1

---

## Task 5.4: Ollama Provider (本地模型)

### 描述
實作 Ollama 本地模型 Provider，支援 LLM 和 Embedding

### 輸出
- `providers/ollama_provider.py`

### 程式碼設計

```python
# providers/ollama_provider.py
import httpx
from .base import (
    BaseLLMProvider, BaseEmbeddingProvider,
    ProviderType, LLMResponse, EmbeddingResponse,
)


class OllamaLLMProvider(BaseLLMProvider):
    """Ollama 本地 LLM Provider"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        default_model: str = "llama3.2",
    ):
        self.base_url = base_url
        self.default_model = default_model
        self._client = httpx.AsyncClient(base_url=base_url, timeout=120.0)

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OLLAMA

    @property
    def available_models(self) -> list[str]:
        # 動態取得已安裝模型
        return []  # 透過 API 查詢

    async def list_models(self) -> list[str]:
        """取得已安裝模型列表"""
        response = await self._client.get("/api/tags")
        data = response.json()
        return [m["name"] for m in data.get("models", [])]

    async def chat(self, messages, model=None, temperature=0.7, max_tokens=2000, **kwargs):
        response = await self._client.post(
            "/api/chat",
            json={
                "model": model or self.default_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            },
        )
        data = response.json()

        return LLMResponse(
            content=data["message"]["content"],
            model=data["model"],
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            },
            finish_reason="stop" if data.get("done") else None,
        )

    async def chat_stream(self, messages, model=None, temperature=0.7, max_tokens=2000, **kwargs):
        async with self._client.stream(
            "POST",
            "/api/chat",
            json={
                "model": model or self.default_model,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            },
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    import json
                    data = json.loads(line)
                    if content := data.get("message", {}).get("content"):
                        yield content

    async def health_check(self):
        try:
            models = await self.list_models()
            return {"status": "ok", "provider": "ollama", "models": models}
        except Exception as e:
            return {"status": "error", "provider": "ollama", "error": str(e)}


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Ollama 本地 Embedding Provider"""

    # 常見 embedding 模型的維度
    MODEL_DIMENSIONS = {
        "nomic-embed-text": 768,
        "mxbai-embed-large": 1024,
        "all-minilm": 384,
    }

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        default_model: str = "nomic-embed-text",
    ):
        self.base_url = base_url
        self.default_model = default_model
        self._client = httpx.AsyncClient(base_url=base_url, timeout=60.0)

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.OLLAMA

    @property
    def available_models(self) -> list[str]:
        return list(self.MODEL_DIMENSIONS.keys())

    @property
    def dimensions(self) -> int:
        return self.MODEL_DIMENSIONS.get(self.default_model, 768)

    async def embed(self, text: str) -> EmbeddingResponse:
        response = await self._client.post(
            "/api/embeddings",
            json={
                "model": self.default_model,
                "prompt": text,
            },
        )
        data = response.json()
        embedding = data["embedding"]

        return EmbeddingResponse(
            embedding=embedding,
            model=self.default_model,
            dimensions=len(embedding),
            usage={"total_tokens": len(text.split())},  # 估算
        )

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResponse]:
        # Ollama 不支援批量，逐一處理
        results = []
        for text in texts:
            results.append(await self.embed(text))
        return results

    async def health_check(self):
        try:
            await self.embed("test")
            return {"status": "ok", "provider": "ollama", "model": self.default_model}
        except Exception as e:
            return {"status": "error", "provider": "ollama", "error": str(e)}
```

### 驗證
```bash
# 先確保 Ollama 運行中
ollama serve

# 拉取模型
ollama pull llama3.2
ollama pull nomic-embed-text
```

```python
from packages.server.providers.ollama_provider import OllamaLLMProvider

provider = OllamaLLMProvider()
response = await provider.chat([{"role": "user", "content": "Hello"}])
print(response.content)
```

### 相依
- Task 5.1

---

## Task 5.5: Provider 工廠與設定

### 描述
實作 Provider 工廠模式和設定管理

### 輸出
- `providers/factory.py`
- 更新 `config.py`

### 程式碼設計

```python
# providers/factory.py
from .base import BaseLLMProvider, BaseEmbeddingProvider, ProviderType
from .openai_provider import OpenAILLMProvider, OpenAIEmbeddingProvider
from .anthropic_provider import AnthropicLLMProvider
from .ollama_provider import OllamaLLMProvider, OllamaEmbeddingProvider
from ..config import settings


class ProviderFactory:
    """Provider 工廠"""

    _llm_providers: dict[ProviderType, type[BaseLLMProvider]] = {
        ProviderType.OPENAI: OpenAILLMProvider,
        ProviderType.ANTHROPIC: AnthropicLLMProvider,
        ProviderType.OLLAMA: OllamaLLMProvider,
    }

    _embedding_providers: dict[ProviderType, type[BaseEmbeddingProvider]] = {
        ProviderType.OPENAI: OpenAIEmbeddingProvider,
        ProviderType.OLLAMA: OllamaEmbeddingProvider,
    }

    @classmethod
    def create_llm_provider(
        cls,
        provider_type: ProviderType | str | None = None,
        **kwargs,
    ) -> BaseLLMProvider:
        """建立 LLM Provider"""
        if provider_type is None:
            provider_type = settings.llm_provider

        if isinstance(provider_type, str):
            provider_type = ProviderType(provider_type)

        provider_class = cls._llm_providers.get(provider_type)
        if not provider_class:
            raise ValueError(f"Unsupported LLM provider: {provider_type}")

        # 依 Provider 類型設定預設參數
        if provider_type == ProviderType.OPENAI:
            kwargs.setdefault("api_key", settings.openai_api_key)
            kwargs.setdefault("default_model", settings.llm_model)
        elif provider_type == ProviderType.ANTHROPIC:
            kwargs.setdefault("api_key", settings.anthropic_api_key)
            kwargs.setdefault("default_model", settings.llm_model)
        elif provider_type == ProviderType.OLLAMA:
            kwargs.setdefault("base_url", settings.ollama_base_url)
            kwargs.setdefault("default_model", settings.llm_model)

        return provider_class(**kwargs)

    @classmethod
    def create_embedding_provider(
        cls,
        provider_type: ProviderType | str | None = None,
        **kwargs,
    ) -> BaseEmbeddingProvider:
        """建立 Embedding Provider"""
        if provider_type is None:
            provider_type = settings.embedding_provider

        if isinstance(provider_type, str):
            provider_type = ProviderType(provider_type)

        provider_class = cls._embedding_providers.get(provider_type)
        if not provider_class:
            raise ValueError(f"Unsupported embedding provider: {provider_type}")

        # 依 Provider 類型設定預設參數
        if provider_type == ProviderType.OPENAI:
            kwargs.setdefault("api_key", settings.openai_api_key)
            kwargs.setdefault("default_model", settings.embedding_model)
        elif provider_type == ProviderType.OLLAMA:
            kwargs.setdefault("base_url", settings.ollama_base_url)
            kwargs.setdefault("default_model", settings.embedding_model)

        return provider_class(**kwargs)

    @classmethod
    def list_llm_providers(cls) -> list[str]:
        """列出支援的 LLM Provider"""
        return [p.value for p in cls._llm_providers.keys()]

    @classmethod
    def list_embedding_providers(cls) -> list[str]:
        """列出支援的 Embedding Provider"""
        return [p.value for p in cls._embedding_providers.keys()]


# 全域單例
_llm_provider: BaseLLMProvider | None = None
_embedding_provider: BaseEmbeddingProvider | None = None


def get_llm_provider() -> BaseLLMProvider:
    """取得全域 LLM Provider"""
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = ProviderFactory.create_llm_provider()
    return _llm_provider


def get_embedding_provider() -> BaseEmbeddingProvider:
    """取得全域 Embedding Provider"""
    global _embedding_provider
    if _embedding_provider is None:
        _embedding_provider = ProviderFactory.create_embedding_provider()
    return _embedding_provider
```

### 更新 config.py

```python
# config.py 新增
class Settings(BaseSettings):
    # ... 現有設定

    # LLM Provider
    llm_provider: str = "openai"  # openai, anthropic, ollama
    llm_model: str = "gpt-4o-mini"

    # Embedding Provider
    embedding_provider: str = "openai"  # openai, ollama
    embedding_model: str = "text-embedding-3-small"

    # API Keys
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
```

### 驗證
```python
from packages.server.providers.factory import ProviderFactory

# 建立 OpenAI LLM
llm = ProviderFactory.create_llm_provider("openai")

# 建立 Anthropic LLM
llm = ProviderFactory.create_llm_provider("anthropic")

# 建立 Ollama LLM
llm = ProviderFactory.create_llm_provider("ollama")
```

### 相依
- Task 5.2
- Task 5.3
- Task 5.4

---

## Task 5.6: Service 層重構

### 描述
重構 EmbedService 和 ChatService 使用 Provider 抽象

### 輸出
- 更新 `services/embed_service.py`
- 更新 `services/chat_service.py`

### 程式碼設計

```python
# services/embed_service.py 重構
class EmbedService:
    def __init__(
        self,
        embedding_provider: BaseEmbeddingProvider | None = None,
        vector_store: VectorStore | None = None,
    ):
        self.provider = embedding_provider or get_embedding_provider()
        self.vector_store = vector_store or get_vector_store()

    @property
    def dimensions(self) -> int:
        return self.provider.dimensions

    async def embed_text(self, text: str) -> list[float]:
        response = await self.provider.embed(text)
        return response.embedding

    # ... 其他方法保持相似結構
```

```python
# services/chat_service.py 重構
class ChatService:
    def __init__(
        self,
        llm_provider: BaseLLMProvider | None = None,
        embed_service: EmbedService | None = None,
    ):
        self.llm = llm_provider or get_llm_provider()
        self._embed_service = embed_service

    async def chat(self, query: str, db: Database, ...) -> dict[str, Any]:
        # ... 搜尋上下文

        # 使用抽象 Provider
        response = await self.llm.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return {
            "answer": response.content,
            "usage": response.usage,
            # ...
        }
```

### 驗證
```python
# 切換到 Anthropic
from packages.server.providers.factory import ProviderFactory
from packages.server.services.chat_service import ChatService

llm = ProviderFactory.create_llm_provider("anthropic")
service = ChatService(llm_provider=llm)
response = await service.chat("如何使用 React?", db)
```

### 相依
- Task 5.5

---

## Task 5.7: Web UI Provider 設定

### 描述
在 Web UI 設定頁加入 Provider 設定功能

### 輸出
- 更新 `packages/web-ui/src/views/SettingsView.vue`
- 新增 `packages/web-ui/src/components/ProviderSettings.vue`

### 功能
- LLM Provider 選擇（OpenAI / Anthropic / Ollama）
- Embedding Provider 選擇（OpenAI / Ollama）
- 模型選擇（依 Provider 動態顯示）
- API Key 設定（安全儲存）
- Ollama 連線設定
- Provider 連線測試按鈕

### UI 設計
```
┌─────────────────────────────────────┐
│ Provider 設定                        │
├─────────────────────────────────────┤
│ LLM Provider:  [OpenAI ▼]           │
│ LLM Model:     [gpt-4o-mini ▼]      │
│ API Key:       [••••••••••••] [Test]│
│                                     │
│ Embedding Provider: [OpenAI ▼]      │
│ Embedding Model: [text-embedding-3-small ▼] │
│                                     │
│ ─── Ollama 設定 ───                 │
│ Base URL: [http://localhost:11434]  │
│ [測試連線]                          │
│                                     │
│ [儲存設定]                          │
└─────────────────────────────────────┘
```

### 相依
- Task 5.5
- Task 5.8

---

## Task 5.8: Provider 健康檢查 API

### 描述
提供 Provider 狀態檢查的 API 端點

### 輸出
- `api/providers.py`

### API 端點
```yaml
# 列出支援的 Provider
GET /api/v1/providers
{
  "llm": ["openai", "anthropic", "ollama"],
  "embedding": ["openai", "ollama"]
}

# 取得 Provider 模型列表
GET /api/v1/providers/{type}/models?provider=openai
{
  "provider": "openai",
  "models": ["gpt-4o", "gpt-4o-mini", ...]
}

# 測試 Provider 連線
POST /api/v1/providers/test
{
  "provider_type": "llm",
  "provider": "openai",
  "api_key": "sk-...",
  "model": "gpt-4o-mini"
}

# 回應
{
  "status": "ok",
  "provider": "openai",
  "latency_ms": 245
}

# 取得目前 Provider 設定
GET /api/v1/providers/current
{
  "llm": {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "status": "ok"
  },
  "embedding": {
    "provider": "openai",
    "model": "text-embedding-3-small",
    "status": "ok"
  }
}

# 更新 Provider 設定
PUT /api/v1/providers/current
{
  "llm_provider": "anthropic",
  "llm_model": "claude-sonnet-4-20250514",
  "anthropic_api_key": "sk-ant-..."
}
```

### 相依
- Task 5.5

---

# Phase 5 完成條件

```
□ Provider 抽象層建立完成
□ OpenAI Provider 可用
□ Anthropic Provider 可用
□ Ollama Provider 可用
□ 可透過設定切換 Provider
□ Web UI 可設定 Provider
□ Provider 健康檢查 API 可用
□ 現有功能（Chat、Embedding）正常運作
```

---

# 預估時間

| Task | 時間 |
|------|------|
| 5.1 Provider 抽象基類 | 1 hr |
| 5.2 OpenAI Provider 重構 | 1.5 hr |
| 5.3 Anthropic Provider | 1.5 hr |
| 5.4 Ollama Provider | 2 hr |
| 5.5 Provider 工廠與設定 | 1.5 hr |
| 5.6 Service 層重構 | 2 hr |
| 5.7 Web UI Provider 設定 | 2 hr |
| 5.8 Provider 健康檢查 API | 1 hr |
| **Phase 5 合計** | **~12.5 小時** |
