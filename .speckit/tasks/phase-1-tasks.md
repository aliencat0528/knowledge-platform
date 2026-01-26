# Phase 1 Tasks - 核心基礎

> Phase 1 目標：可以透過擴充套件收藏單頁，存入本地 SQLite

---

## Task 1.1: 專案初始化

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

## Task 1.2: SQLite 資料庫層

### 描述
實作 SQLite 資料庫操作層

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
# 應該包含所有表格
```

### 相依
- Task 1.1

### 估計時間
1 小時

---

## Task 1.3: Pydantic Models

### 描述
定義 API 請求/回應的資料模型

### 輸入
- API 設計（technical-plan.md）

### 輸出
- storage/models.py（擴充）
  - ArticleCreate
  - ArticleResponse
  - ArticleBatchCreate
  - ImportResult
  - SearchQuery
  - SearchResult

### 驗證
```python
from storage.models import ArticleCreate
article = ArticleCreate(
    source_type="web",
    source_id="test",
    title="Test",
    content="# Test"
)
# 應該正常建立
```

### 相依
- Task 1.2

### 估計時間
30 分鐘

---

## Task 1.4: Generic Parser

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
- Task 1.1

### 估計時間
1 小時

---

## Task 1.5: Import Service

### 描述
實作文章匯入服務（含去重邏輯）

### 輸入
- 去重邏輯定義（epic-2-data-processing.md）

### 輸出
- services/import_service.py
  - import_article()
  - import_batch()
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
- Task 1.2
- Task 1.3

### 估計時間
1.5 小時

---

## Task 1.6: FastAPI 基礎設定

### 描述
設定 FastAPI 應用程式和基礎端點

### 輸入
- API 設計（technical-plan.md）

### 輸出
- main.py
- api/__init__.py
- api/articles.py（POST /articles）

### 驗證
```bash
uvicorn main:app --reload

# 測試健康檢查
curl http://localhost:8000/api/v1/health
# 應該回傳 {"status": "ok"}

# 測試新增文章
curl -X POST http://localhost:8000/api/v1/articles \
  -H "Content-Type: application/json" \
  -d '{"source_type": "web", "source_id": "test", "title": "Test", "content": "# Test"}'
# 應該回傳成功
```

### 相依
- Task 1.5

### 估計時間
1 小時

---

## Task 1.7: 擴充套件骨架

### 描述
建立 Chrome Extension 基礎結構

### 輸入
- 專案結構定義

### 輸出
- packages/extension/manifest.json
- packages/extension/popup/index.html
- packages/extension/popup/popup.ts
- packages/extension/background/service-worker.ts

### 驗證
1. 在 Chrome 載入未封裝的擴充功能
2. 點擊擴充功能圖示
3. 應該顯示 Popup UI

### 相依
- 無

### 估計時間
1 小時

---

## Task 1.8: 擴充套件內容提取

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
- Task 1.7

### 估計時間
1.5 小時

---

## Task 1.9: 擴充套件 API 整合

### 描述
將擴充套件與後端 API 整合

### 輸入
- API 端點定義

### 輸出
- packages/extension/popup/popup.ts（更新）
- packages/extension/background/service-worker.ts（更新）

### 驗證
1. 啟動後端服務
2. 瀏覽任意網頁
3. 點擊擴充套件「收藏此頁」
4. 確認文章存入 SQLite

### 相依
- Task 1.6
- Task 1.8

### 估計時間
1 小時

---

## Task 1.10: 錯誤處理與提示

### 描述
完善錯誤處理和使用者提示

### 輸入
- 錯誤情境定義

### 輸出
- 擴充套件：錯誤提示 UI
- 後端：統一錯誤回應

### 驗證
1. 後端未啟動時，顯示「請先啟動服務」
2. 收藏成功時，顯示「收藏成功」
3. 重複收藏時，顯示「已存在」或「已更新」

### 相依
- Task 1.9

### 估計時間
45 分鐘

---

## Phase 1 完成條件

```
✅ 後端服務可啟動
✅ 擴充套件可載入
✅ 可收藏當前網頁
✅ 資料存入 SQLite
✅ 重複收藏正確處理
✅ 錯誤有友善提示
```

---

## 任務依賴圖

```
Task 1.1 (專案初始化)
    │
    ├── Task 1.2 (SQLite)
    │       │
    │       └── Task 1.3 (Models)
    │               │
    │               └── Task 1.5 (Import Service)
    │                       │
    │                       └── Task 1.6 (FastAPI)
    │                               │
    │                               └── Task 1.9 (整合)
    │                                       │
    │                                       └── Task 1.10 (錯誤處理)
    │
    └── Task 1.4 (Generic Parser)
            │
            └── (被 Task 1.5 使用)

Task 1.7 (擴充套件骨架)
    │
    └── Task 1.8 (內容提取)
            │
            └── Task 1.9 (整合)
```

---

## 預估總時間

| Task | 時間 |
|------|------|
| 1.1 專案初始化 | 30 min |
| 1.2 SQLite | 1 hr |
| 1.3 Models | 30 min |
| 1.4 Generic Parser | 1 hr |
| 1.5 Import Service | 1.5 hr |
| 1.6 FastAPI | 1 hr |
| 1.7 擴充套件骨架 | 1 hr |
| 1.8 內容提取 | 1.5 hr |
| 1.9 整合 | 1 hr |
| 1.10 錯誤處理 | 45 min |
| **合計** | **~10 小時** |
