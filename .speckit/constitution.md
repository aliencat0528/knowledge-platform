# Knowledge Platform - Constitution

> 本文件定義專案的核心原則與治理規範，所有開發決策都應遵循這些原則。
> 此文件為「不可變」的基礎設定，除非經過重大討論，否則不應修改。

---

## 1. 專案願景

### 1.1 使命
建立一個完整的個人知識管理平台，讓使用者能夠：
- 從多種來源收集技術文章與筆記
- 統一儲存與管理知識資料
- 透過智慧搜尋快速找到所需資訊
- 最終實現與知識庫對話的能力

### 1.2 目標使用者
- 軟體工程師
- 技術學習者
- 知識工作者

---

## 2. 核心原則

### 2.1 本地優先 (Local First)
```
優先級：本地儲存 > 雲端同步

- 主要資料存在本地（SQLite + ChromaDB）
- 不強制依賴任何雲端服務
- 離線狀態也能使用核心功能
- Notion 等雲端服務為「可選的同步目標」
```

### 2.2 隱私保護 (Privacy)
```
- 敏感資料不上傳到第三方（除非使用者明確選擇）
- API Key 等憑證只存在本地
- 向量化可選擇本地模型或雲端 API
```

### 2.3 模組化設計 (Modularity)
```
系統應該可以：
- 新增資料來源（Parser）而不影響其他模組
- 新增儲存目標（Storage）而不影響其他模組
- 替換 LLM 提供者而不重寫整個系統
```

### 2.4 去重與版本追蹤 (Deduplication & Versioning)
```
- 相同來源的文章不應重複儲存
- 使用 source_type + source_id 作為唯一識別
- 使用 content_hash 偵測內容變更
- 保留變更歷史以供追溯
```

### 2.5 漸進式功能 (Progressive Enhancement)
```
- 核心功能應該簡單可用
- 進階功能（向量化、Chat）為可選
- 使用者可以只用基礎功能
```

### 2.6 API 開放性 (API Openness)
```
- 所有功能必須透過 API 暴露，支援第三方整合
- API 設計遵循 RESTful 規範，提供完整 OpenAPI 文件
- 認證機制可選，預設本地使用無需認證
- 統一的錯誤回應格式，方便外部工具處理
- 提供整合範例與文件，降低整合門檻
```

---

## 3. 技術規範

### 3.1 技術選型（已確定）

| 層級 | 技術 | 理由 |
|------|------|------|
| 後端語言 | Python 3.11+ | 爬蟲生態系完整、LLM 整合方便 |
| Web 框架 | FastAPI | 現代化、異步支援、自動 API 文件 |
| 主資料庫 | SQLite | 輕量、免架設、單機足夠 |
| 向量資料庫 | ChromaDB | 本地運行、Python 原生 |
| 擴充套件 | Chrome Extension (Manifest V3) | 最多人使用 |
| 前端框架 | Vue 3 + TypeScript (Web UI) | 現代化、生態系完整 |

### 3.2 程式碼規範

```python
# Python
- 使用 Type Hints
- 使用 Pydantic 做資料驗證
- 遵循 PEP 8
- 使用 Black 格式化
- 使用 Ruff 做 Linting

# TypeScript/JavaScript
- 使用 ESLint + Prettier
- 優先使用 TypeScript
```

### 3.3 API 設計原則

```
- RESTful 設計
- 統一錯誤回應格式
- 版本化 API（/api/v1/...）
- 所有端點都有 OpenAPI 文件
```

---

## 4. 架構邊界

### 4.1 系統邊界

```
┌─────────────────────────────────────────────────────────────┐
│                    Knowledge Platform                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  輸入層（Collectors）                                        │
│  ├── Chrome Extension（單頁、樹狀、批量）                    │
│  ├── CLI（.zip 匯入、URL 抓取）                             │
│  └── Scheduler（排程爬取）                                  │
│                                                             │
│  處理層（Processors）                                        │
│  ├── Parsers（各網站解析器）                                │
│  ├── Deduplicator（去重比對）                               │
│  └── Transformer（格式轉換）                                │
│                                                             │
│  儲存層（Storage）                                           │
│  ├── SQLite（主要資料）                                     │
│  ├── ChromaDB（向量索引）                                   │
│  └── Notion Sync（選擇性同步）                              │
│                                                             │
│  查詢層（Query）                                             │
│  ├── REST API                                               │
│  ├── Semantic Search                                        │
│  └── Chat（RAG + LLM）                                      │
│                                                             │
│  部署層（Deployment）                                        │
│  ├── Docker Container                                       │
│  ├── Zeabur / VPS                                          │
│  └── CI/CD（GitHub Actions）                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 外部整合定位

```
本專案（knowledge-platform）為完整的知識管理平台，包含所有功能：
- 單頁收藏、樹狀抓取、批量分頁、.zip 匯入、排程爬取
- 語意搜尋、Chat 對話
- Notion 同步

「子專案」重新定義為「外部整合」：
- 其他爬蟲工具、匯出工具、自製腳本等
- 透過開放 API 與本平台整合
- 不共用程式碼，透過 HTTP API 通訊

整合原則：
1. API 優先
   - 所有功能都有對應的 API 端點
   - 外部工具透過 API 送入資料

2. 格式統一
   - 統一的 Request/Response 格式
   - 完整的 OpenAPI 文件

3. 認證可選
   - 本地使用無需認證
   - 可選啟用 API Key 認證

4. 向下相容
   - API 版本化（/api/v1/）
   - 新版本不破壞舊介面
```

---

## 5. 開發階段

### 5.1 Phase 定義

| Phase | 目標 | 核心功能 |
|-------|------|---------|
| Phase 1 | 核心可用 | 後端 API + 單頁抓取 + SQLite |
| Phase 2 | 資料收集完整 | 批量 + 樹狀 + .zip 匯入 + 去重 |
| Phase 3 | 智慧搜尋 | 向量化 + 語意搜尋 + Notion 同步 |
| Phase 4 | 完整體驗 | Chat + Web UI + 排程爬取 |
| Phase 5 | 多 Provider | OpenAI + Anthropic + Ollama 支援 |
| Phase 6 | 部署上線 | Zeabur + Docker + CI/CD |
| Phase 7 | 進階部署（選用）| Terraform + 雲端自動化 |

### 5.2 MVP 定義（Phase 1 完成時）

```
使用者可以：
✅ 安裝擴充套件
✅ 一鍵收藏當前網頁
✅ 資料存入本地 SQLite
✅ 透過 CLI 查詢已收藏的文章

使用者還不能：
❌ 批量收藏
❌ 樹狀收藏
❌ 語意搜尋
❌ Chat 對話
```

---

## 6. 非功能需求

### 6.1 效能目標

| 操作 | 目標 |
|------|------|
| 單頁抓取 | < 2 秒 |
| 批量抓取（10 頁）| < 15 秒 |
| 關鍵字搜尋 | < 100ms |
| 語意搜尋 | < 500ms |

### 6.2 安全性

- 不儲存使用者密碼
- API Key 加密儲存在本地
- 不追蹤使用者行為

### 6.3 可維護性

- 程式碼覆蓋率目標：70%+
- 所有公開 API 都有文件
- 重要函數都有 docstring

---

## 7. 決策記錄

### ADR-001: 選擇 SQLite 而非 PostgreSQL
- **狀態**: 已採納
- **原因**: 單機使用、免架設、降低使用門檻
- **後果**: 如需多用戶支援，需要遷移

### ADR-002: 本地優先而非雲端優先
- **狀態**: 已採納
- **原因**: 隱私考量、離線可用、降低依賴
- **後果**: 跨裝置同步需要額外處理

### ADR-003: 與子專案保持獨立
- **狀態**: 已採納
- **原因**: 降低耦合、各自迭代、靈活調整
- **後果**: 可能有重複程式碼

---

## 附錄：術語定義

| 術語 | 定義 |
|------|------|
| source_type | 資料來源類型（notion / medium / docs / web）|
| source_id | 來源的唯一識別碼 |
| content_hash | 內容的 MD5 hash，用於比對變更 |
| Parser | 針對特定網站的內容解析器 |
| Collector | 資料收集模組 |
| RAG | Retrieval-Augmented Generation，檢索增強生成 |
