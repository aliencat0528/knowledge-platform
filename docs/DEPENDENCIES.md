# 專案依賴套件

> 本文件列出專案所有依賴套件，新增套件時請同步更新此文件。

---

## 套件總覽

| Package | 技術棧 | 主要用途 |
|---------|--------|----------|
| `packages/server` | Python 3.11+ | FastAPI 後端服務 |
| `packages/web-ui` | Vue 3 + TypeScript | Web 前端介面 |
| `packages/extension` | TypeScript | Chrome 擴充套件 |

---

## 1. Python 後端 (`packages/server/`)

### 設定檔
- `requirements.txt`

### 依賴列表

| 類別 | 套件 | 版本 | 說明 |
|------|------|------|------|
| **Web 框架** | fastapi | ≥0.109.0 | 非同步 Web 框架 |
| | uvicorn | ≥0.27.0 | ASGI 伺服器 |
| | pydantic | ≥2.5.0 | 資料驗證 |
| | pydantic-settings | ≥2.1.0 | 設定管理 |
| **資料庫** | aiosqlite | ≥0.19.0 | 異步 SQLite |
| **向量資料庫** | chromadb | ≥0.4.22 | 向量儲存與語意搜尋 |
| **HTTP 客戶端** | httpx | ≥0.26.0 | 異步 HTTP 請求 |
| **HTML 解析** | beautifulsoup4 | ≥4.12.0 | HTML 解析 |
| | lxml | ≥5.1.0 | XML/HTML 解析器 |
| | markdownify | ≥0.11.0 | HTML 轉 Markdown |
| **外部服務** | notion-client | ≥2.2.0 | Notion API |
| | openai | ≥1.10.0 | OpenAI Embedding + LLM |
| **排程** | apscheduler | ≥3.10.0 | 定時任務排程 |
| **工具** | python-dotenv | ≥1.0.0 | 環境變數載入 |
| | python-multipart | ≥0.0.6 | 檔案上傳支援 |

### 預計新增（Phase 5）

| 套件 | 版本 | 說明 |
|------|------|------|
| anthropic | ≥0.40.0 | Anthropic Claude API |

---

## 2. Web UI (`packages/web-ui/`)

### 設定檔
- `package.json`

### Dependencies（執行時依賴）

| 套件 | 版本 | 說明 |
|------|------|------|
| vue | ^3.5.24 | UI 框架 |
| vue-router | ^4.6.4 | 路由管理 |
| pinia | ^3.0.4 | 狀態管理 |
| axios | ^1.13.3 | HTTP 客戶端 |
| @vueuse/core | ^14.1.0 | Vue 組合式工具集 |

### DevDependencies（開發依賴）

| 套件 | 版本 | 說明 |
|------|------|------|
| vite | ^5.4.21 | 建置工具（支援 Node.js 18+） |
| typescript | ~5.9.3 | TypeScript 編譯器 |
| vue-tsc | ^3.1.4 | Vue TypeScript 檢查 |
| @vitejs/plugin-vue | ^5.2.4 | Vite Vue 插件 |
| @vue/tsconfig | ^0.8.1 | Vue TypeScript 設定 |
| tailwindcss | ^4.1.18 | CSS 框架 |
| @tailwindcss/postcss | ^4.1.18 | Tailwind PostCSS 插件 |
| autoprefixer | ^10.4.23 | CSS 前綴處理 |
| postcss | ^8.5.6 | CSS 處理器 |
| @types/node | ^24.10.1 | Node.js 型別定義 |

---

## 3. Chrome Extension (`packages/extension/`)

### 設定檔
- `manifest.json`（Manifest V3）

### 依賴列表

Chrome Extension 使用原生 JavaScript/TypeScript，無 npm 依賴。

| 類別 | 套件 | 來源 | 說明 |
|------|------|------|------|
| **內容提取** | Readability.js | Mozilla | 文章內容提取 |
| | Turndown.js | DOM to Markdown | HTML 轉 Markdown |

> 這些套件以 minified 檔案形式包含在 `packages/extension/lib/` 目錄中。

---

## 4. 開發工具（全域）

| 工具 | 用途 | 安裝方式 |
|------|------|----------|
| Node.js | Web UI 開發 | 需要 v18.12+ |
| Python | 後端開發 | 需要 v3.11+ |
| Git | 版本控制 | - |
| SQLite | 資料庫 | Python 內建 |

---

## 5. 部署工具（Phase 6）

### 容器化

| 工具 | 版本 | 用途 |
|------|------|------|
| Docker | 24+ | 容器運行環境 |
| Docker Compose | 2.20+ | 多容器編排 |

### CI/CD

| 服務 | 用途 | 設定檔 |
|------|------|--------|
| GitHub Actions | 自動建置與測試 | `.github/workflows/build.yml` |
| Zeabur | 部署平台 | `zeabur.json` |

### 反向代理（自架選用）

| 工具 | 版本 | 用途 |
|------|------|------|
| Caddy | 2.x | 反向代理 + 自動 HTTPS |

### 基礎設施即代碼（進階選用）

| 工具 | 版本 | 用途 |
|------|------|------|
| Terraform | 1.5+ | 雲端資源佈建 |

---

## 6. 外部服務依賴

| 服務 | 用途 | 必要性 | 設定方式 |
|------|------|--------|----------|
| OpenAI API | Embedding + LLM | Phase 3+ 需要 | `OPENAI_API_KEY` |
| Anthropic API | LLM（Phase 5） | 選用 | `ANTHROPIC_API_KEY` |
| Notion API | 同步到 Notion | 選用 | `NOTION_API_KEY` |
| Ollama | 本地模型（Phase 5） | 選用 | `OLLAMA_BASE_URL` |
| Zeabur | 部署平台（Phase 6） | 選用 | `ZEABUR_TOKEN` |

---

## 版本歷史

| 日期 | 變更 |
|------|------|
| 2026-01-27 | 新增 Phase 6 部署工具依賴 |
| 2026-01-27 | 初始版本，包含 Phase 1-4 所有依賴 |

---

## 新增套件指南

當新增套件時，請：

1. **Python 套件**
   - 更新 `packages/server/requirements.txt`
   - 更新本文件的「Python 後端」section

2. **npm 套件**
   - 執行 `npm install <package>` 或 `npm install -D <package>`
   - 更新本文件的「Web UI」section

3. **外部服務**
   - 更新 `.env.example`
   - 更新本文件的「外部服務依賴」section
   - 更新 `packages/server/config.py`（如需要）

4. **Chrome Extension 套件**
   - 將 minified 檔案放入 `packages/extension/lib/`
   - 更新本文件的「Chrome Extension」section
