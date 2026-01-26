# Knowledge Platform - 系統架構

> 本文件描述系統的整體架構、資料流與模組關係。

---

## 1. 高層架構圖

```mermaid
flowchart TB
    subgraph Collectors["輸入層 (Collectors)"]
        EXT["Chrome Extension<br/>擴充套件"]
        CLI["CLI Commands<br/>命令列工具"]
        SCH["Scheduler<br/>排程爬取"]
        WEB["Web UI<br/>網頁上傳"]
    end

    subgraph API["API 層 (FastAPI)"]
        direction LR
        A1["POST /articles"]
        A2["POST /articles/batch"]
        A3["POST /import/zip"]
        A3b["POST /import/chat"]
        A4["GET /search"]
        A5["POST /search/semantic"]
        A6["POST /chat"]
    end

    subgraph Services["服務層 (Services)"]
        PS["ParseService<br/>內容解析"]
        IS["ImportService<br/>匯入 + 去重"]
        SS["SearchService<br/>搜尋"]
        ES["EmbedService<br/>向量化"]
        CS["ChatService<br/>RAG + LLM"]
        NS["NotionSync<br/>Notion 同步"]
    end

    subgraph Storage["儲存層 (Storage)"]
        DB[("SQLite<br/>knowledge.db")]
        VDB[("ChromaDB<br/>向量索引")]
    end

    subgraph External["外部服務"]
        OAI["OpenAI API<br/>Embedding + LLM"]
        NOT["Notion API<br/>同步"]
    end

    %% Connections
    EXT --> API
    CLI --> API
    SCH --> API
    WEB --> API

    API --> Services

    PS --> IS
    IS --> DB
    ES --> VDB
    ES --> OAI
    CS --> VDB
    CS --> OAI
    NS --> NOT
    SS --> DB
    SS --> VDB
```

---

## 2. 資料流圖

### 2.1 收藏單頁流程

```mermaid
sequenceDiagram
    participant U as 使用者
    participant E as 擴充套件
    participant A as API Server
    participant P as ParseService
    participant I as ImportService
    participant D as SQLite

    U->>E: 點擊「收藏此頁」
    E->>E: 抓取頁面 DOM
    E->>E: Readability 提取內容
    E->>E: Turndown 轉 Markdown
    E->>A: POST /api/v1/articles
    A->>P: 解析 + 清理內容
    P->>I: 匯入文章
    I->>I: 計算 content_hash
    I->>D: 查詢是否存在
    alt 新文章
        I->>D: INSERT
        I-->>A: status: "new"
    else 內容相同
        I-->>A: status: "skipped"
    else 內容更新
        I->>D: UPDATE + 記錄歷史
        I-->>A: status: "updated"
    end
    A-->>E: 回應結果
    E-->>U: 顯示提示
```

### 2.2 語意搜尋流程

```mermaid
sequenceDiagram
    participant U as 使用者
    participant A as API Server
    participant E as EmbedService
    participant V as ChromaDB
    participant D as SQLite
    participant O as OpenAI

    U->>A: POST /search/semantic<br/>query: "React 狀態管理"
    A->>E: 向量化查詢
    E->>O: 取得 embedding
    O-->>E: query_vector
    E->>V: 相似度搜尋
    V-->>E: top 5 article_ids
    E->>D: 取得文章詳情
    D-->>E: articles
    E-->>A: 搜尋結果
    A-->>U: 回傳結果 + 相似度分數
```

### 2.3 Chat (RAG) 流程

```mermaid
sequenceDiagram
    participant U as 使用者
    participant A as API Server
    participant C as ChatService
    participant V as ChromaDB
    participant D as SQLite
    participant O as OpenAI

    U->>A: POST /chat<br/>message: "useEffect 怎麼用？"
    A->>C: 處理 Chat 請求
    C->>V: 語意搜尋相關文章
    V-->>C: top 5 相關文章
    C->>D: 取得完整內容
    D-->>C: articles
    C->>C: 組裝 RAG Prompt
    C->>O: 呼叫 LLM
    O-->>C: AI 回答
    C-->>A: 回答 + 參考來源
    A-->>U: 顯示回答
```

---

## 3. 模組關係圖

```mermaid
graph TB
    subgraph Extension["packages/extension"]
        popup["popup/<br/>使用者介面"]
        content["content/<br/>內容抓取"]
        bg["background/<br/>Service Worker"]
        utils["utils/<br/>Notion 偵測"]
        lib["lib/<br/>Readability + Turndown"]
    end

    subgraph Server["packages/server"]
        main["main.py<br/>FastAPI 入口"]

        subgraph API["api/"]
            articles["articles.py"]
            search["search.py"]
            chat["chat.py"]
            import_api["import_api.py"]
            sync["sync.py"]
        end

        subgraph Services["services/"]
            parse_svc["parse_service.py"]
            import_svc["import_service.py"]
            zip_import_svc["zip_import_service.py"]
            chat_import_svc["chat_import_service.py"]
            search_svc["search_service.py"]
            embed_svc["embed_service.py"]
            chat_svc["chat_service.py"]
            notion_svc["notion_sync.py"]
        end

        subgraph Parsers["parsers/"]
            base_parser["base.py"]
            notion_parser["notion.py"]
            medium_parser["medium.py"]
            generic_parser["generic.py"]
        end

        subgraph Storage["storage/"]
            database["database.py<br/>SQLite"]
            vector["vector.py<br/>ChromaDB"]
            models["models.py<br/>Pydantic"]
        end
    end

    %% Extension connections
    popup --> bg
    bg --> content
    bg -->|HTTP| main

    %% API to Services
    main --> API
    articles --> import_svc
    search --> search_svc
    chat --> chat_svc
    import_api --> import_svc
    sync --> notion_svc

    %% Services to Parsers
    parse_svc --> Parsers
    import_svc --> parse_svc

    %% Services to Storage
    import_svc --> database
    search_svc --> database
    search_svc --> vector
    embed_svc --> vector
    chat_svc --> vector
```

---

## 4. 資料模型

### 4.1 ER 圖

```mermaid
erDiagram
    articles ||--o{ article_history : has
    articles ||--o{ article_hierarchy : parent
    articles ||--o{ article_hierarchy : child
    import_batches ||--o{ articles : contains

    articles {
        int id PK
        string source_type
        string source_id
        string title
        text content
        string content_hash
        string url
        string author
        datetime published_at
        json tags
        string notion_page_id
        datetime notion_synced_at
        boolean is_embedded
        datetime created_at
        datetime updated_at
        int version
    }

    article_history {
        int id PK
        int article_id FK
        int version
        text old_content
        text new_content
        datetime changed_at
    }

    article_hierarchy {
        int id PK
        int parent_id FK
        int child_id FK
    }

    import_batches {
        int id PK
        string source
        string file_name
        int new_count
        int updated_count
        int skipped_count
        int error_count
        datetime created_at
    }

    scheduled_tasks {
        int id PK
        string name
        string url_pattern
        string cron_expression
        boolean is_active
        datetime last_run_at
        datetime next_run_at
    }
```

### 4.2 主要欄位說明

| 欄位 | 說明 |
|------|------|
| `source_type` | 來源類型：notion / medium / docs / web / claude-code / cursor |
| `source_id` | 來源唯一識別碼（URL hash 或頁面 ID 或對話 ID） |
| `content_hash` | 內容的 MD5 hash，用於偵測變更 |
| `is_embedded` | 是否已向量化 |
| `version` | 版本號，每次更新 +1 |

---

## 5. 技術棧

```mermaid
mindmap
  root((Knowledge<br/>Platform))
    Backend
      Python 3.11+
      FastAPI
      Pydantic
      SQLite
      ChromaDB
    Extension
      JavaScript ES6+
      Chrome Manifest V3
      Readability.js
      Turndown.js
    External APIs
      OpenAI
        Embedding
        LLM
      Notion API
        Sync
    Future
      Vue 3
      Web UI
```

---

## 6. 部署架構

### 6.1 本地開發

```
┌─────────────────────────────────────────────────────────────┐
│                     本地開發環境                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────┐     ┌─────────────┐                      │
│   │   Chrome    │────▶│   FastAPI   │                      │
│   │  Extension  │     │  localhost  │                      │
│   │             │     │    :8000    │                      │
│   └─────────────┘     └──────┬──────┘                      │
│                              │                              │
│                    ┌─────────┴─────────┐                   │
│                    │                   │                   │
│               ┌────▼────┐        ┌─────▼─────┐            │
│               │ SQLite  │        │ ChromaDB  │            │
│               │ ./data/ │        │  ./data/  │            │
│               └─────────┘        └───────────┘            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 外部服務連接

```
┌─────────────────────────────────────────────────────────────┐
│                      外部服務連接                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   本地服務                          外部 API                 │
│   ────────                          ────────                │
│                                                             │
│   ┌─────────────┐                 ┌─────────────┐          │
│   │   FastAPI   │───Embedding────▶│   OpenAI    │          │
│   │   Server    │───LLM Call─────▶│    API      │          │
│   └──────┬──────┘                 └─────────────┘          │
│          │                                                  │
│          │                        ┌─────────────┐          │
│          └───Sync────────────────▶│   Notion    │          │
│                                   │    API      │          │
│                                   └─────────────┘          │
│                                                             │
│   連接為選用，核心功能可離線運作                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. 安全考量

```
┌─────────────────────────────────────────────────────────────┐
│                      安全設計                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ✅ API Keys 只存在本地 .env，不上傳 Git                   │
│   ✅ 資料庫存在本地，使用者完全掌控                          │
│   ✅ 不追蹤使用者行為                                       │
│   ✅ Notion 同步為選用功能                                  │
│   ✅ 擴充套件只與 localhost 通訊                            │
│                                                             │
│   ⚠️ 注意事項：                                             │
│   • 不要將 .env 提交到版本控制                              │
│   • 不要在公開網路暴露 API Server                           │
│   • 定期備份 data/ 目錄                                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. 擴展指南

### 8.1 新增 Parser

```python
# 1. 建立新檔案 parsers/new_site.py
from .base import BaseParser, ParsedContent

class NewSiteParser(BaseParser):
    def can_parse(self, url: str) -> bool:
        return "newsite.com" in url

    def parse(self, html: str, url: str) -> ParsedContent:
        # 實作解析邏輯
        ...

# 2. 在 parsers/__init__.py 註冊
from .new_site import NewSiteParser
PARSERS = [..., NewSiteParser()]
```

### 8.2 新增儲存目標

```python
# 1. 建立新檔案 storage/new_storage.py
class NewStorage:
    def save(self, article: Article) -> str:
        ...

    def query(self, **kwargs) -> list[Article]:
        ...

# 2. 在 services/ 中整合
```
