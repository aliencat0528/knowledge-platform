# Knowledge Platform - Claude Code Guidelines

> **⚠️ IMPORTANT: 請先閱讀 `../CLAUDE.md`（共用規則），再閱讀本檔案。**
> 本檔案包含專案特定的規則，會擴展共用規則。

---

## 專案概述

個人知識管理平台，整合多種來源的技術文章與筆記。

- **技術棧**: Python FastAPI + SQLite + ChromaDB + Chrome Extension
- **架構**: Monorepo（packages/）

---

## 專案特定 Commit Scopes

除了標準的 types，本專案使用以下 **scopes**：

| Scope | 說明 |
|-------|------|
| `server` | Python 後端服務 |
| `extension` | Chrome 擴充套件 |
| `storage` | 資料庫相關 |
| `parser` | 內容解析器 |
| `search` | 搜尋功能 |
| `chat` | Chat/RAG 功能 |
| `notion` | Notion 同步 |
| `web-ui` | Web 介面 |

**範例：**
- `feat(server): add articles API endpoint`
- `fix(extension): resolve content extraction issue`
- `refactor(parser): optimize Notion parser`

---

## 專案結構

```
knowledge-platform/
├── .speckit/                  # Spec Kit 規格文件
│   ├── constitution.md        # 專案治理原則
│   ├── specs/                 # 功能規格
│   ├── plans/                 # 技術計畫
│   └── tasks/                 # 任務列表
├── packages/
│   ├── extension/             # Chrome 擴充套件
│   ├── server/                # Python 後端
│   └── web-ui/                # Vue 3 前端（Phase 4）
├── scripts/                   # 工具腳本
├── data/                      # 資料目錄（gitignore）
├── docs/                      # 文件
└── tests/                     # 測試
```

---

## 開發指令

```bash
# 後端開發
cd packages/server
pip install -r requirements.txt
uvicorn main:app --reload

# 擴充套件開發
cd packages/extension
npm install
npm run dev

# 執行測試
pytest tests/

# .zip 匯入
python scripts/import_zip.py <path-to-zip>

# 批量向量化
python scripts/embed_all.py
```

---

## Spec Kit 工作流程

本專案使用 Spec-Driven Development，遵循以下流程：

```
1. 查看 Constitution    → .speckit/constitution.md
2. 查看功能規格         → .speckit/specs/
3. 查看技術計畫         → .speckit/plans/
4. 查看任務列表         → .speckit/tasks/
5. 依序完成任務
```

### 重要原則

- **先讀 Spec 再寫程式碼**：所有功能都有對應的 User Story 和驗收條件
- **遵循 Constitution**：特別是「本地優先」和「去重邏輯」
- **更新 Spec**：如果實作與規格有差異，先更新規格再繼續

---

## Phase 直線化開發規則

本專案採用 **Phase 直線化開發**，確保每個階段穩定後才進入下一階段。

### 核心規則

```
1. 同一 Phase 內的分支可並行開發
2. 該 Phase 所有 PR 必須 merge 完成後，才能開始下一 Phase
3. 每個 Phase 結束時，main 分支必須是穩定可用的狀態
```

### 開發流程圖

```
main ─────────────────────────────────────────────────────────►
        │                           │                     │
        │ Phase 1a                  │ Phase 1b            │ Phase 2
        ├── backend-core ──► PR ────┤                     │
        │                    merge  │                     │
        └── extension-core ► PR ────┤                     │
                             merge  │                     │
                                    ├── notion-parser ► PR ┤
                                    │                merge │
                                    └── notion-ext ──► PR ─┤
                                                    merge  │
                                                           ├── ...
```

### 分支命名規則

| Phase | 分支群組 | 命名格式 |
|-------|----------|----------|
| 1a | 後端核心 | `feature/backend-core-sec` |
| 1a | 擴充套件核心 | `feature/extension-core-third` |
| 1b | Notion 解析 | `feature/notion-parser-fourth` |
| 1b | Notion 擴充 | `feature/notion-extension-fifth` |
| 2 | 批量匯入 | `feature/batch-import-sixth` |
| ... | ... | ... |

> 完整對應表請參考 `.speckit/plans/technical-plan.md`

### 版本號分離規則

**重要**：不同 branch type 使用**獨立的版本計數器**，避免互相干擾。

| Type | 版本計數器 | 說明 |
|------|-----------|------|
| `feature/` | Phase 序列 | `sec → third → fourth → ...`，追蹤 Phase 開發順序 |
| `fix/` | 獨立序列 | `first → sec → third → ...`，從 first 開始 |
| `docs/` | 獨立序列 | `first → sec → third → ...`，從 first 開始 |
| `chore/` | 獨立序列 | `first → sec → third → ...`，從 first 開始 |

**範例**：
```
feature/ai-chat-import-seventh   ← Phase 2 第 7 個 feature
feature/vector-search-eighth     ← Phase 3 第 8 個 feature（保留）
fix/popup-crash-first            ← 第 1 個 fix
fix/api-timeout-sec              ← 第 2 個 fix
docs/phase2-status-first         ← 第 1 個 docs
```

**原因**：
- `feature/` 版本號與 Phase 直線化開發綁定，用於追蹤功能開發進度
- `fix/`、`docs/`、`chore/` 是臨時性或輔助性分支，不應佔用 Phase 序列
- 分離計數器確保 Phase 規劃不受非功能分支干擾

### Phase 完成檢查清單

開始下一 Phase 前，確認：

- [ ] 該 Phase 所有 PR 已 merge 到 main
- [ ] main 分支可正常運行
- [ ] 該 Phase 的完成條件全部達成（見 `.speckit/tasks/`）
- [ ] 相關文件已更新（README、docs/）

### 指令

| 指令 | 說明 |
|------|------|
| `開始 Phase X` | Claude 檢查前一 Phase 是否完成，若完成則建立新分支 |
| `Phase 狀態` | 顯示當前 Phase 進度和待完成項目 |

---

## 階段性功能測試文件

> **Claude 必須在每個階段性功能完成後，主動提供完整測試流程**

### 測試文件格式

每完成一個 Task 或功能模組後，必須提供以下資訊：

```markdown
## ✅ Task #X 完成：[功能名稱]

### 完整測試流程

**1. 環境準備**
- 啟動伺服器指令
- 所需環境變數
- 前置條件

**2. 測試指令**
- CLI 測試（如適用）
- API 測試（curl 指令）
- 瀏覽器測試（如適用）

**3. 預期結果**
- 成功時的輸出範例
- 錯誤處理範例

**4. 驗證方式**
- 資料庫查詢
- API 回應確認
- UI 狀態確認

### 新增/修改檔案
| 檔案 | 說明 |
|------|------|

### 新增 API 端點（如適用）
| 端點 | 方法 | 說明 |
|------|------|------|
```

### 觸發條件

| 情況 | 行為 |
|------|------|
| 完成一個 Task | 提供該功能的完整測試流程 |
| 新增 API 端點 | 提供 curl 測試指令 |
| 新增 CLI 工具 | 提供使用範例和參數說明 |
| 新增擴充套件功能 | 提供手動測試步驟 |

### 範例

```markdown
## ✅ Task #1 完成：.zip 匯入功能

### 完整測試流程

**1. 啟動伺服器**
\`\`\`bash
python -m uvicorn packages.server.main:app --reload
\`\`\`

**2. CLI 測試**
\`\`\`bash
# Preview 模式
python scripts/import_zip.py ~/Downloads/Export.zip --preview

# 實際匯入
python scripts/import_zip.py ~/Downloads/Export.zip
\`\`\`

**3. API 測試**
\`\`\`bash
curl -X POST -F "file=@Export.zip" http://localhost:8000/api/v1/import/zip
\`\`\`

**4. 驗證資料**
\`\`\`bash
sqlite3 data/knowledge.db "SELECT id, title FROM articles LIMIT 10"
\`\`\`
```

---

## 觸發詞與文件更新

當這些關鍵詞出現時，檢查是否需要更新相關文件：

| 觸發詞 | 可能需要更新 |
|--------|-------------|
| `parser`, `解析器` | specs/epic-2, plans/ |
| `storage`, `儲存` | specs/epic-3 |
| `search`, `搜尋` | specs/epic-4 |
| `notion`, `同步` | specs/epic-3 |
| `schema`, `資料庫` | plans/technical-plan |
| `api`, `端點` | plans/technical-plan, docs/API.md |
| `npm install`, `pip install`, `依賴`, `套件` | docs/DEPENDENCIES.md |
| `phase`, `階段`, `新功能模組` | constitution.md, plans/technical-plan |
| `deploy`, `部署`, `docker`, `ci/cd` | plans/technical-plan, docs/DEPLOYMENT.md |
| `provider`, `llm`, `embedding` | specs/epic-5, plans/technical-plan |

---

## 強制文檔檢查（Commit 前自動執行）

> **Claude 必須在每次 commit 前主動執行以下檢查，不需用戶提醒**

### Commit 前檢查清單

```
每次 commit 前，Claude 必須自問：

□ 是否新增/修改了功能？
  → 更新 README.md 相關 section
  → 更新 CHANGELOG.md（如適用）

□ 是否新增/刪除了檔案或模組？
  → 更新 docs/ARCHITECTURE.md 模組圖
  → 更新 README.md 專案結構

□ 是否修改了 API？
  → 更新 docs/API.md（如存在）
  → 更新 README.md API section

□ 是否新增了依賴？
  → 更新 requirements.txt 或 package.json
  → 更新 docs/DEPENDENCIES.md（必要）
  → 更新 README.md 安裝說明

□ 是否為重要里程碑？
  → 更新 CHANGELOG.md

□ 是否完成了某個 Task？
  → 更新 `.speckit/tasks/` 對應狀態（📋 → ✅）
  → 確認 Task 輸出檔案都已建立

□ 是否新增了 Phase 或重大功能模組？（必要）
  → 更新 `.speckit/constitution.md`（Phase 定義表）
  → 更新 `.speckit/plans/technical-plan.md`（分支規劃表）
  → 新增對應的 `.speckit/tasks/phase-X-tasks.md`

□ 是否修改了系統架構？
  → 更新 `.speckit/constitution.md`（架構邊界圖）
  → 更新 `.speckit/plans/technical-plan.md`（架構圖）
  → 更新 docs/ARCHITECTURE.md
```

### 違反處理

如果 Claude 漏掉文檔更新：
1. 用戶提醒後，立即補上
2. 在下次 commit 中加入文檔更新
3. 不需要 amend 之前的 commit（除非用戶要求）

---

## 版本歷史追蹤

### CHANGELOG.md 規則

本專案使用 [Keep a Changelog](https://keepachangelog.com/) 格式：

```markdown
# Changelog

## [Unreleased]
### Added
- 新功能描述

### Changed
- 修改描述

### Fixed
- 修復描述

## [0.1.0] - 2026-01-26
### Added
- 初始版本功能
```

### 更新時機

| 事件 | 行為 |
|------|------|
| 完成一個 Task | 在 `[Unreleased]` 加入條目 |
| PR merge 到 main | 保持在 `[Unreleased]` |
| 發布版本 | 將 `[Unreleased]` 改為版本號 + 日期 |

### README 版本顯示

README.md 頂部應顯示當前版本：

```markdown
[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](CHANGELOG.md)
```

---

## 測試要求

```bash
# 執行所有測試
pytest

# 執行特定測試
pytest tests/test_import.py

# 顯示覆蓋率
pytest --cov=packages/server
```

### 測試規範

- Parser 必須有單元測試
- Import Service 必須測試：new, skip, update 三種情況
- API 端點必須有整合測試

---

## 環境設定

```bash
# 複製範例設定
cp .env.example .env

# 必要設定
DATABASE_PATH=./data/knowledge.db
CHROMA_PATH=./data/chroma

# 可選設定（Phase 3+）
OPENAI_API_KEY=sk-...
NOTION_API_KEY=secret_...
NOTION_DATABASE_ID=...
```

---

## 重要提醒

1. **不要直接修改 data/ 目錄的檔案**（資料庫、向量庫）
2. **敏感資料不要 commit**（.env, API keys）
3. **遵循去重邏輯**：source_type + source_id 是唯一識別
4. **保持 Parser 可擴展**：新增 Parser 不應影響其他模組

---

## 套件評估與安裝

### 自動評估原則

Claude 可自行評估並安裝以下類型的工具：

| 類型 | 範例 | 行為 |
|------|------|------|
| **開發效率工具** | uv, ruff, black | 可直接安裝，commit 時說明 |
| **專案已定義依賴** | requirements.txt 內的套件 | 直接安裝 |
| **輔助工具** | pytest 插件, 型別檢查 | 可直接安裝 |

### 需確認的情況

| 類型 | 範例 | 行為 |
|------|------|------|
| **架構性依賴** | 新 ORM, 新框架 | 必須詢問 |
| **付費服務 SDK** | AWS SDK, Stripe | 必須詢問 |
| **大型依賴** | TensorFlow, PyTorch | 必須詢問 |

### 推薦工具列表

| 工具 | 用途 | 適用於 |
|------|------|--------|
| `uv` | 快速 Python 套件管理 | packages/server/ |
| `ruff` | 快速 Python linter | packages/server/ |
| `biome` | 快速 JS/TS linter | packages/extension/ |

---

## Bug 修復流程

### 臨時中斷修 Bug

當開發中發現需要緊急修復的 bug 時：

#### 流程

```
1. 確認當前分支有無未 commit 的重要變更
   ├── 有 → 先 commit 或 stash
   └── 無 → 直接切換

2. 從 main 建立修復分支
   └── git checkout main && git checkout -b fix/<bug-name>-<version>

3. 修復 bug → commit → push → PR

4. PR merge 後，回到原分支
   └── git checkout <original-branch>
   └── git rebase main（取得修復）

5. 繼續原本開發
```

#### 分支命名

```
fix/<bug-description>-<version>

範例：
- fix/popup-crash-first     ← 第 1 個 fix（獨立計數）
- fix/api-timeout-sec       ← 第 2 個 fix（獨立計數）
```

> ⚠️ fix 版本號從 `first` 開始，與 feature 的 Phase 序列**完全獨立**。
> 參見「版本號分離規則」section。

#### 注意事項

- Bug 修復分支應盡量小且專注
- 不要在修復分支做功能開發
- 修復完成後及時清理本地分支

---

## 程序中斷恢復

### 中斷類型與處理

| 中斷類型 | 恢復方式 |
|----------|----------|
| **對話中斷** | 新對話時說明「繼續上次開發」，Claude 會檢查 git status |
| **網路中斷** | 重新連線後檢查最後操作是否完成 |
| **編輯中斷** | 檢查檔案是否完整，必要時回滾 |

### 恢復檢查清單

新對話恢復開發時，Claude 應執行：

```bash
# 1. 檢查當前分支和狀態
git branch --show-current
git status

# 2. 檢查最近 commits
git log --oneline -5

# 3. 檢查是否有 stash
git stash list

# 4. 檢查任務進度
# 查看 .speckit/tasks/ 相關文件
```

### 狀態標記（可選）

若需要長時間中斷，可在 commit message 加上標記：

```
feat(extension): WIP - popup UI 完成 50%

[WIP] 標記表示此 commit 為進行中狀態
下次繼續：完成 notion-detector 整合
```

### 安全原則

- **不確定時詢問**：如果不清楚中斷前的狀態，先詢問用戶
- **優先保留**：寧可多 commit 一個 WIP，也不要丟失進度
- **檢查再行動**：恢復後先 `git status` 確認狀態再繼續
