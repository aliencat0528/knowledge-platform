# Changelog

本專案遵循 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/) 格式，
版本號遵循 [Semantic Versioning](https://semver.org/lang/zh-TW/)。

## [Unreleased]

### Added
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
