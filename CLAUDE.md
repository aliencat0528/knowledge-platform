# Knowledge Platform 規則

> 繼承根目錄共用規則（Claude Code 已自動載入，勿重複讀取 ../CLAUDE.md）

---

## 專案概述
個人知識管理平台，整合多種來源的技術文章與筆記。  
**技術棧**：Python FastAPI + SQLite + ChromaDB + Chrome Extension  
**架構**：Monorepo（packages/）

---

## Commit Scopes

| Scope | 說明 |
|-------|------|
| `server` | Python 後端 |
| `extension` | Chrome 擴充套件 |
| `storage` | 資料庫 |
| `parser` | 內容解析器 |
| `search` | 搜尋功能 |
| `chat` | Chat/RAG |
| `notion` | Notion 同步 |
| `web-ui` | Web 介面 |

---

## 開發指令

```bash
# 後端
cd packages/server && uvicorn main:app --reload

# 擴充套件
cd packages/extension && npm install && npm run dev

# 測試
pytest tests/
pytest --cov=packages/server

# 工具腳本
python scripts/import_zip.py <path-to-zip>
python scripts/embed_all.py
```

---

## SDD 工作流程（.speckit/）

```
1. 先讀 @.speckit/constitution.md（治理原則）
2. 查看功能規格 @.speckit/specs/
3. 查看技術計畫 @.speckit/plans/
4. 依任務列表 @.speckit/tasks/ 執行
5. 實作與規格有差異 → 先更新規格再繼續
```

---

## Phase 直線化開發

- 同 Phase 內分支可並行；下一 Phase 必須等該 Phase 所有 PR merge
- Phase 完成條件：所有 PR merged + main 可正常運行 + 文件更新

**分支版本號**：feature/ 使用 Phase 序列（sec→third→...），fix/docs/chore 獨立從 first 開始

---

## 套件安裝原則

| 類型 | 行為 |
|------|------|
| 開發工具（uv, ruff, biome, pytest 插件） | 可直接安裝 |
| 架構性依賴（新 ORM、新框架） | 必須詢問 |
| 付費/大型依賴（AWS SDK, PyTorch） | 必須詢問 |

---

## 安全提醒
- 禁止修改 `data/` 目錄的 DB / 向量庫檔案
- 禁止 commit `.env`、API keys
- 去重邏輯：`source_type + source_id` 為唯一識別
- Parser 設計保持可擴展（新 Parser 不影響其他模組）

---

## 領域知識索引
需要時：`@.claude/knowledge/index.md`
