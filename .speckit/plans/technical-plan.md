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

### Phase 1: 核心基礎（Week 1-2）

```
目標：可以透過擴充套件收藏單頁，存入本地

任務：
├── 後端
│   ├── 設定 FastAPI 專案
│   ├── 實作 SQLite 儲存層
│   ├── 實作 articles API
│   ├── 實作 GenericParser
│   └── 實作 ImportService（去重邏輯）
│
└── 擴充套件
    ├── 設定 Manifest V3
    ├── 實作 Popup UI
    ├── 實作內容提取
    └── 實作 API 呼叫

驗收：
✅ 擴充套件可載入
✅ 點擊「收藏」後，文章存入 SQLite
✅ 重複收藏會正確處理（跳過或更新）
```

### Phase 2: 資料收集完整（Week 3-4）

```
目標：支援所有收集方式，完整去重

任務：
├── 後端
│   ├── 實作 .zip 匯入
│   ├── 實作 NotionParser
│   ├── 實作版本追蹤
│   └── 實作關鍵字搜尋
│
└── 擴充套件
    ├── 實作批量分頁抓取
    ├── 實作樹狀抓取
    └── 實作進度顯示

驗收：
✅ 可匯入 Notion Export
✅ 可批量收藏分頁
✅ 可樹狀抓取 Notion
✅ 可用關鍵字搜尋
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
NOTION_API_KEY=secret_...
NOTION_DATABASE_ID=...

# 選項
EMBEDDING_PROVIDER=openai  # or local
EMBEDDING_MODEL=text-embedding-3-small
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini

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

## 6. 測試策略

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
