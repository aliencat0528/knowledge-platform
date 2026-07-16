# Knowledge Platform — 領域知識索引

> **載入方式**：先讀此索引，再依需求載入對應檔案。不需要的不載入。

---

## 規格文件（.speckit/）

| 內容 | 路徑 |
|------|------|
| 專案治理原則、Phase 定義、架構邊界 | `@../.speckit/constitution.md` |
| 功能規格（Epic/User Story） | `@../.speckit/specs/` |
| 技術計畫、分支規劃表 | `@../.speckit/plans/technical-plan.md` |
| 當前任務列表 | `@../.speckit/tasks/` |

---

## 領域知識檔案

| 主題 | 檔案 | 何時載入 |
|------|------|---------|
| RAG / 向量搜尋設計 | `@domain-rag.md` | 處理 search/chat/embedding 功能時 |
| Notion 整合細節 | `@domain-notion.md` | 處理 notion sync/parser 時 |
| ChromaDB 使用模式 | `@domain-chromadb.md` | 處理向量庫操作時 |
| 已知問題與解法 | `@solutions.md` | 遇到已知問題時 |
| 資料來源格式說明 | `@sources.md` | 新增/修改 parser 時 |

---

## 快速判斷

- 處理 **parser / 解析** → 載入 `@sources.md`
- 處理 **search / chat / RAG** → 載入 `@domain-rag.md`
- 處理 **notion** → 載入 `@domain-notion.md`
- 遇到 **錯誤 / bug** → 先查 `@solutions.md`
- 需要架構全貌 → 載入 `@../.speckit/constitution.md`
