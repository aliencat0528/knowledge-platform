# Knowledge Platform - Technical Plan

> 本文件定義系統的技術架構與實作計畫。

---

## 1. 系統架構

### 1.1 高層架構圖

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Knowledge Platform                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         輸入層 (Collectors)                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │   │
│  │  │   Chrome    │  │    CLI      │  │  Scheduler  │  │   Web UI    │    │   │
│  │  │  Extension  │  │  Commands   │  │   (Cron)    │  │   Upload    │    │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘    │   │
│  │         │                │                │                │           │   │
│  │         └────────────────┴────────────────┴────────────────┘           │   │
│  │                                   │                                     │   │
│  └───────────────────────────────────┼─────────────────────────────────────┘   │
│                                      │                                         │
│                                      ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         API 層 (FastAPI)                                │   │
│  │                                                                         │   │
│  │   POST /api/v1/articles          - 儲存文章                            │   │
│  │   POST /api/v1/articles/batch    - 批量儲存                            │   │
│  │   POST /api/v1/import/zip        - 匯入 .zip                           │   │
│  │   GET  /api/v1/articles          - 列出文章                            │   │
│  │   GET  /api/v1/search            - 關鍵字搜尋                          │   │
│  │   POST /api/v1/search/semantic   - 語意搜尋                            │   │
│  │   POST /api/v1/chat              - Chat 對話                           │   │
│  │   POST /api/v1/sync/notion       - 同步到 Notion                       │   │
│  │                                                                         │   │
│  └───────────────────────────────────┬─────────────────────────────────────┘   │
│                                      │                                         │
│                                      ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         服務層 (Services)                               │   │
│  │                                                                         │   │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │   │
│  │   │ ParseService│  │ImportService│  │SearchService│  │ ChatService │   │   │
│  │   │ 內容解析    │  │ 去重/匯入   │  │ 搜尋       │  │ RAG + LLM   │   │   │
│  │   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │   │
│  │                                                                         │   │
│  │   ┌─────────────┐  ┌─────────────┐                                     │   │
│  │   │EmbedService │  │ NotionSync  │                                     │   │
│  │   │ 向量化      │  │ Notion 同步 │                                     │   │
│  │   └─────────────┘  └─────────────┘                                     │   │
│  │                                                                         │   │
│  └───────────────────────────────────┬─────────────────────────────────────┘   │
│                                      │                                         │
│                                      ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         儲存層 (Storage)                                │   │
│  │                                                                         │   │
│  │   ┌─────────────────────┐    ┌─────────────────────┐                   │   │
│  │   │       SQLite        │    │      ChromaDB       │                   │   │
│  │   │   data/knowledge.db │    │    data/chroma/     │                   │   │
│  │   │                     │    │                     │                   │   │
│  │   │   • articles        │    │   • embeddings      │                   │   │
│  │   │   • hierarchy       │    │   • metadata        │                   │   │
│  │   │   • history         │    │                     │                   │   │
│  │   │   • batches         │    │                     │                   │   │
│  │   └─────────────────────┘    └─────────────────────┘                   │   │
│  │                                                                         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│                                      │                                         │
│                                      ▼ (選擇性同步)                            │
│                            ┌─────────────────────┐                             │
│                            │    Notion API       │                             │
│                            │   (External)        │                             │
│                            └─────────────────────┘                             │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 專案結構

```
knowledge-platform/
├── .speckit/                           # Spec Kit 規格文件
│   ├── constitution.md
│   ├── specs/
│   ├── plans/
│   └── tasks/
│
├── packages/
│   ├── extension/                      # Chrome 擴充套件
│   │   ├── manifest.json
│   │   ├── popup/
│   │   │   ├── index.html
│   │   │   ├── popup.ts
│   │   │   └── popup.css
│   │   ├── content/
│   │   │   ├── extractor.ts            # 內容提取
│   │   │   └── parsers/
│   │   │       ├── notion.ts
│   │   │       ├── medium.ts
│   │   │       └── generic.ts
│   │   ├── background/
│   │   │   └── service-worker.ts
│   │   ├── lib/
│   │   │   ├── readability.min.js
│   │   │   └── turndown.min.js
│   │   └── options/
│   │       ├── options.html
│   │       └── options.ts
│   │
│   ├── server/                         # Python 後端
│   │   ├── main.py                     # FastAPI 入口
│   │   ├── config.py                   # 設定管理
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── articles.py             # 文章 CRUD
│   │   │   ├── search.py               # 搜尋 API
│   │   │   ├── chat.py                 # Chat API
│   │   │   ├── import_api.py           # 匯入 API
│   │   │   └── sync.py                 # 同步 API
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── parse_service.py        # 內容解析
│   │   │   ├── import_service.py       # 匯入 + 去重
│   │   │   ├── zip_import_service.py   # Notion .zip 匯入
│   │   │   ├── chat_import_service.py  # AI 對話匯入
│   │   │   ├── search_service.py       # 搜尋邏輯
│   │   │   ├── embed_service.py        # 向量化
│   │   │   ├── chat_service.py         # RAG + LLM
│   │   │   └── notion_sync.py          # Notion 同步
│   │   ├── parsers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                 # Parser 基類
│   │   │   ├── notion.py
│   │   │   ├── medium.py
│   │   │   ├── docs.py
│   │   │   └── generic.py
│   │   ├── storage/
│   │   │   ├── __init__.py
│   │   │   ├── database.py             # SQLite 操作
│   │   │   ├── vector.py               # ChromaDB 操作
│   │   │   └── models.py               # Pydantic Models
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── markdown.py             # Markdown 處理
│   │
│   └── web-ui/                         # Vue 3 前端 (Phase 4)
│       ├── package.json
│       ├── src/
│       └── ...
│
├── scripts/
│   ├── import_zip.py                   # .zip 匯入腳本
│   ├── import_chat.py                  # AI 對話匯入腳本
│   ├── embed_all.py                    # 批量向量化
│   └── setup_db.py                     # 初始化資料庫
│
├── data/                               # 資料目錄 (gitignore)
│   ├── knowledge.db
│   └── chroma/
│
├── tests/
│   ├── test_parsers.py
│   ├── test_import.py
│   └── test_search.py
│
├── docs/
│   ├── API.md
│   ├── SETUP.md
│   └── ARCHITECTURE.md
│
├── pyproject.toml                      # Python 專案設定
├── requirements.txt
├── CLAUDE.md                           # Claude Code 規則
└── README.md
```

---

## 2. 技術選型詳細

### 2.1 後端技術

| 套件 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 主語言 |
| FastAPI | 0.109+ | Web 框架 |
| Pydantic | 2.x | 資料驗證 |
| SQLAlchemy | 2.x | ORM（可選） |
| aiosqlite | 0.19+ | 異步 SQLite |
| chromadb | 0.4+ | 向量資料庫 |
| openai | 1.x | Embedding + LLM |
| httpx | 0.26+ | HTTP 客戶端 |
| beautifulsoup4 | 4.12+ | HTML 解析 |
| markdownify | 0.11+ | HTML → Markdown |
| notion-client | 2.x | Notion API |
| apscheduler | 3.10+ | 排程任務 |
| uvicorn | 0.27+ | ASGI 伺服器 |

### 2.2 擴充套件技術

| 套件/工具 | 用途 |
|----------|------|
| TypeScript | 主語言 |
| Vite | 打包工具 |
| Readability.js | 內容提取 |
| Turndown.js | HTML → Markdown |

### 2.3 資料庫設計

詳見 `epic-3-storage.md` 的 Schema 定義。

---

## 3. API 設計

### 3.1 RESTful API 端點

```yaml
# 文章管理
POST   /api/v1/articles              # 新增文章
GET    /api/v1/articles              # 列出文章（分頁）
GET    /api/v1/articles/{id}         # 取得單篇
PUT    /api/v1/articles/{id}         # 更新文章
DELETE /api/v1/articles/{id}         # 刪除文章

# 批量操作
POST   /api/v1/articles/batch        # 批量新增
POST   /api/v1/import/zip            # 匯入 .zip
POST   /api/v1/import/chat           # 匯入 AI 對話（Claude Code, Cursor 等）

# 搜尋
GET    /api/v1/search                # 關鍵字搜尋
POST   /api/v1/search/semantic       # 語意搜尋

# Chat
POST   /api/v1/chat                  # 對話
GET    /api/v1/chat/history/{id}     # 對話歷史

# 同步
POST   /api/v1/sync/notion           # 同步到 Notion
GET    /api/v1/sync/status           # 同步狀態

# 系統
GET    /api/v1/health                # 健康檢查
GET    /api/v1/stats                 # 統計資訊
```

### 3.2 統一回應格式

```python
# 成功回應
{
    "success": True,
    "data": { ... },
    "meta": {
        "total": 100,
        "page": 1,
        "limit": 20
    }
}

# 錯誤回應
{
    "success": False,
    "error": {
        "code": "ARTICLE_NOT_FOUND",
        "message": "Article with id 123 not found"
    }
}
```

---

## 4. 開發階段詳細

### Phase 1a: 核心基礎

```
目標：可以透過擴充套件收藏單頁，存入本地

任務：
├── 後端
│   ├── 設定 FastAPI 專案
│   ├── 實作 SQLite 儲存層（含 article_hierarchy）
│   ├── 實作 articles API
│   ├── 實作 GenericParser
│   ├── 實作 ImportService（去重邏輯）
│   └── 確保 API 文件自動生成（/docs, /redoc）
│
└── 擴充套件
    ├── 設定 Manifest V3
    ├── 實作 Popup UI（含 Notion 偵測）
    ├── 實作內容提取
    └── 實作 API 呼叫

驗收：
✅ 擴充套件可載入
✅ 點擊「收藏」後，文章存入 SQLite
✅ 重複收藏會正確處理（跳過或更新）
✅ /docs 可查看 API 文件
```

### Phase 1b: Notion 樹狀抓取

```
目標：可以一鍵收藏 Notion 頁面及所有子頁面

任務：
├── 後端
│   ├── 實作 NotionParser
│   ├── 實作樹狀匯入 API（含父子關係）
│   └── 實作 article_hierarchy 查詢
│
└── 擴充套件
    ├── 實作 Notion 頁面偵測
    ├── 實作子頁面掃描
    ├── 實作樹狀收藏 UI（子頁面選擇）
    ├── 實作進度顯示
    └── 實作遞迴抓取（BFS + visited set）

驗收：
✅ 擴充套件偵測到 Notion 頁面時顯示特殊 UI
✅ 可列出並選擇子頁面
✅ 可一鍵收藏選中的頁面（含進度）
✅ 父子關係正確儲存
✅ 循環引用不會造成無限迴圈
```

### Phase 2: 資料收集完整（Week 3-4）

```
目標：支援所有收集方式，完整去重

任務：
├── 後端
│   ├── 實作 .zip 匯入
│   ├── 實作關鍵字搜尋
│   ├── 實作 AI 對話匯入（Claude Code, Cursor, Windsurf）
│   └── 實作版本追蹤
│
└── 擴充套件
    ├── 實作批量分頁抓取
    └── 實作進度顯示

驗收：
✅ 可匯入 Notion Export (.zip)
✅ 可批量收藏分頁
✅ 可用關鍵字搜尋
✅ 可匯入 AI 編輯器對話（JSONL, SQLite, Markdown）
```

### Phase 3: 智慧搜尋（Week 5-6）

```
目標：支援語意搜尋，同步到 Notion

任務：
├── 後端
│   ├── 整合 ChromaDB
│   ├── 實作 Embedding Service
│   ├── 實作語意搜尋
│   └── 實作 Notion 同步
│
└── CLI
    └── 實作批量向量化腳本

驗收：
✅ 新文章自動向量化
✅ 可用自然語言搜尋
✅ 可同步到 Notion
```

### Phase 4: 完整體驗（Week 7-8）

```
目標：Chat 功能 + Web UI

任務：
├── 後端
│   ├── 實作 RAG 流程
│   ├── 實作 Chat API
│   └── 實作排程爬取
│
└── 前端
    ├── Vue 3 專案設定
    ├── 文章列表頁
    ├── 搜尋頁
    └── Chat 頁

驗收：
✅ 可與知識庫對話
✅ Web UI 可瀏覽、搜尋、Chat
✅ 排程自動抓取
```

### Phase 5: 多 Provider 支援（Week 9-10）

```
目標：支援多種 LLM 和 Embedding Provider

任務：
├── 後端
│   ├── Provider 抽象層設計
│   ├── OpenAI Provider 重構
│   ├── Anthropic Provider 實作
│   ├── Ollama Provider 實作（本地模型）
│   ├── Provider 工廠與設定
│   ├── Service 層重構
│   └── Provider 健康檢查 API
│
└── 前端
    └── Web UI Provider 設定頁

驗收：
✅ 可切換 LLM Provider（OpenAI/Anthropic/Ollama）
✅ 可切換 Embedding Provider（OpenAI/Ollama）
✅ Web UI 可設定和測試 Provider
✅ 本地模型可正常運作
```

### 4.5 分支規劃對應表

本專案採用 **Phase 直線化開發**，每個 Phase 完成後才能開始下一個。

#### Phase 1a → Phase 1b → Phase 2 → Phase 3 → Phase 4

| Phase | 分支名稱 | 包含任務 | 預估時間 | 狀態 |
|-------|----------|----------|----------|------|
| **1a** | `feature/backend-core-sec` | 1a.1~1a.6（專案初始化到 FastAPI） | ~6 hr | ✅ 完成 |
| **1a** | `feature/extension-core-third` | 1a.7~1a.10（擴充套件骨架到錯誤處理） | ~4 hr | ✅ 完成 |
| **1b** | `feature/notion-parser-fourth` | 1b.1~1b.2（NotionParser + 樹狀 API） | ~2.5 hr | ✅ 完成 |
| **1b** | `feature/notion-extension-fifth` | 1b.3~1b.7（子頁面掃描到整合測試） | ~5.5 hr | ✅ 完成 |
| **2** | `feature/batch-import-sixth` | 2.1~2.4（批量分頁 + .zip 匯入 + 搜尋） | ~6 hr | ✅ 完成 |
| **2** | `feature/ai-chat-import-seventh` | 2.5~2.7（AI 對話匯入：Claude Code, Cursor） | ~4 hr | 📋 待開始 |
| **3** | `feature/vector-search-eighth` | 3.1~3.5（ChromaDB + 語意搜尋） | ~8 hr | 📋 待開始 |
| **3** | `feature/notion-sync-ninth` | 3.6~3.10（Notion 同步 + 認證） | ~7 hr | 📋 待開始 |
| **4** | `feature/chat-rag-tenth` | 4.1~4.4（RAG + Chat API） | ~8 hr | ✅ 完成 |
| **4** | `feature/scheduler-eleventh` | 4.5~4.6（排程爬取） | ~4 hr | ✅ 完成 |
| **4** | `feature/web-ui-twelfth` | 4.7~4.12（Web UI + 整合測試） | ~8 hr | ✅ 完成 |
| **5** | `feature/multi-provider-thirteenth` | 5.1~5.8（多 Provider 支援） | ~12.5 hr | 📋 待開始 |
| **6** | `feature/deployment-thirteenth` | 6.1~6.8（Zeabur 部署 + CI/CD） | ~8 hr | 🔄 進行中 |

#### 開發流程

```
                    Phase 1a 完成
                         │
main ────┬───────────────┼───────────────┬───────────────┬────────►
         │               │               │               │
         ├─ backend-core ┤               │               │
         │    (PR #2)    │               │               │
         │               │               │               │
         └─ extension-core               │               │
              (PR #3)    │               │               │
                         │               │               │
                    Phase 1b 開始        │               │
                         │               │               │
                         ├─ notion-parser                │
                         │    (PR #4)    │               │
                         │               │               │
                         └─ notion-ext ──┤               │
                              (PR #5)    │               │
                                         │               │
                                    Phase 2 開始         │
                                         │               │
                                         ├─ batch-import │
                                         │    (PR #6)    │
                                         │               │
                                         └─ parsers ─────┤
                                              (PR #7)    │
                                                         │
                                                    Phase 3 開始
                                                         ...
```

#### 分支開始條件

| 要開始的 Phase | 前置條件 |
|----------------|----------|
| Phase 1a | 無（可直接開始） |
| Phase 1b | Phase 1a 所有 PR 已 merge |
| Phase 2 | Phase 1b 所有 PR 已 merge |
| Phase 3 | Phase 2 所有 PR 已 merge |
| Phase 4 | Phase 3 所有 PR 已 merge |
| Phase 5 | Phase 4 所有 PR 已 merge |
| Phase 6 | Phase 4 Web UI 完成（可與 Phase 5 平行） |
| Phase 7 | Phase 6 完成後選擇（進階部署選項） |

---

## 5. 設定管理

### 5.1 環境變數

```bash
# .env (本地開發)

# 基本設定
DATABASE_PATH=./data/knowledge.db
CHROMA_PATH=./data/chroma

# API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...  # Phase 5+
NOTION_API_KEY=secret_...
NOTION_DATABASE_ID=...

# LLM Provider (openai / anthropic / ollama)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini

# Embedding Provider (openai / ollama)
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small

# Ollama (本地模型，Phase 5+)
OLLAMA_BASE_URL=http://localhost:11434

# 選項
AUTO_EMBED=false  # 新文章自動向量化

# 開發
DEBUG=true
LOG_LEVEL=INFO
```

### 5.2 Config 類

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    database_path: str = "./data/knowledge.db"
    chroma_path: str = "./data/chroma"

    # API Keys
    openai_api_key: str | None = None
    notion_api_key: str | None = None
    notion_database_id: str | None = None

    # Embedding
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"

    # LLM
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"

    # Server
    debug: bool = False
    log_level: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 6. 整合層設計

### 6.1 API 設計原則

```
┌─────────────────────────────────────────────────────────────┐
│                    API 設計原則                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   1. RESTful + JSON                                         │
│      - 資源導向設計                                          │
│      - 統一使用 JSON 格式                                    │
│                                                             │
│   2. 版本化                                                  │
│      - /api/v1/ 前綴                                        │
│      - 新版本不破壞舊介面                                    │
│                                                             │
│   3. 統一錯誤格式                                            │
│      - 所有錯誤回傳相同結構                                  │
│      - 包含 code、message、details                          │
│                                                             │
│   4. 自動文件                                                │
│      - FastAPI 自動產生 OpenAPI spec                        │
│      - /docs (Swagger UI)                                   │
│      - /redoc (ReDoc)                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 認證機制

```python
# 認證策略：可選的 API Key

# 本地模式（預設）
# - 未設定 API_KEY 環境變數
# - 所有請求無需認證

# 認證模式
# - 設定 API_KEY 環境變數
# - 所有請求需帶 X-API-Key Header

from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    expected_key = settings.api_key
    if expected_key is None:
        return  # 本地模式，不需認證
    if api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
```

### 6.3 支援的整合方式

| 方式 | 說明 | 範例 |
|------|------|------|
| HTTP API | 標準 REST 呼叫 | curl、httpx、fetch |
| CLI | 命令列工具 | `python scripts/import_url.py <url>` |
| 批量匯入 | .zip / JSON 檔案 | `python scripts/import_zip.py <file>` |
| SDK | Python package（未來）| `from knowledge_platform import Client` |

### 6.4 整合流程

```
┌─────────────────────────────────────────────────────────────┐
│                    整合流程                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   1. 閱讀 API 文件                                          │
│      └── GET /docs 或 /redoc                               │
│                                                             │
│   2. 測試連線                                                │
│      └── GET /api/v1/health                                │
│                                                             │
│   3. 送入資料                                                │
│      ├── 單篇: POST /api/v1/articles                       │
│      └── 批量: POST /api/v1/articles/batch                 │
│                                                             │
│   4. 驗證結果                                                │
│      └── GET /api/v1/articles?source_id=xxx               │
│                                                             │
│   5. 搜尋使用                                                │
│      ├── 關鍵字: GET /api/v1/search?q=xxx                  │
│      └── 語意: POST /api/v1/search/semantic                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. 測試策略

### 6.1 測試類型

| 類型 | 覆蓋目標 | 工具 |
|------|---------|------|
| 單元測試 | Services, Parsers | pytest |
| 整合測試 | API 端點 | pytest + httpx |
| E2E 測試 | 擴充套件 | Playwright |

### 6.2 測試範例

```python
# tests/test_import_service.py

def test_import_new_article():
    """新文章應該被正確儲存"""
    service = ImportService(db)
    result = service.import_article(
        source_type="web",
        source_id="test123",
        title="Test Article",
        content="# Test\n\nContent here"
    )
    assert result.status == "new"
    assert result.article_id is not None

def test_import_duplicate_skip():
    """相同內容應該被跳過"""
    service = ImportService(db)
    # 先匯入一次
    service.import_article(...)
    # 再匯入一次
    result = service.import_article(...)
    assert result.status == "skipped"

def test_import_update_on_change():
    """內容變更應該更新"""
    service = ImportService(db)
    # 先匯入
    service.import_article(content="Version 1")
    # 修改後匯入
    result = service.import_article(content="Version 2")
    assert result.status == "updated"
```

---

## 8. 部署架構

### Phase 6: 部署與 DevOps

```
目標：部署到 Zeabur，建立 CI/CD 流程

任務：
├── 部署設定
│   ├── zeabur.json 設定檔
│   ├── Dockerfile（多階段建置）
│   └── 環境變數管理
│
├── CI/CD
│   ├── GitHub Actions Build
│   └── 自動部署到 Zeabur
│
├── 維運
│   ├── 健康檢查強化
│   └── 資料備份機制
│
└── 進階規劃
    ├── Docker Compose（自架方案）
    └── Terraform（雲端方案）

驗收：
✅ Zeabur 部署成功
✅ PR merge 後自動部署
✅ 健康檢查正常
✅ 備份機制可用
```

### 8.1 部署架構圖

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Production Environment                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                         Zeabur Platform                              │   │
│   │                                                                      │   │
│   │   ┌─────────────────┐        ┌─────────────────┐                    │   │
│   │   │   knowledge-api │        │  knowledge-web  │                    │   │
│   │   │   (Container)   │        │    (Static)     │                    │   │
│   │   │                 │        │                 │                    │   │
│   │   │   FastAPI       │◄──────►│   Vue 3 SPA     │                    │   │
│   │   │   Port 8000     │        │   Port 80       │                    │   │
│   │   │                 │        │                 │                    │   │
│   │   └────────┬────────┘        └─────────────────┘                    │   │
│   │            │                                                         │   │
│   │            ▼                                                         │   │
│   │   ┌─────────────────┐                                               │   │
│   │   │     Volume      │                                               │   │
│   │   │  /app/data      │                                               │   │
│   │   │                 │                                               │   │
│   │   │  • knowledge.db │                                               │   │
│   │   │  • chroma/      │                                               │   │
│   │   └─────────────────┘                                               │   │
│   │                                                                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│                              ┌─────────────┐                                │
│                              │   Secrets   │                                │
│                              │             │                                │
│                              │ OPENAI_KEY  │                                │
│                              │ NOTION_KEY  │                                │
│                              └─────────────┘                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ GitHub Actions
                                      │
┌─────────────────────────────────────┴───────────────────────────────────────┐
│                                CI/CD Pipeline                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌───────────┐    ┌───────────┐    ┌───────────┐    ┌───────────┐        │
│   │   Push    │───►│   Build   │───►│   Test    │───►│  Deploy   │        │
│   │           │    │           │    │           │    │           │        │
│   │  PR/Main  │    │  Docker   │    │  pytest   │    │  Zeabur   │        │
│   │           │    │  Vue      │    │  vue-tsc  │    │  Action   │        │
│   └───────────┘    └───────────┘    └───────────┘    └───────────┘        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 部署方式比較

| 方式 | 複雜度 | 成本 | 適用場景 | 狀態 |
|------|--------|------|----------|------|
| **Zeabur** | ⭐ | $5-15/月 | 快速上線 | Phase 6 實作 |
| **Docker Compose** | ⭐⭐ | $5-10/月 | 自架 VPS | Phase 6 規劃 |
| **Terraform** | ⭐⭐⭐ | 變動 | 多環境 | Phase 7 選項 |
| **Kubernetes** | ⭐⭐⭐⭐⭐ | $50+/月 | 大規模 | 未來選項 |

### 8.3 進階擴展路線

```
Phase 6（目前）：Zeabur 單機部署
     │
     ▼
Phase 7（選項）：
     │
     ├──► 7A: Docker Compose + VPS
     │         └── 適合：自主控制、固定成本
     │
     ├──► 7B: Terraform + DigitalOcean
     │         └── 適合：自動化、多環境
     │
     └──► 7C: Terraform + AWS/GCP
               └── 適合：企業級、高可用
```
