# Changelog

本專案遵循 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/) 格式，
版本號遵循 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

## [Unreleased]

### Added
- API 認證：所有 `/api/v1/*` 端點（health 除外）要求 `X-API-Key` header
  - `API_KEY` 已設定 → 驗證（timing-safe 比對）；production 未設定 → fail closed（503）；development 未設定 → 放行
  - `.env.example`、`.env.production.example` 新增 `API_KEY` 說明
- 自動化測試套件（本專案首次導入測試）
  - `tests/test_import_dedup.py` - 去重不變式 23 項測試：content hash、
    NEW/SKIPPED/UPDATED 三態、版本遞增與 history、identity scope、批次匯入、輸入驗證
  - `tests/conftest.py` - 每個測試獨立的暫存 SQLite fixture（不觸及 `./data/knowledge.db`）
  - 涵蓋核心不變式：`source_type + source_id` 為唯一識別
- Phase 6 部署基礎設施
  - `zeabur.json` - Zeabur 服務設定檔
  - `packages/server/Dockerfile`、`packages/web-ui/Dockerfile` - 多階段容器建置
  - `.dockerignore`、`.env.production.example` - 生產環境設定
  - `deploy/` - Docker Compose（dev/prod）、Caddyfile、Terraform 規劃
  - `.github/workflows/build.yml`、`deploy.yml` - CI/CD Pipeline
  - `docs/DEPLOYMENT.md` - 部署指南
  - 生產環境安全強化：`config.py` 新增 `is_production`，`ENVIRONMENT=production` 時關閉 `/docs`、`/redoc`、`/openapi.json` 並隱藏 `database_path` 等敏感資訊
- 資料備份與還原功能
  - `scripts/backup.py` - 備份 SQLite 和 ChromaDB 到 .tar.gz
  - `scripts/restore.py` - 從備份還原資料
  - `docs/BACKUP.md` - 完整備份/還原指南
- 進階 Health Check 端點
  - `GET /api/v1/health/ready` - Readiness check（檢查 DB 和 ChromaDB）
  - `GET /api/v1/health/live` - Liveness check（簡單存活檢查）
- Notion 擴充套件子頁面功能 (Task 1b.3~1b.6)
  - 子頁面掃描（notion-scanner.js）
  - 樹狀選擇 UI（checkbox 列表、全選/取消）
  - 樹狀抓取與進度顯示
  - 取消按鈕支援
- Notion Parser (Task 1b.1)
  - 解析 Notion 頁面 HTML 結構
  - 提取子頁面連結
  - 從 URL 提取頁面 ID
  - 支援特殊區塊（Toggle, Callout, Code 等）
- 樹狀匯入 API 驗證 (Task 1b.2)
  - POST /articles/tree 端點測試通過
  - 父子關係正確儲存於 article_hierarchy
- Chrome 擴充套件核心功能 (Task 1a.7, 1a.8)
  - Manifest V3 設定
  - Popup UI 與伺服器狀態指示
  - 內容提取（Readability.js + Turndown.js）
  - Notion 頁面偵測與 ID 提取
  - Service Worker 背景服務
- CLAUDE.md 新增規則
  - 套件評估與安裝指南
  - Bug 修復流程
  - 程序中斷恢復流程
  - 強制文檔檢查清單
  - 版本歷史追蹤規則

### Fixed
- `/api/v1/stats` 補上 API 認證：先前認證只套在 router 層，直接定義於 app 的
  stats 端點被遺漏；新增測試驗證所有 `/api/v1/*`（health 除外）都掛認證
- CORS 設定改用 `allow_origin_regex`：原 `allow_origins` 的 wildcard 條目
  （`chrome-extension://*` 等）因 Starlette 只做完全比對而從未生效
- `scripts/restore.py` 解壓備份改用 `filter="data"`，阻擋惡意壓縮檔路徑穿越
- `.cursor/rules/00-core.mdc` 補上根規則已有的 2 條安全條款（外部匯入內容視為資料、禁改專案外檔案）

### Changed
- 更新 README.md 擴充套件安裝說明
- 更新 docs/ARCHITECTURE.md 擴充套件模組圖

## [0.1.0] - 2026-01-26

### Added
- 專案初始化
- Python 後端服務 (FastAPI)
  - 專案結構與設定
  - SQLite 資料庫層（含 article_hierarchy）
  - Pydantic 資料模型
  - Generic Parser 基礎實作
  - Import Service（含去重邏輯）
  - Articles API（POST /articles, POST /articles/batch）
  - Health API（GET /health）
  - 統一錯誤處理
- Spec Kit 規格文件
  - constitution.md
  - 功能規格 (specs/)
  - 技術計畫 (plans/)
  - 任務列表 (tasks/)
- 文件
  - README.md
  - docs/ARCHITECTURE.md
  - CLAUDE.md（專案開發規則）
