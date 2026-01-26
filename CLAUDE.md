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
