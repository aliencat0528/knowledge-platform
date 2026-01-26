# Epic 5: 第三方整合 (External Integration)

> 本文件定義平台如何與外部工具整合，確保 API 的開放性與一致性。

---

## 概述

Knowledge Platform 設計為開放平台，支援：
- 自製爬蟲腳本
- 其他瀏覽器擴充套件
- 第三方匯出工具
- 自動化工作流程（如 n8n、Zapier）

所有整合透過 RESTful API 進行，無需共用程式碼。

---

## User Story 5.1: API 文件

### 描述
```
作為一個想整合的開發者
我想要查閱完整的 API 文件
這樣我可以了解如何與平台對接
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: 查看 Swagger UI
  Given 本地服務正在運行
  When 我訪問 http://localhost:8000/docs
  Then 看到 Swagger UI 介面
  And 列出所有可用的 API 端點
  And 可以直接在頁面上測試 API

Scenario: 查看 ReDoc
  Given 本地服務正在運行
  When 我訪問 http://localhost:8000/redoc
  Then 看到 ReDoc 格式的文件
  And 文件結構清晰易讀

Scenario: 下載 OpenAPI Spec
  Given 本地服務正在運行
  When 我訪問 http://localhost:8000/openapi.json
  Then 取得 OpenAPI 3.0 格式的 JSON 檔案
  And 可以匯入 Postman 或其他工具
```

### 技術備註
- FastAPI 自動生成 OpenAPI 文件
- 確保所有端點都有描述和範例
- 使用 Pydantic 模型自動產生 Schema

---

## User Story 5.2: 認證機制

### 描述
```
作為一個部署在非本機環境的使用者
我想要透過 API Key 保護我的服務
這樣只有授權的工具才能存取
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: 本地模式（預設）
  Given 服務在 localhost 運行
  And 未設定 API_KEY 環境變數
  When 我呼叫任何 API
  Then 不需要認證即可存取

Scenario: 啟用 API Key 認證
  Given 服務設定了 API_KEY=my-secret-key
  When 我呼叫 API 但未帶 Header
  Then 回傳 401 Unauthorized

Scenario: 正確的 API Key
  Given 服務設定了 API_KEY=my-secret-key
  When 我呼叫 API 並帶上 Header: X-API-Key: my-secret-key
  Then 正常回傳結果
```

### API Key 設定

```bash
# .env
API_KEY=your-secret-api-key  # 設定後啟用認證，留空則不需認證
```

### Header 格式

```http
GET /api/v1/articles HTTP/1.1
Host: localhost:8000
X-API-Key: your-secret-api-key
```

---

## User Story 5.3: 統一錯誤格式

### 描述
```
作為一個整合開發者
我想要收到格式統一的錯誤回應
這樣我可以統一處理各種錯誤情況
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: 欄位驗證錯誤
  Given 我呼叫 POST /api/v1/articles
  When 缺少必填欄位 source_type
  Then 回傳 422 Unprocessable Entity
  And 錯誤格式符合規範

Scenario: 資源不存在
  Given 我呼叫 GET /api/v1/articles/99999
  When 該文章不存在
  Then 回傳 404 Not Found
  And 錯誤格式符合規範

Scenario: 伺服器錯誤
  Given 發生未預期的錯誤
  Then 回傳 500 Internal Server Error
  And 錯誤訊息不洩漏敏感資訊
```

### 錯誤回應格式

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable error message",
    "details": {
      "field": "source_type",
      "reason": "required"
    }
  }
}
```

### 錯誤代碼列表

| HTTP Status | Error Code | 說明 |
|-------------|------------|------|
| 400 | BAD_REQUEST | 請求格式錯誤 |
| 401 | UNAUTHORIZED | 未認證 |
| 403 | FORBIDDEN | 無權限 |
| 404 | NOT_FOUND | 資源不存在 |
| 409 | CONFLICT | 資源衝突（如重複） |
| 422 | VALIDATION_ERROR | 欄位驗證失敗 |
| 500 | INTERNAL_ERROR | 伺服器錯誤 |

---

## User Story 5.4: 整合範例

### 描述
```
作為一個想快速上手的開發者
我想要參考整合範例程式碼
這樣我可以快速完成整合
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: Python 範例
  Given 我查看 docs/examples/
  Then 找到 python_example.py
  And 範例可直接執行
  And 包含新增、查詢、搜尋的範例

Scenario: cURL 範例
  Given 我查看 API 文件
  Then 每個端點都有 cURL 範例
  And 可以直接複製執行
```

### Python 範例

```python
# examples/python_example.py
import httpx

BASE_URL = "http://localhost:8000/api/v1"

# 新增文章
def add_article(title: str, content: str, url: str = None):
    response = httpx.post(f"{BASE_URL}/articles", json={
        "source_type": "web",
        "source_id": hashlib.md5(url.encode()).hexdigest() if url else str(uuid4()),
        "title": title,
        "content": content,
        "url": url
    })
    return response.json()

# 搜尋文章
def search(query: str):
    response = httpx.get(f"{BASE_URL}/search", params={"q": query})
    return response.json()

# 批量新增
def add_batch(articles: list):
    response = httpx.post(f"{BASE_URL}/articles/batch", json={
        "articles": articles
    })
    return response.json()
```

### cURL 範例

```bash
# 新增文章
curl -X POST http://localhost:8000/api/v1/articles \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "web",
    "source_id": "example-001",
    "title": "Example Article",
    "content": "# Hello\n\nThis is content."
  }'

# 搜尋
curl "http://localhost:8000/api/v1/search?q=React"

# 批量新增
curl -X POST http://localhost:8000/api/v1/articles/batch \
  -H "Content-Type: application/json" \
  -d '{
    "articles": [
      {"source_type": "web", "source_id": "1", "title": "Article 1", "content": "..."},
      {"source_type": "web", "source_id": "2", "title": "Article 2", "content": "..."}
    ]
  }'
```

---

## User Story 5.5: Webhook 通知（Phase 4+）

### 描述
```
作為一個想接收即時通知的使用者
我想要設定 Webhook
這樣當有新文章或更新時可以收到通知
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: 設定 Webhook
  Given 我有一個接收通知的 endpoint
  When 我設定 WEBHOOK_URL 環境變數
  Then 系統會在事件發生時發送通知

Scenario: 新文章通知
  Given 已設定 Webhook
  When 新文章被儲存
  Then 發送 POST 請求到 Webhook URL
  And 包含文章資訊
```

### Webhook 格式

```json
{
  "event": "article.created",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "article_id": 123,
    "title": "New Article",
    "source_type": "web"
  }
}
```

### 支援的事件

| Event | 說明 |
|-------|------|
| article.created | 新文章建立 |
| article.updated | 文章更新 |
| batch.completed | 批量匯入完成 |
| sync.completed | Notion 同步完成 |

---

## 優先級

| User Story | 優先級 | Phase |
|------------|--------|-------|
| 5.1 API 文件 | P0 | Phase 1a |
| 5.3 統一錯誤格式 | P0 | Phase 1a |
| 5.4 整合範例 | P1 | Phase 2 |
| 5.2 認證機制 | P2 | Phase 3 |
| 5.5 Webhook 通知 | P3 | Phase 4+ |

---

## 整合架構圖

```
┌─────────────────────────────────────────────────────────────┐
│                    外部整合架構                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   外部工具                                                   │
│   ─────────                                                 │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐      │
│   │ 自製    │  │ 其他    │  │ n8n /   │  │ CLI     │      │
│   │ 爬蟲    │  │ 擴充套件│  │ Zapier  │  │ Scripts │      │
│   └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘      │
│        │            │            │            │            │
│        └────────────┴────────────┴────────────┘            │
│                          │                                  │
│                          ▼                                  │
│        ┌─────────────────────────────────────┐             │
│        │           HTTP REST API              │             │
│        │    POST /api/v1/articles            │             │
│        │    POST /api/v1/articles/batch      │             │
│        │    GET  /api/v1/search              │             │
│        │    ...                              │             │
│        └─────────────────┬───────────────────┘             │
│                          │                                  │
│                          ▼                                  │
│        ┌─────────────────────────────────────┐             │
│        │       Knowledge Platform             │             │
│        │           Backend                    │             │
│        └─────────────────────────────────────┘             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```
