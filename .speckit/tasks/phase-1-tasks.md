# Phase 1 Tasks - 核心基礎 + Notion 樹狀

> Phase 1 分為兩個 Milestone：
> - **Phase 1a**：核心可用（單頁收藏 + API 文件）
> - **Phase 1b**：Notion 樹狀抓取（優先功能）

---

# Phase 1a: 核心基礎

> 目標：可以透過擴充套件收藏單頁，存入本地 SQLite

---

## Task 1a.1: 專案初始化

### 描述
設定 Python 後端專案結構和依賴

### 輸入
- 技術計畫中的專案結構

### 輸出
- pyproject.toml
- requirements.txt
- packages/server/ 目錄結構
- config.py

### 驗證
```bash
cd packages/server
pip install -r requirements.txt
python -c "from config import settings; print(settings)"
# 應該正常執行
```

### 估計時間
30 分鐘

---

## Task 1a.2: SQLite 資料庫層

### 描述
實作 SQLite 資料庫操作層（含 article_hierarchy 表）

### 輸入
- Schema 定義（epic-3-storage.md）

### 輸出
- storage/database.py
- storage/models.py
- scripts/setup_db.py

### 驗證
```bash
python scripts/setup_db.py
# 應該建立 data/knowledge.db
# 應該包含：articles, article_history, article_hierarchy, import_batches
```

### 相依
- Task 1a.1

### 估計時間
1 小時

---

## Task 1a.3: Pydantic Models

### 描述
定義 API 請求/回應的資料模型

### 輸入
- API 設計（technical-plan.md）

### 輸出
- storage/models.py（擴充）
  - ArticleCreate
  - ArticleResponse
  - ArticleBatchCreate
  - ArticleTreeCreate（for Phase 1b）
  - ImportResult
  - SearchQuery
  - SearchResult
  - ErrorResponse

### 驗證
```python
from storage.models import ArticleCreate, ErrorResponse
article = ArticleCreate(
    source_type="web",
    source_id="test",
    title="Test",
    content="# Test"
)
# 應該正常建立
```

### 相依
- Task 1a.2

### 估計時間
30 分鐘

---

## Task 1a.4: Generic Parser

### 描述
實作通用網頁內容解析器

### 輸入
- Parser 介面定義（epic-2-data-processing.md）

### 輸出
- parsers/base.py（BaseParser 抽象類）
- parsers/generic.py（GenericParser 實作）

### 驗證
```python
from parsers.generic import GenericParser

parser = GenericParser()
html = "<html><body><article><h1>Title</h1><p>Content</p></article></body></html>"
result = parser.parse(html, "https://example.com/article")

assert result.title == "Title"
assert "Content" in result.content
```

### 相依
- Task 1a.1

### 估計時間
1 小時

---

## Task 1a.5: Import Service

### 描述
實作文章匯入服務（含去重邏輯）

### 輸入
- 去重邏輯定義（epic-2-data-processing.md）

### 輸出
- services/import_service.py
  - import_article()
  - import_batch()
  - import_tree()（預留 for Phase 1b）
  - _calculate_hash()
  - _check_duplicate()

### 驗證
```python
from services.import_service import ImportService

service = ImportService(db)

# 新增
result1 = service.import_article(source_type="web", source_id="1", ...)
assert result1.status == "new"

# 重複
result2 = service.import_article(source_type="web", source_id="1", ...)
assert result2.status == "skipped"

# 更新
result3 = service.import_article(source_type="web", source_id="1", content="new content", ...)
assert result3.status == "updated"
```

### 相依
- Task 1a.2
- Task 1a.3

### 估計時間
1.5 小時

---

## Task 1a.6: FastAPI 基礎設定

### 描述
設定 FastAPI 應用程式、基礎端點、統一錯誤處理

### 輸入
- API 設計（technical-plan.md）
- 錯誤格式（epic-5-integration.md）

### 輸出
- main.py
- api/__init__.py
- api/articles.py（POST /articles, POST /articles/batch）
- api/health.py（GET /health）
- middleware/error_handler.py

### 驗證
```bash
uvicorn main:app --reload

# 健康檢查
curl http://localhost:8000/api/v1/health
# {"status": "ok"}

# API 文件
curl http://localhost:8000/docs
# 應該回傳 Swagger UI HTML

# 新增文章
curl -X POST http://localhost:8000/api/v1/articles \
  -H "Content-Type: application/json" \
  -d '{"source_type": "web", "source_id": "test", "title": "Test", "content": "# Test"}'
# 應該回傳成功
```

### 相依
- Task 1a.5

### 估計時間
1 小時

---

## Task 1a.7: 擴充套件骨架

### 描述
建立 Chrome Extension 基礎結構（含 Notion 偵測邏輯）

### 輸入
- 專案結構定義
- Notion 偵測規則（epic-1-data-collection.md）

### 輸出
- packages/extension/manifest.json
- packages/extension/popup/index.html
- packages/extension/popup/popup.ts
- packages/extension/background/service-worker.ts
- packages/extension/utils/notion-detector.ts

### 驗證
1. 在 Chrome 載入未封裝的擴充功能
2. 點擊擴充功能圖示
3. 應該顯示 Popup UI
4. 在 Notion 頁面應該顯示 "Notion 頁面偵測到"

### 相依
- 無

### 估計時間
1 小時

---

## Task 1a.8: 擴充套件內容提取

### 描述
實作擴充套件的內容提取功能

### 輸入
- Readability.js
- Turndown.js

### 輸出
- packages/extension/content/extractor.ts
- packages/extension/lib/readability.min.js
- packages/extension/lib/turndown.min.js

### 驗證
1. 在任意網頁執行內容提取
2. 應該回傳 { title, content, url }
3. content 應該是 Markdown 格式

### 相依
- Task 1a.7

### 估計時間
1.5 小時

---

## Task 1a.9: 擴充套件 API 整合

### 描述
將擴充套件與後端 API 整合

### 輸入
- API 端點定義

### 輸出
- packages/extension/popup/popup.ts（更新）
- packages/extension/background/service-worker.ts（更新）
- packages/extension/api/client.ts

### 驗證
1. 啟動後端服務
2. 瀏覽任意網頁
3. 點擊擴充套件「收藏此頁」
4. 確認文章存入 SQLite

### 相依
- Task 1a.6
- Task 1a.8

### 估計時間
1 小時

---

## Task 1a.10: 錯誤處理與提示

### 描述
完善錯誤處理和使用者提示

### 輸入
- 錯誤情境定義
- 統一錯誤格式（epic-5-integration.md）

### 輸出
- 擴充套件：錯誤提示 UI
- 後端：統一錯誤回應

### 驗證
1. 後端未啟動時，顯示「請先啟動服務」
2. 收藏成功時，顯示「收藏成功」
3. 重複收藏時，顯示「已存在」或「已更新」

### 相依
- Task 1a.9

### 估計時間
45 分鐘

---

# Phase 1a 完成條件

```
✅ 後端服務可啟動
✅ /docs 可查看 API 文件
✅ 擴充套件可載入
✅ 可收藏當前網頁（一般網頁）
✅ 資料存入 SQLite
✅ 重複收藏正確處理
✅ 錯誤有友善提示
✅ Notion 頁面可偵測（顯示不同 UI）
```

---

# Phase 1b: Notion 樹狀抓取

> 目標：可以一鍵收藏 Notion 頁面及所有子頁面

---

## Task 1b.1: Notion Parser

### 描述
實作 Notion 頁面專用解析器

### 輸入
- Notion 頁面結構分析
- Parser 介面（parsers/base.py）

### 輸出
- parsers/notion.py
  - parse_page() - 解析單頁內容
  - extract_sub_pages() - 提取子頁面連結
  - get_page_id() - 從 URL 提取頁面 ID

### 驗證
```python
from parsers.notion import NotionParser

parser = NotionParser()
# 測試用 Notion HTML
result = parser.parse(notion_html, "https://notion.so/xxx")

assert result.title is not None
assert result.source_id is not None  # 32-char page ID
assert isinstance(result.sub_pages, list)
```

### 相依
- Task 1a.4（BaseParser）

### 估計時間
1.5 小時

---

## Task 1b.2: 樹狀匯入 API

### 描述
實作樹狀結構的匯入 API

### 輸入
- Import Service
- article_hierarchy 表

### 輸出
- api/articles.py（新增 POST /articles/tree）
- services/import_service.py（更新 import_tree）

### API 規格
```yaml
POST /api/v1/articles/tree
{
  "root": {
    "source_type": "notion",
    "source_id": "page-id",
    "title": "Parent Page",
    "content": "..."
  },
  "children": [
    {
      "source_type": "notion",
      "source_id": "child-id-1",
      "title": "Child Page 1",
      "content": "...",
      "children": []  # 可遞迴
    }
  ]
}
```

### 驗證
```bash
curl -X POST http://localhost:8000/api/v1/articles/tree \
  -H "Content-Type: application/json" \
  -d '{"root": {...}, "children": [...]}'

# 檢查 article_hierarchy 有正確記錄
```

### 相依
- Task 1a.5
- Task 1a.6

### 估計時間
1 小時

---

## Task 1b.3: 擴充套件子頁面掃描

### 描述
在擴充套件中實作 Notion 子頁面掃描功能

### 輸入
- Notion DOM 結構分析
- Content Script 權限

### 輸出
- packages/extension/content/notion-scanner.ts
  - scanSubPages() - 掃描當前頁面的子頁面連結
  - getPageTitle() - 取得頁面標題
  - getPageId() - 取得頁面 ID

### 驗證
1. 在有子頁面的 Notion 頁面執行
2. 應該回傳子頁面列表
3. 每個子頁面包含 { url, title, id }

### 相依
- Task 1a.7

### 估計時間
1.5 小時

---

## Task 1b.4: 擴充套件樹狀 UI

### 描述
實作 Notion 樹狀收藏的 UI

### 輸入
- UI 規格（epic-1-data-collection.md）

### 輸出
- packages/extension/popup/notion-tree.ts
- packages/extension/popup/notion-tree.css

### UI 功能
- 顯示子頁面列表（checkbox）
- 全選/取消全選
- 「只收藏此頁」按鈕
- 「收藏此頁 + 勾選的子頁面」按鈕

### 驗證
1. 在 Notion 頁面打開擴充套件
2. 應該顯示子頁面列表
3. 可以勾選/取消子頁面
4. 按鈕正確觸發對應動作

### 相依
- Task 1b.3

### 估計時間
1 小時

---

## Task 1b.5: 樹狀遍歷與抓取

### 描述
實作遞迴抓取 Notion 子頁面的邏輯

### 輸入
- BFS/DFS 遍歷演算法
- visited set 避免循環

### 輸出
- packages/extension/background/tree-crawler.ts
  - crawlTree() - 遞迴抓取
  - buildHierarchy() - 建立樹狀結構

### 驗證
```javascript
// 模擬測試
const result = await crawlTree({
  rootUrl: "https://notion.so/page-a",
  selectedChildren: ["page-b", "page-c"],
  maxDepth: 3
});

// 應該回傳樹狀結構
// 循環引用應該被跳過
```

### 相依
- Task 1b.1（NotionParser）
- Task 1b.3（scanner）

### 估計時間
1.5 小時

---

## Task 1b.6: 進度顯示

### 描述
實作抓取進度的即時顯示

### 輸入
- 進度 UI 規格（epic-1-data-collection.md）

### 輸出
- packages/extension/popup/progress.ts
- packages/extension/popup/progress.css

### 功能
- 進度條（x/total）
- 目前抓取的頁面名稱
- 已完成、進行中、等待中狀態
- 可取消按鈕

### 驗證
1. 開始樹狀抓取
2. 顯示進度條和狀態
3. 完成後顯示統計

### 相依
- Task 1b.5

### 估計時間
45 分鐘

---

## Task 1b.7: 整合測試

### 描述
完整流程的整合測試

### 輸入
- 所有 Phase 1b 組件

### 輸出
- 完整可用的 Notion 樹狀抓取功能
- tests/test_notion_tree.py

### 驗證
1. 在真實 Notion 頁面（有子頁面）測試
2. 選擇部分子頁面收藏
3. 確認所有頁面正確存入
4. 確認父子關係正確
5. 確認重複抓取正確處理

### 相依
- Task 1b.2
- Task 1b.4
- Task 1b.5
- Task 1b.6

### 估計時間
1 小時

---

# Phase 1b 完成條件

```
✅ 擴充套件在 Notion 頁面顯示樹狀 UI
✅ 可掃描並列出子頁面
✅ 可選擇性勾選子頁面
✅ 可一鍵抓取選中頁面
✅ 顯示抓取進度
✅ 父子關係正確儲存
✅ 循環引用不會造成問題
✅ 重複抓取正確處理（跳過/更新）
```

---

# 任務依賴圖

```
Phase 1a:
─────────
Task 1a.1 (專案初始化)
    │
    ├── Task 1a.2 (SQLite) ─── Task 1a.3 (Models) ─── Task 1a.5 (Import) ─── Task 1a.6 (FastAPI)
    │                                                                              │
    └── Task 1a.4 (Generic Parser) ────────────────────────────────────────────────┘
                                                                                   │
Task 1a.7 (Extension 骨架) ─── Task 1a.8 (內容提取) ───────────────────── Task 1a.9 (整合)
                                                                              │
                                                                        Task 1a.10 (錯誤處理)

Phase 1b:
─────────
Task 1a.4 (BaseParser)
    │
    └── Task 1b.1 (NotionParser)
            │
            └── Task 1b.5 (樹狀遍歷)
                    │
Task 1a.5 + 1a.6    │
    │               │
    └── Task 1b.2 (樹狀 API)
                    │
Task 1a.7           │
    │               │
    └── Task 1b.3 (子頁面掃描) ─── Task 1b.4 (樹狀 UI)
                                        │
                                        └── Task 1b.5 ─── Task 1b.6 (進度) ─── Task 1b.7 (整合測試)
```

---

# 預估總時間

## Phase 1a

| Task | 時間 |
|------|------|
| 1a.1 專案初始化 | 30 min |
| 1a.2 SQLite | 1 hr |
| 1a.3 Models | 30 min |
| 1a.4 Generic Parser | 1 hr |
| 1a.5 Import Service | 1.5 hr |
| 1a.6 FastAPI | 1 hr |
| 1a.7 擴充套件骨架 | 1 hr |
| 1a.8 內容提取 | 1.5 hr |
| 1a.9 整合 | 1 hr |
| 1a.10 錯誤處理 | 45 min |
| **Phase 1a 合計** | **~10 小時** |

## Phase 1b

| Task | 時間 |
|------|------|
| 1b.1 Notion Parser | 1.5 hr |
| 1b.2 樹狀 API | 1 hr |
| 1b.3 子頁面掃描 | 1.5 hr |
| 1b.4 樹狀 UI | 1 hr |
| 1b.5 樹狀遍歷 | 1.5 hr |
| 1b.6 進度顯示 | 45 min |
| 1b.7 整合測試 | 1 hr |
| **Phase 1b 合計** | **~8 小時** |

## 總計

| Phase | 時間 |
|-------|------|
| Phase 1a | ~10 小時 |
| Phase 1b | ~8 小時 |
| **Phase 1 總計** | **~18 小時** |
