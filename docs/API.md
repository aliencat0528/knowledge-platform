# Knowledge Platform - API 參考

> 本檔為 API 端點的完整清單（單一正本）。README 只做摘要並連結至此。
> 互動式文件：啟動服務後訪問 http://localhost:8000/docs（Swagger UI）。
> 認證：所有 `/api/v1/*`（health 除外）需帶 `X-API-Key` header，詳見 `docs/DEPLOYMENT.md` 環境變數 `API_KEY`。

---

## 文章 Articles

| 方法 | 路徑 | 說明 |
|------|------|------|
| `POST` | `/api/v1/articles` | 新增文章 |
| `POST` | `/api/v1/articles/batch` | 批量新增 |
| `GET` | `/api/v1/articles` | 列出文章 |

## 匯入 Import

| 方法 | 路徑 | 說明 |
|------|------|------|
| `POST` | `/api/v1/import/zip` | 匯入 Notion Export .zip |
| `POST` | `/api/v1/import/chat` | 匯入 AI 對話 |

## 搜尋 Search

| 方法 | 路徑 | 說明 |
|------|------|------|
| `GET` | `/api/v1/search` | 關鍵字搜尋 |
| `POST` | `/api/v1/search/semantic` | 語意搜尋 |

## Notion 同步 Sync

| 方法 | 路徑 | 說明 |
|------|------|------|
| `POST` | `/api/v1/sync/notion` | 同步文章到 Notion |
| `POST` | `/api/v1/sync/notion/batch` | 批量同步到 Notion |
| `GET` | `/api/v1/sync/status` | 取得同步狀態 |

## Chat（RAG）

| 方法 | 路徑 | 說明 |
|------|------|------|
| `POST` | `/api/v1/chat` | Chat 對話（RAG） |
| `GET` | `/api/v1/chat/history` | 對話歷史列表 |
| `GET` | `/api/v1/chat/history/{id}` | 對話詳情 |
| `DELETE` | `/api/v1/chat/history/{id}` | 刪除對話 |

## 排程 Scheduler

| 方法 | 路徑 | 說明 |
|------|------|------|
| `POST` | `/api/v1/scheduler/tasks` | 建立排程任務 |
| `GET` | `/api/v1/scheduler/tasks` | 列出排程任務 |
| `PUT` | `/api/v1/scheduler/tasks/{id}` | 更新排程任務 |
| `DELETE` | `/api/v1/scheduler/tasks/{id}` | 刪除排程任務 |
| `POST` | `/api/v1/scheduler/tasks/{id}/run` | 手動執行任務 |
| `GET` | `/api/v1/scheduler/status` | 排程器狀態 |
| `POST` | `/api/v1/scheduler/start` | 啟動排程器 |
| `POST` | `/api/v1/scheduler/stop` | 停止排程器 |

## 健康檢查 Health（免認證）

| 方法 | 路徑 | 說明 |
|------|------|------|
| `GET` | `/api/v1/health` | 基本健康檢查 |
| `GET` | `/api/v1/health/ready` | Readiness 檢查（驗證 DB 和 ChromaDB） |
| `GET` | `/api/v1/health/live` | Liveness 檢查 |

---

> 生產環境（`ENVIRONMENT=production`）會自動關閉 `/docs`、`/redoc`、`/openapi.json` 並隱藏敏感資訊。

## 相關文件

- 各端點的請求／回應範例與測試指令 → `docs/TESTING.md`
- 部署與環境變數（含 `API_KEY`）→ `docs/DEPLOYMENT.md`
- 系統架構與模組職責 → `docs/ARCHITECTURE.md`
