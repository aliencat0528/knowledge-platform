# Knowledge Platform - 測試指南

> 本文件提供完整的測試檢查清單和測試指令。

---

## 目錄

1. [環境準備](#環境準備)
2. [API 測試指令](#api-測試指令)
3. [功能測試檢查清單](#功能測試檢查清單)
4. [整合測試流程](#整合測試流程)

---

## 環境準備

### 1. 啟動後端服務

```bash
# 進入專案目錄
cd knowledge-platform

# 啟動虛擬環境
source .venv/bin/activate

# 安裝依賴（如需要）
pip install -r packages/server/requirements.txt

# 啟動服務
cd packages/server
uvicorn main:app --reload

# 或從專案根目錄
python -m uvicorn packages.server.main:app --reload
```

### 2. 環境變數設定

```bash
# 複製範例設定
cp .env.example .env

# 編輯 .env 填入實際值
# 必要：
DATABASE_PATH=./data/knowledge.db
CHROMA_PATH=./data/chroma

# 語意搜尋 + Chat 需要：
OPENAI_API_KEY=sk-your-api-key

# Notion 同步需要：
NOTION_API_KEY=secret_your-notion-api-key
NOTION_DATABASE_ID=your-database-id
```

### 3. 確認服務狀態

```bash
# 健康檢查
curl http://localhost:8000/api/v1/health

# 預期回應：
# {"status":"ok","version":"0.1.0"}

# 系統統計
curl http://localhost:8000/api/v1/stats
```

---

## API 測試指令

### 文章 API

```bash
# 新增文章
curl -X POST http://localhost:8000/api/v1/articles \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "web",
    "source_id": "test-article-1",
    "title": "測試文章",
    "content": "# 測試內容\n\n這是一篇測試文章。",
    "url": "https://example.com/test"
  }'

# 列出文章
curl "http://localhost:8000/api/v1/articles?limit=10"

# 取得單篇文章
curl http://localhost:8000/api/v1/articles/1

# 更新文章
curl -X PUT http://localhost:8000/api/v1/articles/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "更新後的標題"}'

# 刪除文章
curl -X DELETE http://localhost:8000/api/v1/articles/1
```

### 匯入 API

```bash
# 匯入 Notion .zip
curl -X POST http://localhost:8000/api/v1/import/zip \
  -F "file=@/path/to/Export.zip"

# 預覽 .zip 內容
curl -X POST http://localhost:8000/api/v1/import/zip/preview \
  -F "file=@/path/to/Export.zip"

# 匯入 AI 對話（Markdown）
curl -X POST http://localhost:8000/api/v1/import/chat \
  -H "Content-Type: application/json" \
  -d '{
    "source": "markdown",
    "content": "## User\n如何使用 React?\n\n## Assistant\nReact 是..."
  }'
```

### 搜尋 API

```bash
# 關鍵字搜尋
curl "http://localhost:8000/api/v1/search?q=React"

# 語意搜尋（需要 OpenAI API Key + 已向量化的文章）
curl -X POST http://localhost:8000/api/v1/search/semantic \
  -H "Content-Type: application/json" \
  -d '{
    "query": "如何在前端管理狀態",
    "limit": 5
  }'
```

### Notion 同步 API

```bash
# 檢查同步狀態
curl http://localhost:8000/api/v1/sync/status

# 同步單篇文章
curl -X POST http://localhost:8000/api/v1/sync/notion \
  -H "Content-Type: application/json" \
  -d '{"article_id": 1}'

# 批量同步
curl -X POST http://localhost:8000/api/v1/sync/notion/batch \
  -H "Content-Type: application/json" \
  -d '{"limit": 10}'

# 移除同步資訊
curl -X DELETE http://localhost:8000/api/v1/sync/notion/1
```

### Chat API（RAG）

```bash
# 發送對話
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "如何使用 React Hooks?"
  }'

# 多輪對話（使用 conversation_id）
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "可以舉個例子嗎?",
    "conversation_id": "uuid-from-previous-response"
  }'

# 列出對話歷史
curl http://localhost:8000/api/v1/chat/history

# 取得單一對話
curl http://localhost:8000/api/v1/chat/history/{conversation_id}

# 刪除對話
curl -X DELETE http://localhost:8000/api/v1/chat/history/{conversation_id}
```

### Scheduler API（排程爬取）

```bash
# 啟動排程器
curl -X POST http://localhost:8000/api/v1/scheduler/start

# 查看排程器狀態
curl http://localhost:8000/api/v1/scheduler/status

# 建立排程任務
curl -X POST http://localhost:8000/api/v1/scheduler/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "每日抓取技術部落格",
    "url_pattern": "https://example.com/blog",
    "cron_expression": "0 9 * * *"
  }'

# 列出所有任務
curl "http://localhost:8000/api/v1/scheduler/tasks"

# 列出啟用中的任務
curl "http://localhost:8000/api/v1/scheduler/tasks?active_only=true"

# 取得單一任務
curl http://localhost:8000/api/v1/scheduler/tasks/1

# 更新任務
curl -X PUT http://localhost:8000/api/v1/scheduler/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{
    "cron_expression": "0 */6 * * *",
    "is_active": true
  }'

# 手動執行任務
curl -X POST http://localhost:8000/api/v1/scheduler/tasks/1/run

# 刪除任務
curl -X DELETE http://localhost:8000/api/v1/scheduler/tasks/1

# 停止排程器
curl -X POST http://localhost:8000/api/v1/scheduler/stop

# Cron 表達式格式：分 時 日 月 星期幾
# 範例：
# - "0 */6 * * *"   每 6 小時
# - "30 2 * * *"    每天凌晨 2:30
# - "0 9 * * 1"     每週一早上 9:00
# - "*/30 * * * *"  每 30 分鐘
```

---

## 功能測試檢查清單

### Phase 1: 核心基礎

#### 後端 API
- [ ] `GET /api/v1/health` 回傳 OK
- [ ] `GET /api/v1/stats` 顯示正確統計
- [ ] `POST /api/v1/articles` 可新增文章
- [ ] `GET /api/v1/articles` 可列出文章（分頁正確）
- [ ] `PUT /api/v1/articles/{id}` 可更新文章
- [ ] `DELETE /api/v1/articles/{id}` 可刪除文章

#### 擴充套件
- [ ] 擴充套件可正常載入
- [ ] 點擊「收藏」可儲存當前頁面
- [ ] 伺服器狀態指示正確（連線/斷線）
- [ ] Notion 頁面可正確偵測
- [ ] 子頁面可掃描並顯示

### Phase 2: 資料收集

#### .zip 匯入
- [ ] `POST /api/v1/import/zip` 可匯入 Notion Export
- [ ] 預覽模式顯示正確
- [ ] 重複內容正確處理（跳過/更新）
- [ ] CLI 腳本可用：`python scripts/import_zip.py`

#### AI 對話匯入
- [ ] Claude Code JSONL 格式可匯入
- [ ] Cursor SQLite 格式可匯入
- [ ] Markdown 格式可匯入
- [ ] CLI 腳本可用：`python scripts/import_chat.py`

#### 關鍵字搜尋
- [ ] `GET /api/v1/search?q=xxx` 可搜尋
- [ ] 結果包含高亮片段
- [ ] 篩選功能正確（source_type, tags）

### Phase 3: 智慧搜尋

#### 向量化
- [ ] `python scripts/embed_all.py --preview` 顯示待處理文章
- [ ] `python scripts/embed_all.py` 可批量向量化
- [ ] `AUTO_EMBED=true` 時新文章自動向量化
- [ ] ChromaDB 資料正確儲存

#### 語意搜尋
- [ ] `POST /api/v1/search/semantic` 可搜尋
- [ ] 結果按相似度排序
- [ ] threshold 篩選正確
- [ ] 無 API Key 時回傳 503

#### Notion 同步
- [ ] `GET /api/v1/sync/status` 顯示狀態
- [ ] `POST /api/v1/sync/notion` 可同步文章
- [ ] Notion 頁面正確建立
- [ ] 更新文章會更新 Notion
- [ ] 批量同步可用
- [ ] 無設定時回傳 503

### Phase 4: Chat RAG

#### Chat 功能
- [ ] `POST /api/v1/chat` 可對話
- [ ] 回答包含引用來源
- [ ] 多輪對話（conversation_id）正確
- [ ] 無 API Key 時回傳 503

#### 對話歷史
- [ ] `GET /api/v1/chat/history` 可列出對話
- [ ] `GET /api/v1/chat/history/{id}` 可取得對話詳情
- [ ] `DELETE /api/v1/chat/history/{id}` 可刪除對話
- [ ] 對話正確儲存到資料庫

#### 排程爬取
- [ ] `POST /api/v1/scheduler/start` 可啟動排程器
- [ ] `POST /api/v1/scheduler/tasks` 可建立任務
- [ ] `GET /api/v1/scheduler/tasks` 可列出任務
- [ ] `PUT /api/v1/scheduler/tasks/{id}` 可更新任務
- [ ] `DELETE /api/v1/scheduler/tasks/{id}` 可刪除任務
- [ ] `POST /api/v1/scheduler/tasks/{id}/run` 可手動執行
- [ ] `GET /api/v1/scheduler/status` 顯示正確狀態
- [ ] Cron 表達式驗證正確
- [ ] 任務按排程自動執行
- [ ] 執行結果正確儲存

---

## 整合測試流程

### 完整流程測試

```bash
# 1. 確認服務啟動
curl http://localhost:8000/api/v1/health

# 2. 新增測試文章
curl -X POST http://localhost:8000/api/v1/articles \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "docs",
    "source_id": "react-hooks-guide",
    "title": "React Hooks 完整指南",
    "content": "# React Hooks\n\n## useState\nuseState 是最基本的 Hook...\n\n## useEffect\nuseEffect 用於處理副作用...",
    "tags": ["react", "hooks", "frontend"]
  }'

# 3. 向量化文章
python scripts/embed_all.py

# 4. 測試語意搜尋
curl -X POST http://localhost:8000/api/v1/search/semantic \
  -H "Content-Type: application/json" \
  -d '{"query": "如何使用 React 管理狀態", "limit": 5}'

# 5. 測試 Chat（需要向量化後的文章）
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "React Hooks 有哪些？分別做什麼用？"}'

# 6. 測試多輪對話
# 使用上一步回傳的 conversation_id
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "詳細說明 useState 的使用方式",
    "conversation_id": "上一步的 conversation_id"
  }'

# 7. 檢查對話歷史
curl http://localhost:8000/api/v1/chat/history
```

### CLI 腳本測試

```bash
# .zip 匯入
python scripts/import_zip.py ~/Downloads/Export.zip --preview
python scripts/import_zip.py ~/Downloads/Export.zip

# AI 對話匯入
python scripts/import_chat.py ~/.claude/projects/my-project/conversations/ --preview
python scripts/import_chat.py ~/.claude/projects/my-project/conversations/

# 批量向量化
python scripts/embed_all.py --preview
python scripts/embed_all.py --limit 10
python scripts/embed_all.py --force
```

### 資料庫驗證

```bash
# 檢查文章數量
sqlite3 data/knowledge.db "SELECT COUNT(*) FROM articles"

# 檢查向量化狀態
sqlite3 data/knowledge.db "SELECT COUNT(*) FROM articles WHERE is_embedded = 1"

# 檢查 Notion 同步狀態
sqlite3 data/knowledge.db "SELECT COUNT(*) FROM articles WHERE notion_page_id IS NOT NULL"

# 檢查對話數量
sqlite3 data/knowledge.db "SELECT COUNT(*) FROM conversations"

# 檢查訊息數量
sqlite3 data/knowledge.db "SELECT COUNT(*) FROM messages"

# 檢查排程任務數量
sqlite3 data/knowledge.db "SELECT COUNT(*) FROM scheduled_tasks"

# 檢查啟用中的排程任務
sqlite3 data/knowledge.db "SELECT COUNT(*) FROM scheduled_tasks WHERE is_active = 1"
```

---

## 錯誤處理測試

### 預期錯誤回應

```bash
# 文章不存在
curl http://localhost:8000/api/v1/articles/99999
# 預期：404 {"code": "ARTICLE_NOT_FOUND", ...}

# 缺少必要欄位
curl -X POST http://localhost:8000/api/v1/articles \
  -H "Content-Type: application/json" \
  -d '{"title": "只有標題"}'
# 預期：422 驗證錯誤

# 無 OpenAI API Key 使用語意搜尋
# （先移除 OPENAI_API_KEY 環境變數）
curl -X POST http://localhost:8000/api/v1/search/semantic \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
# 預期：503 {"code": "...", "message": "... OPENAI_API_KEY ..."}

# 無 Notion 設定使用同步
curl -X POST http://localhost:8000/api/v1/sync/notion \
  -H "Content-Type: application/json" \
  -d '{"article_id": 1}'
# 預期：503 {"code": "NOTION_NOT_CONFIGURED", ...}
```

---

## 自動化測試

```bash
# 執行所有測試
pytest tests/

# 執行特定測試檔案
pytest tests/test_import.py

# 顯示覆蓋率
pytest --cov=packages/server

# 詳細輸出
pytest -v tests/
```

---

## 效能測試

### 批量匯入效能

```bash
# 準備大量測試資料
# 匯入並計時
time python scripts/import_zip.py large_export.zip

# 預期：1000 篇文章 < 1 分鐘
```

### 向量化效能

```bash
# 批量向量化計時
time python scripts/embed_all.py --limit 100

# 預期：100 篇文章 ~2-3 分鐘（受 API 限制）
```

### 搜尋效能

```bash
# 關鍵字搜尋
time curl "http://localhost:8000/api/v1/search?q=React"
# 預期：< 100ms

# 語意搜尋
time curl -X POST http://localhost:8000/api/v1/search/semantic \
  -H "Content-Type: application/json" \
  -d '{"query": "React", "limit": 10}'
# 預期：< 2s（含 embedding 生成）
```

---

## 常見問題

### Q: 語意搜尋沒有結果？

1. 確認文章已向量化：
   ```bash
   sqlite3 data/knowledge.db "SELECT COUNT(*) FROM articles WHERE is_embedded = 1"
   ```
2. 執行向量化：
   ```bash
   python scripts/embed_all.py
   ```

### Q: Chat 回答不包含知識庫內容？

1. 確認有向量化的文章
2. 降低 threshold 值：
   ```bash
   curl -X POST http://localhost:8000/api/v1/chat \
     -d '{"message": "問題", "options": {"max_context": 10}}'
   ```

### Q: Notion 同步失敗？

1. 確認 Integration 有權限存取 Database
2. 確認 Database ID 正確
3. 檢查 Database 欄位名稱是否符合預期

---

> 最後更新：2026-01-27（新增 Scheduler API 測試指令）
