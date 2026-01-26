# Phase 2 Tasks - 資料收集完整

> Phase 2 包含所有資料收集方式的實作，確保完整去重和多來源支援。

---

## 完成狀態總覽

| Task | 功能 | 分支 | 狀態 |
|------|------|------|------|
| 2.1 | .zip 匯入服務 | `feature/batch-import-sixth` | ✅ 完成 |
| 2.2 | .zip 匯入 API | `feature/batch-import-sixth` | ✅ 完成 |
| 2.3 | 擴充套件批量分頁 | `feature/batch-import-sixth` | ✅ 完成 |
| 2.4 | 關鍵字搜尋 API | `feature/batch-import-sixth` | ✅ 完成 |
| 2.5 | AI 對話匯入服務 | `feature/ai-chat-import-seventh` | ✅ 完成 |
| 2.6 | AI 對話匯入 API | `feature/ai-chat-import-seventh` | ✅ 完成 |
| 2.7 | AI 對話匯入 CLI | `feature/ai-chat-import-seventh` | ✅ 完成 |

---

# 已完成任務（PR #8）

## Task 2.1: .zip 匯入服務 ✅

### 描述
實作 Notion Export .zip 檔案的匯入服務

### 輸出
- `services/zip_import_service.py`

### 功能
- 解壓縮 .zip 檔案
- 解析 Notion 檔名格式（提取 page ID）
- 支援 .md 和 .html 檔案
- 整合去重邏輯

---

## Task 2.2: .zip 匯入 API ✅

### 描述
提供 .zip 檔案上傳和匯入的 API 端點

### 輸出
- `api/import_api.py`
- `scripts/import_zip.py`

### API 端點
- `POST /api/v1/import/zip` - 上傳並匯入
- `POST /api/v1/import/zip/preview` - 預覽內容

---

## Task 2.3: 擴充套件批量分頁 ✅

### 描述
在 Chrome 擴充套件中實作批量分頁抓取功能

### 輸出
- 更新 `popup/index.html` - 模式切換 UI
- 更新 `popup/popup.css` - 批量模式樣式
- 更新 `popup/popup.js` - 批量抓取邏輯

### 功能
- 模式切換（單頁/批量）
- 列出所有開啟的分頁
- 全選/取消全選
- 批量儲存到 /articles/batch

---

## Task 2.4: 關鍵字搜尋 API ✅

### 描述
實作關鍵字搜尋功能

### 輸出
- `api/search.py`

### API 端點
- `GET /api/v1/search` - 關鍵字搜尋
  - 參數：`q`, `source_type`, `tags`, `limit`, `offset`
  - 回傳：文章列表 + 評分 + 高亮

---

# 已完成任務（PR #9）

## Task 2.5: AI 對話匯入服務 ✅

### 描述
實作多種 AI 編輯器對話的匯入服務

### 輸入
- Claude Code：`~/.claude/projects/*/conversations/*.jsonl`
- Cursor：`~/Library/Application Support/Cursor/User/workspaceStorage/*/state.vscdb`
- Windsurf：`~/Library/Application Support/Windsurf/User/`
- Markdown：手動複製貼上的對話

### 輸出
- `services/chat_import_service.py`

### 功能
```python
class ChatImportService:
    # 支援的來源
    SOURCES = {
        "claude-code": {
            "format": "jsonl",
            "path_pattern": "~/.claude/projects/*/conversations/*.jsonl",
        },
        "cursor": {
            "format": "sqlite",
            "path_pattern": "~/Library/Application Support/Cursor/User/workspaceStorage/*/state.vscdb",
        },
        "markdown": {
            "format": "markdown",
            "path_pattern": None,  # 手動輸入
        },
    }

    async def import_jsonl(self, file_path: Path) -> ImportResult:
        """匯入 Claude Code JSONL 格式"""
        pass

    async def import_sqlite(self, file_path: Path) -> ImportResult:
        """匯入 Cursor/VS Code SQLite 格式"""
        pass

    async def import_markdown(self, content: str) -> ImportResult:
        """匯入 Markdown 格式對話"""
        pass

    async def auto_detect_and_import(self, path: Path) -> ImportResult:
        """自動偵測格式並匯入"""
        pass
```

### 驗證
```bash
# 匯入 Claude Code 對話
python scripts/import_chat.py ~/.claude/projects/my-project/conversations/

# 匯入 Cursor 對話
python scripts/import_chat.py ~/Library/Application\ Support/Cursor/ --format cursor
```

### 相依
- Task 2.1（ImportService 基礎）

### 估計時間
2 小時

---

## Task 2.6: AI 對話匯入 API ✅

### 描述
提供 AI 對話匯入的 API 端點

### 輸出
- 更新 `api/import_api.py`

### API 端點
```yaml
POST /api/v1/import/chat
Content-Type: application/json

{
  "source": "claude-code",  # or "cursor", "markdown"
  "content": "...",         # For markdown
  "file_path": "..."        # For file-based (optional, server-side only)
}

# 回應
{
  "success": true,
  "results": [...],
  "summary": {
    "new": 5,
    "skipped": 2,
    "error": 0
  }
}
```

### 相依
- Task 2.5

### 估計時間
1 小時

---

## Task 2.7: AI 對話匯入 CLI ✅

### 描述
提供命令列工具批量匯入 AI 對話

### 輸出
- `scripts/import_chat.py`

### 使用方式
```bash
# 自動偵測並匯入
python scripts/import_chat.py <path>

# 指定格式
python scripts/import_chat.py <path> --format claude-code
python scripts/import_chat.py <path> --format cursor
python scripts/import_chat.py <path> --format markdown

# 預覽模式
python scripts/import_chat.py <path> --preview

# 從剪貼簿匯入 markdown
python scripts/import_chat.py --clipboard
```

### 相依
- Task 2.5
- Task 2.6

### 估計時間
1 小時

---

# Phase 2 完成條件

```
✅ 可匯入 Notion Export .zip
✅ 可批量收藏分頁
✅ 可用關鍵字搜尋
✅ 可匯入 Claude Code 對話（JSONL）
✅ 可匯入 Cursor 對話（SQLite）
✅ 可匯入 Markdown 格式對話
✅ CLI 支援自動偵測格式
```

---

# 預估時間

| Task | 時間 |
|------|------|
| 2.1 .zip 匯入服務 | 1.5 hr ✅ |
| 2.2 .zip 匯入 API | 1 hr ✅ |
| 2.3 批量分頁 | 2 hr ✅ |
| 2.4 關鍵字搜尋 | 1.5 hr ✅ |
| 2.5 AI 對話服務 | 2 hr ✅ |
| 2.6 AI 對話 API | 1 hr ✅ |
| 2.7 AI 對話 CLI | 1 hr ✅ |
| **Phase 2 合計** | **~10 小時 ✅** |
