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

# 目前擴充套件為純 JavaScript，無需 build 步驟，直接載入源碼目錄即可
```

> 完整本地開發流程（前後端、多終端機、選用服務）見 [部署指南](docs/DEPLOYMENT.md#2-本地開發)。

---

## 使用方式

以下說明各功能怎麼用；**完整的 API 指令與請求／回應範例集中在 [測試指南](docs/TESTING.md)**，本節只給概念與代表性範例。

### 收藏網頁

1. 瀏覽任意技術文章
2. 點擊擴充套件圖示 →「收藏此頁面」
3. 完成。內容自動經 Readability 擷取、去重後入庫

### 搜尋知識庫

支援關鍵字與語意兩種搜尋（語意搜尋需設定 OpenAI API Key 並先向量化）。

```bash
# 關鍵字搜尋
curl "http://localhost:8000/api/v1/search?q=React+Hooks"
```

### 匯入與向量化

- **Notion Export**：`python scripts/import_zip.py path/to/Export.zip`
- **AI 對話**：擴充套件或 `POST /api/v1/import/chat`（支援 Claude Code JSONL、Cursor SQLite、Markdown，自動偵測格式）
- **向量化**（語意搜尋前置）：`python scripts/embed_all.py`（`--preview` 預覽、`--force` 全部重做）

### 同步到 Notion

設定 `NOTION_API_KEY` / `NOTION_DATABASE_ID` 後，可單篇或批量把文章推送到 Notion，並查詢同步狀態。指令見 [測試指南 › Notion 同步](docs/TESTING.md)。

### 排程爬取

啟動排程器後，用 Cron 表達式建立定期抓取任務（如每 6 小時抓一次指定來源），支援手動執行與狀態查詢。指令與 Cron 格式見 [測試指南 › Scheduler](docs/TESTING.md)。

### 備份與還原

`python scripts/backup.py` 建立 SQLite + ChromaDB 備份；`python scripts/restore.py <檔>` 還原（`--preview` 預覽）。完整說明見 [備份與還原指南](docs/BACKUP.md)。

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

> 模組職責與資料流見 [架構文件](docs/ARCHITECTURE.md)。

---

## 設定

複製 `.env.example` 為 `.env` 並填入設定。最關鍵的幾項：

| 變數 | 必要 | 用途 |
|------|------|------|
| `DATABASE_PATH` | ✅ | SQLite 路徑（預設 `./data/knowledge.db`） |
| `OPENAI_API_KEY` | 語意搜尋/Chat 需要 | OpenAI 金鑰 |
| `API_KEY` | 生產環境需要 | `/api/v1/*` 認證用 |

> **完整環境變數清單（必要／選用／系統／Provider 四類，含「少了會怎樣」）為單一正本，見 [部署指南 › 環境變數說明](docs/DEPLOYMENT.md#5-環境變數說明)。**

---

## 開發

### Spec-Driven Development

本專案使用 [GitHub Spec Kit](https://github.com/github/spec-kit) 進行規格驅動開發，規格與計畫在 `.speckit/`（`constitution.md` 治理原則、`specs/` 功能規格、`plans/` 技術計畫、`tasks/` 任務列表）。

### 測試

```bash
pytest tests/
```

> 完整測試流程、預期結果與整合測試見 [測試指南](docs/TESTING.md)。

---

## API 文件

啟動服務後訪問 http://localhost:8000/docs 查看 Swagger UI。主要端點分為文章、匯入、搜尋、Notion 同步、Chat、排程、健康檢查等群組。

> **完整端點清單見 [API 參考](docs/API.md)**；各端點的請求／回應範例見 [測試指南](docs/TESTING.md)。
>
> 生產環境（`ENVIRONMENT=production`）會自動關閉 `/docs`、`/redoc`、`/openapi.json` 並隱藏敏感資訊。

---

## 部署

推薦 **Zeabur 一鍵部署**（連結 GitHub Repository 後依 `zeabur.json` 自動部署），另支援 Docker Compose 自架。

```bash
# Docker Compose（自架）
docker compose -f deploy/docker-compose.prod.yml up -d
```

> 三種部署方式的完整步驟、生產環境變數與 CI/CD 說明見 [部署指南](docs/DEPLOYMENT.md)。

---

## 開發階段

- [x] Phase 1: 核心基礎（單頁收藏 + Notion 樹狀抓取）
- [x] Phase 2: 資料收集（批量 + .zip + AI 對話匯入 + 關鍵字搜尋）
- [x] Phase 3: 智慧搜尋（向量化 + Notion 同步）
- [x] Phase 4: 完整體驗（Chat + Web UI）
- [x] Phase 5: 多來源整合（多 Provider 支援）
- [x] Phase 6: 部署與 DevOps（Zeabur / Docker / CI-CD / 備份）

---

## 版本歷史

各版重點（迭代摘要，逐條變更見 [CHANGELOG.md](CHANGELOG.md)）：

| 版本 | 重點 |
|------|------|
| **v0.4.0**（開發中） | 部署與維運（備份/還原、進階 Health Check）、排程爬取、Chat RAG |
| **v0.3.0** | 語意搜尋（ChromaDB + Embedding）、Notion 同步 |
| **v0.2.0** | AI 對話匯入、批量收藏與搜尋、Notion 樹狀抓取、Chrome 擴充套件核心 |
| **v0.1.0** | 專案初始化（FastAPI 後端、SQLite、去重邏輯、Articles API） |

> ⚠️ 版本編號待對齊：CHANGELOG 目前將 v0.1.0 之後的變更歸於 `[Unreleased]`，
> 尚未拆出 v0.2/v0.3/v0.4 標籤。發布前需確認實際 release 標記後同步兩處。

---

## 授權

MIT License
