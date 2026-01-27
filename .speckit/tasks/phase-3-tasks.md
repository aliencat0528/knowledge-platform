# Phase 3 Tasks - 智慧搜尋

> Phase 3 實作向量搜尋和 Notion 同步功能。

---

## 完成狀態總覽

| Task | 功能 | 分支 | 狀態 |
|------|------|------|------|
| 3.1 | ChromaDB 整合 | `feature/vector-search-eighth` | ✅ 完成 |
| 3.2 | Embedding Service | `feature/vector-search-eighth` | ✅ 完成 |
| 3.3 | 語意搜尋 API | `feature/vector-search-eighth` | ✅ 完成 |
| 3.4 | 批量向量化腳本 | `feature/vector-search-eighth` | ✅ 完成 |
| 3.5 | 自動向量化 | `feature/vector-search-eighth` | ✅ 完成 |
| 3.6 | Notion 同步服務 | `feature/notion-sync-ninth` | ✅ 完成 |
| 3.7 | Notion 同步 API | `feature/notion-sync-ninth` | ✅ 完成 |
| 3.8 | Notion 認證設定 | `feature/notion-sync-ninth` | ✅ 完成 |

---

# feature/vector-search-eighth 分支任務

## Task 3.1: ChromaDB 整合

### 描述
設定 ChromaDB 向量資料庫，提供向量儲存和查詢功能

### 輸出
- `storage/vector.py`

### 功能
```python
class VectorStore:
    def __init__(self, path: str):
        """初始化 ChromaDB 持久化客戶端"""
        pass

    async def add(self, article_id: int, embedding: list[float], metadata: dict):
        """新增文章向量"""
        pass

    async def query(self, embedding: list[float], n_results: int = 5) -> list[dict]:
        """查詢相似向量"""
        pass

    async def delete(self, article_id: int):
        """刪除文章向量"""
        pass

    async def get_count(self) -> int:
        """取得向量數量"""
        pass
```

### 驗證
```python
from storage.vector import VectorStore

store = VectorStore("./data/chroma")
# 應該成功初始化
# 可以新增、查詢、刪除向量
```

### 相依
- 無

---

## Task 3.2: Embedding Service

### 描述
實作文章內容向量化服務，支援 OpenAI Embedding API

### 輸出
- `services/embed_service.py`

### 功能
```python
class EmbedService:
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        """初始化 OpenAI 客戶端"""
        pass

    async def embed_text(self, text: str) -> list[float]:
        """將文字轉換為向量"""
        pass

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量向量化（最多 2048 個）"""
        pass

    def chunk_content(self, content: str, max_tokens: int = 8000) -> list[str]:
        """將長文章分割成適合 embedding 的 chunks"""
        pass
```

### 驗證
```bash
# 需要 OPENAI_API_KEY
python -c "
from packages.server.services.embed_service import EmbedService
import asyncio

async def test():
    service = EmbedService('sk-...')
    vec = await service.embed_text('Hello World')
    print(f'Vector length: {len(vec)}')  # 應該是 1536

asyncio.run(test())
"
```

### 相依
- Task 3.1

---

## Task 3.3: 語意搜尋 API

### 描述
實作語意搜尋 API 端點

### 輸出
- 更新 `api/search.py`
- 更新 `storage/models.py`

### API 端點
```yaml
POST /api/v1/search/semantic
Content-Type: application/json

{
  "query": "如何在 React 中管理狀態",
  "limit": 10,
  "threshold": 0.7
}

# 回應
{
  "success": true,
  "data": {
    "results": [
      {
        "id": 123,
        "title": "useState Hook 教學",
        "snippet": "...",
        "similarity": 0.89,
        "source_type": "docs",
        "url": "..."
      }
    ],
    "total": 5
  }
}
```

### 驗證
```bash
curl -X POST http://localhost:8000/api/v1/search/semantic \
  -H "Content-Type: application/json" \
  -d '{"query": "React 狀態管理", "limit": 5}'
```

### 相依
- Task 3.1
- Task 3.2

---

## Task 3.4: 批量向量化腳本

### 描述
提供 CLI 工具批量向量化所有未向量化的文章

### 輸出
- `scripts/embed_all.py`

### 使用方式
```bash
# 向量化所有未處理文章
python scripts/embed_all.py

# 重新向量化全部
python scripts/embed_all.py --force

# 只處理指定數量
python scripts/embed_all.py --limit 100

# 預覽模式
python scripts/embed_all.py --preview
```

### 功能
- 讀取 SQLite 中 `is_embedded = False` 的文章
- 批量呼叫 Embedding API
- 儲存到 ChromaDB
- 更新 SQLite 的 `is_embedded` 欄位
- 顯示進度

### 驗證
```bash
# 先匯入一些文章
python scripts/import_zip.py ~/Downloads/Export.zip

# 執行向量化
python scripts/embed_all.py --preview  # 預覽
python scripts/embed_all.py            # 執行

# 確認結果
sqlite3 data/knowledge.db "SELECT COUNT(*) FROM articles WHERE is_embedded = 1"
```

### 相依
- Task 3.2
- Task 3.3

---

## Task 3.5: 自動向量化

### 描述
新文章匯入時自動向量化

### 輸出
- 更新 `services/import_service.py`

### 功能
- 在 `import_article()` 成功後觸發向量化
- 可透過設定開關（`AUTO_EMBED=true`）
- 向量化失敗不影響文章儲存

### 驗證
```bash
# 設定環境變數
export AUTO_EMBED=true

# 透過 API 匯入文章
curl -X POST http://localhost:8000/api/v1/articles \
  -H "Content-Type: application/json" \
  -d '{"source_type": "web", "source_id": "test", "title": "Test", "content": "..."}'

# 確認已向量化
sqlite3 data/knowledge.db "SELECT is_embedded FROM articles WHERE source_id = 'test'"
```

### 相依
- Task 3.2

---

# Phase 3 第一分支完成條件

```
□ ChromaDB 可正常初始化和查詢
□ 可將文章轉換為向量
□ 語意搜尋 API 可用
□ 批量向量化腳本可用
□ 新文章可選擇自動向量化
```

---

# 預估時間

| Task | 時間 |
|------|------|
| 3.1 ChromaDB 整合 | 1 hr |
| 3.2 Embedding Service | 1.5 hr |
| 3.3 語意搜尋 API | 1.5 hr |
| 3.4 批量向量化腳本 | 1 hr |
| 3.5 自動向量化 | 1 hr |
| **vector-search-eighth 合計** | **~6 小時** |

---

# feature/notion-sync-ninth 分支任務

## Task 3.6: Notion 同步服務 ✅

### 描述
實作將文章同步到 Notion Database 的服務

### 輸出
- `services/notion_sync.py`

### 功能
```python
class NotionSync:
    def __init__(self, api_key: str, database_id: str):
        """初始化 Notion 客戶端"""
        pass

    async def sync_article(self, db: Database, article_id: int) -> dict:
        """同步單篇文章到 Notion"""
        pass

    async def batch_sync(self, db: Database, article_ids: list[int] | None = None, limit: int = 10) -> dict:
        """批量同步文章"""
        pass

    async def get_sync_status(self, db: Database) -> dict:
        """取得同步狀態統計"""
        pass
```

### 驗證
```bash
# 設定環境變數
export NOTION_API_KEY=secret_...
export NOTION_DATABASE_ID=...

# 透過 API 同步
curl -X POST http://localhost:8000/api/v1/sync/notion \
  -H "Content-Type: application/json" \
  -d '{"article_id": 1}'
```

### 相依
- Phase 1a（文章儲存）

---

## Task 3.7: Notion 同步 API ✅

### 描述
提供 Notion 同步的 API 端點

### 輸出
- `api/sync.py`

### API 端點
```yaml
# 同步單篇文章
POST /api/v1/sync/notion
Content-Type: application/json

{
  "article_id": 123
}

# 回應
{
  "success": true,
  "article_id": 123,
  "notion_page_id": "abc123...",
  "notion_url": "https://notion.so/...",
  "synced_at": "2026-01-27T12:30:00Z"
}

# 批量同步
POST /api/v1/sync/notion/batch
{
  "article_ids": [1, 2, 3],  # 可選
  "limit": 10
}

# 同步狀態
GET /api/v1/sync/status

# 移除同步資訊
DELETE /api/v1/sync/notion/{article_id}
```

### 相依
- Task 3.6

---

## Task 3.8: Notion 認證設定 ✅

### 描述
配置 Notion API 認證流程

### 輸出
- 更新 `.env.example`
- 更新 `config.py`（已預設）

### 設定方式

#### 1. 建立 Notion Integration

1. 前往 https://www.notion.so/my-integrations
2. 點擊 "New integration"
3. 填寫名稱（如 "Knowledge Platform"）
4. 選擇 Workspace
5. 點擊 "Submit"
6. 複製 "Internal Integration Token"

#### 2. 建立 Notion Database

建立一個 Database 並包含以下欄位：

| 欄位名稱 | 類型 | 說明 |
|---------|------|------|
| Name | Title | 文章標題 |
| URL | URL | 文章連結 |
| Source Type | Select | 來源類型（notion/web/docs/medium） |
| Tags | Multi-select | 標籤 |
| Author | Rich text | 作者 |
| Published | Date | 發布日期 |
| Saved At | Date | 儲存日期 |
| Local ID | Number | 本地文章 ID |

#### 3. 分享 Database 給 Integration

1. 開啟 Database 頁面
2. 點擊右上角 "..." → "Connections"
3. 搜尋並選擇你的 Integration
4. 點擊 "Confirm"

#### 4. 設定環境變數

```bash
# .env
NOTION_API_KEY=secret_abc123...
NOTION_DATABASE_ID=12a34b56c78d...
```

Database ID 可從 URL 取得：
`https://notion.so/<workspace>/<database_id>?v=...`

### 驗證
```bash
# 檢查同步狀態
curl http://localhost:8000/api/v1/sync/status

# 應該回傳 configured: true
```

---

# Phase 3 第二分支完成條件

```
✅ Notion 同步服務可正常運作
✅ 可同步單篇文章到 Notion
✅ 可批量同步文章
✅ 同步狀態 API 可查詢
✅ 認證設定文件完整
```

---

# Phase 3 合計預估時間

| Task | 時間 |
|------|------|
| 3.1 ChromaDB 整合 | 1 hr ✅ |
| 3.2 Embedding Service | 1.5 hr ✅ |
| 3.3 語意搜尋 API | 1.5 hr ✅ |
| 3.4 批量向量化腳本 | 1 hr ✅ |
| 3.5 自動向量化 | 1 hr ✅ |
| 3.6 Notion 同步服務 | 2 hr ✅ |
| 3.7 Notion 同步 API | 1 hr ✅ |
| 3.8 Notion 認證設定 | 0.5 hr ✅ |
| **Phase 3 合計** | **~9.5 小時** |
