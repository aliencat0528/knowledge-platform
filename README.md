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
- `GET /api/v1/articles` - 列出文章
- `GET /api/v1/search` - 關鍵字搜尋
- `POST /api/v1/search/semantic` - 語意搜尋
- `POST /api/v1/chat` - Chat 對話

---

## 開發階段

- [x] Phase 1: 核心基礎（單頁收藏 + SQLite）
- [ ] Phase 2: 資料收集（批量 + .zip + 去重）
- [ ] Phase 3: 智慧搜尋（向量化 + Notion 同步）
- [ ] Phase 4: 完整體驗（Chat + Web UI）

---

## 版本歷史

### v0.2.0 (開發中)
- **Chrome 擴充套件核心**
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
