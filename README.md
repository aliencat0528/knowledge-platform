# Knowledge Platform

> 個人知識管理平台 - 整合多種來源的技術文章與筆記

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 功能特色

- 📄 **一鍵收藏** - Chrome 擴充套件快速收藏當前網頁
- 📁 **樹狀抓取** - 一次收藏 Notion 頁面及所有子頁面
- 📑 **批量收藏** - 一次收藏所有開啟的分頁
- 📦 **Zip 匯入** - 匯入 Notion Export .zip 檔案
- 🤖 **AI 對話匯入** - 匯入 Claude Code、Cursor 等 AI 編輯器對話
- 🗂️ **智慧去重** - 自動偵測重複內容，追蹤版本變更
- 🔍 **語意搜尋** - 用自然語言找到相關文章
- 💬 **Chat 對話** - 與你的知識庫對話（RAG）
- 📤 **Notion 同步** - 選擇性同步到 Notion

---

## 快速開始

### 前置需求

- Python 3.11+
- Node.js 18+ (擴充套件開發用)
- Chrome 瀏覽器

### 安裝

```bash
# 1. Clone 專案
git clone <repo-url>
cd knowledge-platform

# 2. 安裝後端依賴
cd packages/server
pip install -r requirements.txt

# 3. 初始化資料庫
python scripts/setup_db.py

# 4. 啟動後端服務
uvicorn main:app --reload
```

### 安裝擴充套件

```bash
# 在 Chrome 載入擴充套件
# 1. 打開 chrome://extensions/
# 2. 啟用「開發人員模式」
# 3. 點擊「載入未封裝項目」
# 4. 選擇 packages/extension 目錄

# 目前擴充套件為純 JavaScript，無需 build 步驟
# 直接載入源碼目錄即可
```

---

## 使用方式

### 收藏網頁

1. 瀏覽任意技術文章
2. 點擊擴充套件圖示
3. 點擊「收藏此頁面」
4. 完成！

### 搜尋知識庫

```bash
# 關鍵字搜尋
curl "http://localhost:8000/api/v1/search?q=React+Hooks"

# 語意搜尋（需要設定 OpenAI API Key）
curl -X POST "http://localhost:8000/api/v1/search/semantic" \
  -H "Content-Type: application/json" \
  -d '{"query": "如何在 React 中管理狀態"}'
```

### 匯入 Notion Export

```bash
python scripts/import_zip.py path/to/Export.zip
```

### 向量化文章（語意搜尋）

```bash
# 設定 OpenAI API Key
export OPENAI_API_KEY=sk-...

# 預覽要向量化的文章
python scripts/embed_all.py --preview

# 執行向量化
python scripts/embed_all.py

# 重新向量化全部（包含已向量化的）
python scripts/embed_all.py --force
```

### 同步到 Notion

```bash
# 1. 設定 Notion API（參考下方設定說明）
export NOTION_API_KEY=secret_...
export NOTION_DATABASE_ID=...

# 2. 檢查同步狀態
curl http://localhost:8000/api/v1/sync/status

# 3. 同步單篇文章
curl -X POST http://localhost:8000/api/v1/sync/notion \
  -H "Content-Type: application/json" \
  -d '{"article_id": 1}'

# 4. 批量同步（未同步的文章）
curl -X POST http://localhost:8000/api/v1/sync/notion/batch \
  -H "Content-Type: application/json" \
  -d '{"limit": 10}'
```

---

## 專案結構

```
knowledge-platform/
├── .speckit/              # Spec Kit 規格文件
├── packages/
│   ├── extension/         # Chrome 擴充套件
│   ├── server/            # Python 後端
│   └── web-ui/            # Web 介面（開發中）
├── scripts/               # 工具腳本
├── data/                  # 資料目錄
├── docs/                  # 文件
└── tests/                 # 測試
```

---

## 設定

複製 `.env.example` 為 `.env` 並填入必要設定：

```bash
# 基本設定（必要）
DATABASE_PATH=./data/knowledge.db
CHROMA_PATH=./data/chroma

# OpenAI（語意搜尋 + Chat 需要）
OPENAI_API_KEY=sk-...

# 自動向量化（新文章匯入時自動產生 embedding）
AUTO_EMBED=true

# Notion 同步（選用）
NOTION_API_KEY=secret_...
NOTION_DATABASE_ID=...
```

---

## 開發

### Spec-Driven Development

本專案使用 [GitHub Spec Kit](https://github.com/github/spec-kit) 進行規格驅動開發：

```bash
# 查看專案原則
cat .speckit/constitution.md

# 查看功能規格
ls .speckit/specs/

# 查看技術計畫
cat .speckit/plans/technical-plan.md

# 查看任務列表
cat .speckit/tasks/phase-1-tasks.md
```

### 執行測試

```bash
pytest tests/
```

---

## API 文件

啟動服務後，訪問 http://localhost:8000/docs 查看 Swagger UI。

主要端點：
- `POST /api/v1/articles` - 新增文章
- `POST /api/v1/articles/batch` - 批量新增
- `GET /api/v1/articles` - 列出文章
- `POST /api/v1/import/zip` - 匯入 Notion Export .zip
- `POST /api/v1/import/chat` - 匯入 AI 對話
- `GET /api/v1/search` - 關鍵字搜尋
- `POST /api/v1/search/semantic` - 語意搜尋
- `POST /api/v1/sync/notion` - 同步文章到 Notion
- `POST /api/v1/sync/notion/batch` - 批量同步到 Notion
- `GET /api/v1/sync/status` - 取得同步狀態
- `POST /api/v1/chat` - Chat 對話（RAG）
- `GET /api/v1/chat/history` - 對話歷史列表
- `GET /api/v1/chat/history/{id}` - 對話詳情
- `DELETE /api/v1/chat/history/{id}` - 刪除對話

---

## 開發階段

- [x] Phase 1: 核心基礎（單頁收藏 + Notion 樹狀抓取）
- [x] Phase 2: 資料收集（批量 + .zip + AI 對話匯入 + 關鍵字搜尋）
- [x] Phase 3: 智慧搜尋（向量化 + Notion 同步）
- [ ] Phase 4: 完整體驗（Chat + Web UI）

---

## 版本歷史

### v0.4.0 (開發中)
- **Chat RAG（Phase 4 進行中）**
  - RAG 流程（語意搜尋 + LLM）
  - Chat 服務 (`ChatService`)
  - Chat API 端點（`POST /chat`）
  - 對話歷史管理
  - 多輪對話支援
  - 引用來源標註

### v0.3.0 (2026-01-27)
- **Notion 同步（Phase 3 完成）**
  - Notion 同步服務（建立/更新頁面）
  - 同步 API 端點（`POST /sync/notion`）
  - 批量同步支援（`POST /sync/notion/batch`）
  - 同步狀態查詢（`GET /sync/status`）
  - Markdown 轉 Notion blocks
  - 速率限制處理和重試機制
- **語意搜尋（Phase 3 完成）**
  - ChromaDB 向量資料庫整合
  - OpenAI Embedding Service
  - 語意搜尋 API (`POST /search/semantic`)
  - 批量向量化腳本 (`scripts/embed_all.py`)
  - 新文章自動向量化選項

### v0.2.0 (2026-01-27)
- **AI 對話匯入（Phase 2 完成）**
  - Claude Code JSONL 格式匯入
  - Cursor SQLite 格式匯入
  - Markdown 格式對話匯入
  - CLI 自動偵測格式
- **批量收藏與搜尋**
  - 擴充套件批量分頁收藏
  - Notion Export .zip 匯入
  - 關鍵字搜尋 API
- **Notion 樹狀抓取（Phase 1b）**
  - Notion 頁面 HTML 解析
  - 子頁面掃描與選擇 UI
  - 樹狀抓取與進度顯示
  - 樹狀匯入 API（父子關係儲存）
- **Chrome 擴充套件核心（Phase 1a）**
  - Manifest V3 設定
  - Popup UI 與伺服器狀態指示
  - 內容提取（Readability.js + Turndown.js）
  - Notion 頁面偵測與 ID 提取
  - Service Worker 背景服務

### v0.1.0 (2026-01-26)
- **專案初始化**
  - Python FastAPI 後端服務
  - SQLite 資料庫層（含 article_hierarchy）
  - Pydantic 資料模型
  - Generic Parser 基礎實作
  - Import Service（含去重邏輯）
  - Articles API 端點
  - Spec Kit 規格文件
  - 專案文件（README、ARCHITECTURE.md）

> 完整變更記錄請參考 [CHANGELOG.md](CHANGELOG.md)

---

## 授權

MIT License
