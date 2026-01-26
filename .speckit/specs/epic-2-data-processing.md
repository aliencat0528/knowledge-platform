# Epic 2: 資料處理 (Data Processing)

> 本文件定義資料處理相關的所有功能規格。

---

## User Story 2.1: 內容解析

### 描述
```
作為系統
我需要解析不同網站的內容
這樣才能提取出乾淨、結構化的文章
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: 解析一般網頁
  Given 收到一個網頁的 HTML
  When 執行內容解析
  Then 提取主要文章內容（排除導覽、廣告、頁尾）
  And 轉換成 Markdown 格式
  And 保留程式碼區塊（含語言標記）
  And 保留圖片連結
  And 提取 metadata（標題、作者、日期）

Scenario: 解析 Notion 頁面
  Given 收到 Notion 頁面的 HTML
  When 執行 Notion Parser
  Then 正確解析 Notion 特有的區塊
  And 保留 Toggle、Callout 等特殊格式
  And 提取子頁面連結

Scenario: 解析 Medium 文章
  Given 收到 Medium 文章的 HTML
  When 執行 Medium Parser
  Then 繞過付費牆提示（如果可能）
  And 提取完整文章內容
  And 提取作者資訊和標籤
```

### Parser 介面定義

```python
from abc import ABC, abstractmethod
from pydantic import BaseModel

class ParsedContent(BaseModel):
    title: str
    content: str  # Markdown
    author: str | None
    published_at: datetime | None
    tags: list[str]
    images: list[str]  # URLs
    child_pages: list[str]  # For Notion

class BaseParser(ABC):
    @abstractmethod
    def can_parse(self, url: str) -> bool:
        """判斷此 Parser 是否能處理該 URL"""
        pass

    @abstractmethod
    def parse(self, html: str, url: str) -> ParsedContent:
        """解析 HTML 並回傳結構化內容"""
        pass
```

### 支援的 Parser

| Parser | 網站 | 優先級 |
|--------|------|--------|
| GenericParser | 所有網站（fallback） | P0 |
| NotionParser | notion.so | P0 |
| MediumParser | medium.com | P2 |
| DevToParser | dev.to | P2 |
| DocsParser | react.dev, vuejs.org 等 | P2 |

---

## User Story 2.2: 去重比對

### 描述
```
作為系統
我需要偵測重複的文章
這樣才能避免重複儲存相同內容
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: 完全相同的文章
  Given 資料庫中已有文章 A (source_type=web, source_id=abc123)
  When 嘗試新增相同 source_type 和 source_id 的文章
  And content_hash 相同
  Then 回傳 status="skipped"
  And 不新增也不更新

Scenario: 相同來源但內容更新
  Given 資料庫中已有文章 A (content_hash=hash1)
  When 嘗試新增相同來源的文章
  And content_hash 不同 (hash2)
  Then 更新文章內容
  And version += 1
  And 記錄到 article_history
  And 回傳 status="updated"

Scenario: 全新文章
  Given 資料庫中沒有相同 source_type + source_id 的文章
  When 新增文章
  Then 建立新記錄
  And 回傳 status="new"
```

### 比對邏輯

```python
def deduplicate(article: ArticleInput) -> DedupeResult:
    # 1. 計算 content_hash
    content_hash = md5(article.content)

    # 2. 查詢是否已存在
    existing = db.query(
        "SELECT * FROM articles WHERE source_type=? AND source_id=?",
        (article.source_type, article.source_id)
    )

    if not existing:
        return DedupeResult(action="insert", reason="new")

    if existing.content_hash == content_hash:
        return DedupeResult(action="skip", reason="identical")

    return DedupeResult(action="update", reason="content_changed")
```

---

## User Story 2.3: 版本追蹤

### 描述
```
作為使用者
我想要追蹤文章的修改歷史
這樣我可以看到文章的演變
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: 查看文章歷史
  Given 文章 A 已被更新過 3 次
  When 我查詢文章 A 的歷史
  Then 看到 3 筆歷史記錄
  And 每筆包含：舊內容、新內容、變更時間

Scenario: 回滾到舊版本
  Given 文章 A 目前是版本 3
  When 我選擇回滾到版本 1
  Then 文章內容恢復為版本 1
  And version 變成 4（不是 1）
  And 記錄此次回滾到 history
```

### 資料模型

```sql
CREATE TABLE article_history (
    id INTEGER PRIMARY KEY,
    article_id INTEGER REFERENCES articles(id),
    version INTEGER NOT NULL,
    old_content TEXT,
    new_content TEXT,
    old_hash TEXT,
    new_hash TEXT,
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    change_type TEXT  -- 'update', 'rollback'
);
```

---

## User Story 2.4: 向量化

### 描述
```
作為系統
我需要將文章內容向量化
這樣才能支援語意搜尋
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: 新文章自動向量化
  Given 新增一篇文章
  And 向量化功能已啟用
  When 文章儲存成功
  Then 自動呼叫 Embedding API
  And 將向量存入 ChromaDB
  And 標記 is_processed = True

Scenario: 批量向量化
  Given 有 100 篇文章尚未向量化
  When 執行批量向量化指令
  Then 逐批處理（每批 10 篇）
  And 顯示進度
  And 處理失敗的不影響其他
```

### 向量化設定

```python
EMBEDDING_CONFIG = {
    "provider": "openai",  # or "local"
    "model": "text-embedding-3-small",
    "dimensions": 1536,
    "batch_size": 10,
    "chunk_size": 1000,  # 每個 chunk 的字數
    "chunk_overlap": 100,
}
```

---

## 優先級

| User Story | 優先級 | Phase |
|------------|--------|-------|
| 2.1 內容解析 | P0 | Phase 1 |
| 2.2 去重比對 | P0 | Phase 1 |
| 2.3 版本追蹤 | P2 | Phase 2 |
| 2.4 向量化 | P1 | Phase 3 |
