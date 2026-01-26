# Epic 4: 查詢與 Chat (Query & Chat)

> 本文件定義查詢與 Chat 相關的所有功能規格。

---

## User Story 4.1: 關鍵字搜尋

### 描述
```
作為使用者
我想要用關鍵字搜尋我的知識庫
這樣我可以快速找到相關文章
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: 基本關鍵字搜尋
  Given 知識庫中有 100 篇文章
  When 我搜尋「React Hooks」
  Then 回傳標題或內容包含「React」且包含「Hooks」的文章
  And 按相關度排序
  And 顯示匹配的片段（highlight）

Scenario: 標籤過濾
  Given 搜尋「Hooks」
  When 我加上標籤過濾「React」
  Then 只回傳有「React」標籤的結果

Scenario: 無結果
  Given 搜尋「xyz123不存在的詞」
  When 執行搜尋
  Then 回傳空結果
  And 顯示「找不到相關文章」
```

### API 定義

```
GET /api/v1/search?q=React+Hooks&tags=React&limit=20&offset=0

Response:
{
  "total": 45,
  "results": [
    {
      "id": 123,
      "title": "React Hooks 完全指南",
      "snippet": "...useState 是最常用的 <mark>Hook</mark>...",
      "source_type": "docs",
      "tags": ["React", "Hooks"],
      "score": 0.95,
      "url": "https://react.dev/..."
    }
  ]
}
```

---

## User Story 4.2: 語意搜尋

### 描述
```
作為使用者
我想要用自然語言搜尋
這樣即使用詞不同也能找到相關內容
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: 語意搜尋
  Given 知識庫中有文章「useState Hook 教學」
  When 我搜尋「如何在 React 中管理狀態」
  Then 即使沒有完全匹配的詞
  But 語意相近
  Then 回傳「useState Hook 教學」

Scenario: 混合搜尋
  Given 同時啟用關鍵字和語意搜尋
  When 我搜尋
  Then 結合兩種結果
  And 去重並重新排序
```

### 搜尋流程

```
┌─────────────────────────────────────────────────────────────┐
│                    語意搜尋流程                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  使用者輸入：「如何在 React 中管理狀態」                     │
│         │                                                   │
│         ▼                                                   │
│  ┌─────────────────┐                                        │
│  │ Embedding API   │ 將查詢轉成向量                         │
│  └────────┬────────┘                                        │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────┐                                        │
│  │ ChromaDB 查詢   │ 找出最相似的 N 篇                      │
│  └────────┬────────┘                                        │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────┐                                        │
│  │ SQLite 補充資料 │ 取得完整文章資訊                       │
│  └────────┬────────┘                                        │
│           │                                                 │
│           ▼                                                 │
│  回傳結果                                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### API 定義

```
POST /api/v1/search/semantic
{
  "query": "如何在 React 中管理狀態",
  "limit": 10,
  "threshold": 0.7  // 最低相似度
}

Response:
{
  "results": [
    {
      "id": 123,
      "title": "useState Hook 教學",
      "similarity": 0.89,
      "snippet": "...",
      ...
    }
  ]
}
```

---

## User Story 4.3: Chat 對話

### 描述
```
作為使用者
我想要用對話方式查詢知識庫
這樣我可以問複雜問題並得到整合的答案
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: 基本問答
  Given 知識庫有 React 相關文章
  When 我問「React 的 useEffect 和 useLayoutEffect 有什麼差別？」
  Then 系統搜尋相關文章
  And 將相關內容傳給 LLM
  And 回傳整合後的答案
  And 標註參考來源

Scenario: 追問
  Given 我已問過「useEffect 是什麼？」
  When 我追問「那它常見的錯誤用法有哪些？」
  Then 系統理解這是追問
  And 在相同主題下搜尋
  And 回傳相關答案

Scenario: 知識庫沒有相關資料
  Given 我問的問題不在知識庫範圍內
  When 執行 Chat
  Then 回傳「知識庫中沒有相關資料，以下是根據一般知識的回答...」
  And 明確標示這不是來自知識庫
```

### RAG 流程

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         RAG 流程                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  使用者問題：「useEffect 和 useLayoutEffect 差別？」                     │
│         │                                                               │
│         ▼                                                               │
│  ┌─────────────────┐                                                    │
│  │ 1. 語意搜尋     │ 找出相關文章（top 5）                              │
│  └────────┬────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ 2. 組裝 Prompt  │                                                    │
│  │                 │                                                    │
│  │  System: 你是知識庫助手...                                           │
│  │                 │                                                    │
│  │  Context:                                                            │
│  │  [文章1] useEffect 是用於處理副作用...                               │
│  │  [文章2] useLayoutEffect 在 DOM 更新後同步執行...                    │
│  │                 │                                                    │
│  │  Question: useEffect 和 useLayoutEffect 差別？                       │
│  │                 │                                                    │
│  └────────┬────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                    │
│  │ 3. LLM 生成回答 │                                                    │
│  └────────┬────────┘                                                    │
│           │                                                             │
│           ▼                                                             │
│  回傳答案 + 參考來源                                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### API 定義

```
POST /api/v1/chat
{
  "message": "useEffect 和 useLayoutEffect 差別？",
  "conversation_id": "conv_123",  // 可選，用於追蹤對話
  "include_sources": true
}

Response:
{
  "answer": "useEffect 和 useLayoutEffect 的主要差別在於執行時機...",
  "sources": [
    {"id": 123, "title": "React Hooks 完全指南", "relevance": 0.92},
    {"id": 456, "title": "useEffect 深入解析", "relevance": 0.85}
  ],
  "conversation_id": "conv_123"
}
```

### Prompt 模板

```python
SYSTEM_PROMPT = """你是一個知識庫助手，根據提供的文章內容回答問題。

規則：
1. 只根據提供的文章內容回答
2. 如果文章中沒有相關資訊，明確說明
3. 回答時標註參考來源（用 [1], [2] 等標記）
4. 使用繁體中文回答
5. 回答要簡潔但完整
"""

USER_PROMPT_TEMPLATE = """
參考文章：
{context}

問題：{question}

請根據以上文章回答問題。
"""
```

---

## User Story 4.4: Web UI 介面

### 描述
```
作為使用者
我想要一個網頁介面來瀏覽和搜尋我的知識庫
這樣我不用只靠 CLI
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: 瀏覽文章列表
  Given 知識庫有 50 篇文章
  When 我打開 Web UI
  Then 看到文章列表（分頁顯示）
  And 可以按時間、來源、標籤排序/過濾

Scenario: 搜尋介面
  Given 我在 Web UI
  When 我輸入搜尋詞
  Then 即時顯示搜尋結果
  And 可以切換關鍵字/語意搜尋

Scenario: Chat 介面
  Given 我在 Web UI 的 Chat 頁面
  When 我輸入問題
  Then 顯示 AI 回答
  And 顯示參考來源（可點擊）
  And 保留對話歷史
```

### UI 線框圖

```
┌─────────────────────────────────────────────────────────────────────────┐
│  📚 Knowledge Platform                              [搜尋] [Chat] [設定] │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  🔍 搜尋知識庫...                              [關鍵字 ▼] [搜尋] │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  篩選：[全部來源 ▼] [全部標籤 ▼] [最近更新 ▼]                          │
│                                                                         │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  📄 React Hooks 完全指南                                    2024-01-25  │
│     react.dev • React, Hooks                                           │
│     useState 是最常用的 Hook，用於在函數組件中添加狀態...              │
│                                                                         │
│  📄 Vue 3 Composition API                                   2024-01-24  │
│     vuejs.org • Vue, Composition API                                    │
│     Composition API 是 Vue 3 引入的新特性...                           │
│                                                                         │
│  📄 TypeScript 泛型指南                                     2024-01-23  │
│     typescriptlang.org • TypeScript, Generics                          │
│     泛型讓你可以編寫可重用的組件...                                     │
│                                                                         │
│  ─────────────────────────────────────────────────────────────────────  │
│  顯示 1-10 / 50                                    [< 上一頁] [下一頁 >] │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 優先級

| User Story | 優先級 | Phase |
|------------|--------|-------|
| 4.1 關鍵字搜尋 | P1 | Phase 2 |
| 4.2 語意搜尋 | P1 | Phase 3 |
| 4.3 Chat 對話 | P2 | Phase 4 |
| 4.4 Web UI | P2 | Phase 4 |
