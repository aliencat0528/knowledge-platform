# Phase 4 Tasks - 完整體驗

> Phase 4 實作 Chat RAG 功能、排程爬取和 Web UI。

---

## 完成狀態總覽

| Task | 功能 | 分支 | 狀態 |
|------|------|------|------|
| 4.1 | RAG 流程設計 | `feature/chat-rag-tenth` | ✅ 完成 |
| 4.2 | Chat Service | `feature/chat-rag-tenth` | ✅ 完成 |
| 4.3 | Chat API | `feature/chat-rag-tenth` | ✅ 完成 |
| 4.4 | 對話歷史 | `feature/chat-rag-tenth` | ✅ 完成 |
| 4.5 | 排程服務 | `feature/scheduler-eleventh` | ✅ 完成 |
| 4.6 | 排程 API | `feature/scheduler-eleventh` | ✅ 完成 |
| 4.7 | Vue 3 專案設定 | `feature/web-ui-twelfth` | 📋 待開始 |
| 4.8 | 文章列表頁 | `feature/web-ui-twelfth` | 📋 待開始 |
| 4.9 | 搜尋頁 | `feature/web-ui-twelfth` | 📋 待開始 |
| 4.10 | Chat 頁 | `feature/web-ui-twelfth` | 📋 待開始 |
| 4.11 | 設定頁 | `feature/web-ui-twelfth` | 📋 待開始 |
| 4.12 | 整合測試 | `feature/web-ui-twelfth` | 📋 待開始 |

---

# feature/chat-rag-tenth 分支任務

## Task 4.1: RAG 流程設計

### 描述
設計並實作 RAG (Retrieval-Augmented Generation) 流程

### 輸出
- `services/chat_service.py`

### RAG 流程
```
用戶問題
    ↓
1. 語意搜尋 (EmbedService + VectorStore)
    ↓
2. 取得相關文章片段 (top-k)
    ↓
3. 建構 Prompt (System + Context + Question)
    ↓
4. 呼叫 LLM (OpenAI GPT-4o-mini)
    ↓
5. 回傳答案 + 引用來源
```

### 功能
```python
class ChatService:
    def __init__(self, embed_service: EmbedService, llm_provider: str = "openai"):
        """初始化 Chat 服務"""
        pass

    async def search_context(self, query: str, limit: int = 5) -> list[dict]:
        """搜尋相關上下文"""
        pass

    async def build_prompt(self, query: str, context: list[dict]) -> str:
        """建構 RAG Prompt"""
        pass

    async def chat(self, query: str, conversation_id: str | None = None) -> dict:
        """執行 RAG 對話"""
        pass
```

### 相依
- Task 3.2 (EmbedService)
- Task 3.3 (語意搜尋)

---

## Task 4.2: Chat Service 實作

### 描述
實作完整的 Chat Service，包含對話管理和 LLM 呼叫

### 輸出
- 更新 `services/chat_service.py`
- 新增 `storage/models.py` 對話模型

### 功能
- 對話歷史管理（記憶體或資料庫）
- System Prompt 設計
- Context 長度控制
- 串流輸出支援（可選）
- 引用來源標註

### 驗證
```python
from packages.server.services.chat_service import ChatService

service = ChatService()
response = await service.chat("如何在 React 中使用 useState?")
print(response["answer"])
print(response["sources"])
```

### 相依
- Task 4.1

---

## Task 4.3: Chat API

### 描述
提供 Chat 對話的 API 端點

### 輸出
- `api/chat.py`

### API 端點
```yaml
POST /api/v1/chat
Content-Type: application/json

{
  "message": "如何在 React 中管理狀態?",
  "conversation_id": "optional-uuid",  # 可選，用於多輪對話
  "options": {
    "model": "gpt-4o-mini",           # 可選
    "temperature": 0.7,               # 可選
    "max_context": 5                  # 可選，最多取幾篇相關文章
  }
}

# 回應
{
  "success": true,
  "data": {
    "answer": "在 React 中管理狀態可以使用...",
    "sources": [
      {
        "id": 123,
        "title": "useState Hook 教學",
        "url": "...",
        "snippet": "..."
      }
    ],
    "conversation_id": "uuid-xxx",
    "usage": {
      "prompt_tokens": 500,
      "completion_tokens": 200
    }
  }
}
```

### 相依
- Task 4.2

---

## Task 4.4: 對話歷史

### 描述
實作對話歷史儲存和查詢功能

### 輸出
- 更新 `storage/database.py` - 新增 conversations 表
- 更新 `api/chat.py` - 新增歷史查詢端點

### 資料庫 Schema
```sql
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,           -- UUID
    title TEXT,                    -- 對話標題（自動產生）
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,            -- user | assistant
    content TEXT NOT NULL,
    sources TEXT,                  -- JSON array of source references
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);
```

### API 端點
```yaml
GET /api/v1/chat/history
# 列出所有對話

GET /api/v1/chat/history/{conversation_id}
# 取得單一對話歷史

DELETE /api/v1/chat/history/{conversation_id}
# 刪除對話
```

### 相依
- Task 4.3

---

# Phase 4 第一分支完成條件

```
✅ RAG 流程可正常運作
✅ Chat API 可回答問題
✅ 回答包含引用來源
✅ 對話歷史可儲存和查詢
✅ 多輪對話支援
```

---

# feature/scheduler-eleventh 分支任務

## Task 4.5: 排程服務

### 描述
實作排程爬取服務，定期抓取指定 URL

### 輸出
- `services/scheduler_service.py`

### 功能
```python
class SchedulerService:
    def __init__(self):
        """初始化 APScheduler"""
        pass

    async def add_task(self, name: str, url_pattern: str, cron: str) -> dict:
        """新增排程任務"""
        pass

    async def remove_task(self, task_id: int) -> bool:
        """移除排程任務"""
        pass

    async def list_tasks(self) -> list[dict]:
        """列出所有任務"""
        pass

    async def run_task(self, task_id: int) -> dict:
        """手動執行任務"""
        pass
```

### 相依
- Phase 1a（文章儲存）

---

## Task 4.6: 排程 API

### 描述
提供排程任務管理的 API 端點

### 輸出
- `api/scheduler.py`

### API 端點
```yaml
POST /api/v1/scheduler/tasks
# 新增排程任務

GET /api/v1/scheduler/tasks
# 列出所有任務

DELETE /api/v1/scheduler/tasks/{task_id}
# 刪除任務

POST /api/v1/scheduler/tasks/{task_id}/run
# 手動執行任務
```

### 相依
- Task 4.5

---

# Phase 4 第二分支完成條件

```
✅ 可新增排程任務
✅ 排程可定時執行
✅ 可手動觸發任務
✅ 任務執行結果可查詢
```

---

# feature/web-ui-twelfth 分支任務

## Task 4.7: Vue 3 專案設定

### 描述
初始化 Vue 3 + Vite 專案

### 輸出
- `packages/web-ui/` 完整專案結構

### 技術棧
- Vue 3 (Composition API)
- Vite
- Tailwind CSS
- Pinia (狀態管理)
- Vue Router

---

## Task 4.8: 文章列表頁

### 描述
實作文章列表頁面

### 功能
- 文章列表（分頁）
- 篩選（來源類型、標籤）
- 排序（日期、標題）
- 文章詳情預覽

---

## Task 4.9: 搜尋頁

### 描述
實作搜尋功能頁面

### 功能
- 關鍵字搜尋
- 語意搜尋切換
- 搜尋結果列表
- 結果高亮

---

## Task 4.10: Chat 頁

### 描述
實作 Chat 對話頁面

### 功能
- 對話介面
- 對話歷史列表
- 引用來源展示
- 新對話建立

---

## Task 4.11: 設定頁

### 描述
實作設定管理頁面

### 功能
- API 設定（OpenAI Key）
- Notion 同步設定
- 排程任務管理
- 系統狀態

---

## Task 4.12: 整合測試

### 描述
完整功能整合測試

### 測試項目
- 擴充套件 → API → 資料庫
- 搜尋功能（關鍵字 + 語意）
- Chat 功能
- Notion 同步
- Web UI 操作

---

# Phase 4 第三分支完成條件

```
□ Vue 3 專案可運行
□ 文章列表可瀏覽
□ 搜尋功能可用
□ Chat 對話可用
□ 設定頁可管理配置
□ 整合測試通過
```

---

# 預估時間

| Task | 時間 |
|------|------|
| 4.1 RAG 流程設計 | 2 hr |
| 4.2 Chat Service | 2 hr |
| 4.3 Chat API | 1.5 hr |
| 4.4 對話歷史 | 1.5 hr |
| **chat-rag-tenth 合計** | **~7 小時** |
| 4.5 排程服務 | 2 hr |
| 4.6 排程 API | 1.5 hr |
| **scheduler-eleventh 合計** | **~3.5 小時** |
| 4.7 Vue 3 設定 | 1 hr |
| 4.8 文章列表頁 | 2 hr |
| 4.9 搜尋頁 | 2 hr |
| 4.10 Chat 頁 | 2 hr |
| 4.11 設定頁 | 1.5 hr |
| 4.12 整合測試 | 2 hr |
| **web-ui-twelfth 合計** | **~10.5 小時** |
| **Phase 4 總計** | **~21 小時** |
