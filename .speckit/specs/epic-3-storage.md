# Epic 3: 資料儲存 (Storage)

> 本文件定義資料儲存相關的所有功能規格。

---

## User Story 3.1: 本地儲存 (SQLite)

### 描述
```
作為系統
我需要將文章資料儲存到本地 SQLite
這樣資料可以離線存取且完全由使用者掌控
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: 儲存新文章
  Given 已解析的文章資料
  When 呼叫儲存 API
  Then 文章存入 SQLite
  And 自動計算 content_hash
  And 自動設定 created_at
  And 回傳新建立的文章 ID

Scenario: 資料庫不存在
  Given data/knowledge.db 不存在
  When 服務啟動
  Then 自動建立資料庫
  And 執行 schema 初始化
```

### 資料庫 Schema

```sql
-- 主要文章表
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 唯一識別
    source_type TEXT NOT NULL,        -- 'notion', 'medium', 'docs', 'web'
    source_id TEXT NOT NULL,          -- 來源的唯一 ID

    -- 內容
    title TEXT NOT NULL,
    content TEXT NOT NULL,            -- Markdown 格式
    content_hash TEXT NOT NULL,       -- MD5 hash
    url TEXT,

    -- Metadata
    author TEXT,
    published_at DATETIME,
    tags TEXT,                        -- JSON: ["React", "Hooks"]

    -- Notion 同步
    notion_page_id TEXT,              -- 同步到 Notion 後的 Page ID
    notion_synced_at DATETIME,

    -- 向量化
    is_embedded BOOLEAN DEFAULT FALSE,

    -- 系統欄位
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1,

    UNIQUE(source_type, source_id)
);

-- 父子關係（樹狀結構）
CREATE TABLE article_hierarchy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    child_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    UNIQUE(parent_id, child_id)
);

-- 變更歷史
CREATE TABLE article_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    old_content TEXT,
    new_content TEXT,
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 匯入批次
CREATE TABLE import_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,             -- 'extension', 'api', 'zip', 'scheduler'
    file_name TEXT,
    new_count INTEGER DEFAULT 0,
    updated_count INTEGER DEFAULT 0,
    skipped_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 排程任務
CREATE TABLE scheduled_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url_pattern TEXT NOT NULL,        -- 要爬取的 URL 或 pattern
    cron_expression TEXT NOT NULL,    -- "0 9 * * *" = 每天 9 點
    is_active BOOLEAN DEFAULT TRUE,
    last_run_at DATETIME,
    next_run_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_articles_source ON articles(source_type, source_id);
CREATE INDEX idx_articles_created ON articles(created_at);
CREATE INDEX idx_articles_embedded ON articles(is_embedded);
CREATE INDEX idx_hierarchy_parent ON article_hierarchy(parent_id);
CREATE INDEX idx_hierarchy_child ON article_hierarchy(child_id);
```

---

## User Story 3.2: 向量儲存 (ChromaDB)

### 描述
```
作為系統
我需要將文章的向量索引儲存到 ChromaDB
這樣才能支援語意搜尋
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: 儲存向量
  Given 文章已計算 embedding
  When 儲存到 ChromaDB
  Then 使用 article_id 作為 document ID
  And 儲存向量和 metadata
  And 更新 SQLite 的 is_embedded = True

Scenario: 查詢相似文章
  Given ChromaDB 中有 100 篇文章的向量
  When 用「React 狀態管理」查詢
  Then 回傳最相似的 5 篇文章
  And 包含相似度分數
```

### ChromaDB 設定

```python
import chromadb

# 初始化（本地持久化）
client = chromadb.PersistentClient(path="./data/chroma")

# Collection 設定
collection = client.get_or_create_collection(
    name="knowledge_articles",
    metadata={"hnsw:space": "cosine"}  # 使用 cosine 相似度
)

# 儲存文件
collection.add(
    ids=["article_123"],
    embeddings=[[0.1, 0.2, ...]],
    metadatas=[{
        "article_id": 123,
        "title": "React Hooks 指南",
        "source_type": "docs",
        "tags": "React,Hooks"
    }],
    documents=["文章內容..."]
)

# 查詢
results = collection.query(
    query_embeddings=[query_vector],
    n_results=5,
    include=["metadatas", "distances", "documents"]
)
```

---

## User Story 3.3: Notion 同步

### 描述
```
作為使用者
我想要將收藏的文章同步到我的 Notion
這樣我可以在 Notion 中瀏覽和整理
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: 同步單篇文章
  Given 本地有一篇新文章
  And Notion Integration 已設定
  When 我選擇同步到 Notion
  Then 在 Notion Database 建立新頁面
  And 更新 SQLite 的 notion_page_id
  And 更新 notion_synced_at

Scenario: 更新已同步的文章
  Given 文章已同步到 Notion
  And 本地文章有更新
  When 執行同步
  Then 更新 Notion 頁面內容
  And 保留原有的 Page ID

Scenario: 同步失敗（API 限制）
  Given Notion API 達到速率限制
  When 執行同步
  Then 顯示錯誤訊息
  And 自動排入重試佇列
```

### Notion Database 欄位

| 欄位 | Notion 類型 | 說明 |
|------|------------|------|
| Name | Title | 文章標題 |
| URL | URL | 原始網址 |
| Source Type | Select | notion/medium/docs/web |
| Tags | Multi-select | 標籤 |
| Author | Rich text | 作者 |
| Published | Date | 發布日期 |
| Saved At | Date | 收藏日期 |
| Local ID | Number | 本地 SQLite ID |

### API 實作

```python
from notion_client import Client

class NotionSync:
    def __init__(self, api_key: str, database_id: str):
        self.client = Client(auth=api_key)
        self.database_id = database_id

    def sync_article(self, article: Article) -> str:
        """同步文章到 Notion，回傳 Page ID"""

        if article.notion_page_id:
            # 更新
            return self._update_page(article)
        else:
            # 新增
            return self._create_page(article)

    def _create_page(self, article: Article) -> str:
        response = self.client.pages.create(
            parent={"database_id": self.database_id},
            properties=self._build_properties(article),
            children=self._markdown_to_blocks(article.content)
        )
        return response["id"]
```

---

## 優先級

| User Story | 優先級 | Phase |
|------------|--------|-------|
| 3.1 SQLite 儲存 | P0 | Phase 1 |
| 3.2 ChromaDB 向量儲存 | P1 | Phase 3 |
| 3.3 Notion 同步 | P1 | Phase 3 |
