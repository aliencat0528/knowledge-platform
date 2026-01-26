# Epic 1: 資料收集 (Data Collection)

> 本文件定義資料收集相關的所有功能規格。

---

## User Story 1.1: 單頁抓取

### 描述
```
作為一個技術學習者
我想要一鍵收藏當前瀏覽的網頁
這樣我可以快速保存有價值的文章到我的知識庫
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: 成功收藏一般網頁
  Given 我正在瀏覽一篇技術文章
  And 本地服務正在運行
  When 我點擊擴充套件的「收藏此頁」按鈕
  Then 頁面內容被抓取並轉換成 Markdown
  And 資料被存入本地 SQLite
  And 我看到「收藏成功」的提示

Scenario: 本地服務未運行
  Given 我正在瀏覽一篇技術文章
  And 本地服務未運行
  When 我點擊擴充套件的「收藏此頁」按鈕
  Then 我看到「請先啟動本地服務」的錯誤提示

Scenario: 重複收藏同一頁面
  Given 我已經收藏過某篇文章
  When 我再次收藏同一篇文章（相同 URL）
  Then 系統檢查 content_hash
  And 如果內容相同，顯示「已存在，跳過」
  And 如果內容不同，更新文章並顯示「已更新」
```

### 技術備註
- 使用 Readability.js 提取主要內容
- 使用 Turndown.js 轉換成 Markdown
- source_type: 根據 URL 判斷（notion/medium/docs/web）
- source_id: URL 的 hash 或頁面特定 ID

### UI 規格

```
┌─────────────────────────────────┐
│  📥 Knowledge Collector         │
│  ─────────────────────────────  │
│                                 │
│  當前頁面：                      │
│  📄 React Hooks 完全指南        │
│  react.dev/reference/...       │
│                                 │
│  類型：[官方文件 ▼]             │
│  標籤：[React] [Hooks] [+]     │
│                                 │
│  ┌───────────────────────────┐ │
│  │     📄 收藏此頁面          │ │
│  └───────────────────────────┘ │
│                                 │
│  ─────────────────────────────  │
│  💡 服務狀態：🟢 運行中         │
│                                 │
└─────────────────────────────────┘
```

---

## User Story 1.2: 樹狀抓取（Notion 專用）⭐ Phase 1b 核心

### 描述
```
作為一個 Notion 使用者
我想要一鍵收藏 Notion 頁面及其所有子頁面
這樣我可以完整保存一個知識區塊
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: 成功抓取有子頁面的 Notion 頁面
  Given 我正在瀏覽一個 Notion 頁面
  And 該頁面有 5 個子頁面
  When 我點擊「收藏此頁面 + 子頁面」
  Then 系統遞迴抓取所有子頁面
  And 顯示抓取進度（1/6, 2/6...）
  And 所有頁面存入資料庫並保留父子關係
  And 顯示「成功收藏 6 個頁面」

Scenario: 子頁面有循環引用
  Given 頁面 A 連結到頁面 B
  And 頁面 B 又連結回頁面 A
  When 我抓取頁面 A + 子頁面
  Then 系統偵測到循環並跳過已抓取的頁面
  And 不會無限迴圈

Scenario: 只收藏當前 Notion 頁面
  Given 我正在瀏覽一個 Notion 頁面
  When 我點擊「只收藏此頁」
  Then 只抓取當前頁面，不遞迴
  And 顯示「成功收藏 1 個頁面」

Scenario: 選擇性收藏子頁面
  Given 我正在瀏覽一個有 10 個子頁面的 Notion 頁面
  When 我點擊「收藏 + 子頁面」
  Then 顯示子頁面列表供勾選
  And 我可以取消不需要的子頁面
  And 只抓取勾選的頁面
```

### 技術備註
- 從 DOM 中提取子頁面連結
- 使用 BFS 或 DFS 遍歷
- 維護 visited set 避免循環
- 記錄 article_hierarchy 關係

### Notion 頁面偵測

```javascript
// 判斷是否為 Notion 頁面
function isNotionPage(url) {
  return /notion\.so|notion\.site/.test(url);
}

// 子頁面選擇器（可能需要更新）
const SUB_PAGE_SELECTORS = [
  '[data-block-id] a[href*="notion.so"]',
  '.notion-page-block a',
  '.notion-collection-item a'
];
```

### UI 規格（Notion 模式）

```
┌─────────────────────────────────┐
│  📥 Knowledge Collector         │
│  ─────────────────────────────  │
│                                 │
│  🔗 Notion 頁面偵測到            │
│                                 │
│  📄 Backend 教育訓練文件         │
│  notion.so/...                  │
│                                 │
│  發現 5 個子頁面：               │
│  ☑️ API 設計規範                │
│  ☑️ 資料庫設計                  │
│  ☑️ 部署流程                    │
│  ☐ 會議記錄（取消勾選）          │
│  ☑️ 開發環境設定                │
│                                 │
│  ┌───────────────────────────┐ │
│  │  📄 只收藏此頁             │ │
│  └───────────────────────────┘ │
│  ┌───────────────────────────┐ │
│  │  📂 收藏此頁 + 勾選的子頁面 │ │
│  └───────────────────────────┘ │
│                                 │
│  ─────────────────────────────  │
│  💡 服務狀態：🟢 運行中         │
│                                 │
└─────────────────────────────────┘
```

### 進度顯示

```
┌─────────────────────────────────┐
│  📥 正在收藏...                  │
│  ─────────────────────────────  │
│                                 │
│  ████████░░░░░░░░░░░░  3/6      │
│                                 │
│  ✅ Backend 教育訓練文件         │
│  ✅ API 設計規範                │
│  🔄 資料庫設計（進行中）         │
│  ⏳ 部署流程                    │
│  ⏳ 開發環境設定                │
│                                 │
└─────────────────────────────────┘
```

---

## User Story 1.3: 批量分頁抓取

### 描述
```
作為一個研究者
我想要一鍵收藏所有開啟的技術文章分頁
這樣我不用一個一個手動收藏
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: 成功批量收藏
  Given 我開啟了 10 個分頁
  And 其中 8 個是技術文章，2 個是 YouTube
  When 我點擊「收藏所有分頁」
  Then 系統顯示分頁列表（自動排除 YouTube）
  And 我可以手動勾選/取消
  And 點擊確認後批量抓取
  And 顯示「成功收藏 8 個頁面」

Scenario: 部分頁面抓取失敗
  Given 我選擇收藏 5 個分頁
  And 其中 1 個需要登入
  When 批量抓取執行
  Then 4 個成功，1 個失敗
  And 顯示「成功 4 個，失敗 1 個」
  And 可以查看失敗原因
```

### 過濾規則
```javascript
// 自動排除的網站
const EXCLUDED_PATTERNS = [
  /youtube\.com/,
  /facebook\.com/,
  /twitter\.com/,
  /instagram\.com/,
  /mail\.google\.com/,
  /chrome:\/\//,
  /chrome-extension:\/\//,
  /localhost/,
];
```

---

## User Story 1.4: .zip 匯入（Notion Export）

### 描述
```
作為一個從 Notion 匯出筆記的使用者
我想要把 Export 的 .zip 檔案匯入到知識庫
這樣我可以整合歷史筆記
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: 成功匯入 .zip
  Given 我有一個 Notion Export 的 .zip 檔案
  And 裡面有 50 個 .md 檔案
  When 我執行 `python scripts/import_zip.py export.zip`
  Then 系統解壓並解析所有檔案
  And 跳過空檔案（乾淨標題但無內容的）
  And 清理檔名中的 Page ID
  And 顯示匯入統計（新增 45，跳過 5）

Scenario: 重複匯入
  Given 我已經匯入過 export.zip
  When 我再次匯入同一個 .zip
  Then 系統比對 source_id 和 content_hash
  And 相同的跳過，有變更的更新
  And 顯示「新增 0，更新 3，跳過 42」
```

### 檔名解析規則
```python
# 輸入: "Backend 教育訓練文件 d280e341cee24ac5985312044ecab021.md"
# 輸出: title="Backend 教育訓練文件", source_id="d280e341..."

import re
def parse_filename(filename):
    match = re.search(r'\s+([a-f0-9]{32})$', filename.stem)
    if match:
        return {
            "title": filename.stem[:match.start()].strip(),
            "source_id": match.group(1)
        }
    return {
        "title": filename.stem,
        "source_id": md5(filename.stem)
    }
```

---

## User Story 1.5: 排程爬取

### 描述
```
作為一個想追蹤技術更新的使用者
我想要定期自動抓取指定網站的新文章
這樣我不會錯過重要更新
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: 設定排程任務
  Given 我想追蹤 react.dev/blog
  When 我新增一個排程任務
  And 設定每天抓取一次
  Then 系統每天自動檢查新文章
  And 只抓取尚未收藏的文章

Scenario: 排程執行
  Given 已設定追蹤 react.dev/blog
  And 上次抓取後有 2 篇新文章
  When 排程時間到達
  Then 系統自動抓取 2 篇新文章
  And 記錄到 import_batches
```

### 支援的網站（初期）
- React Blog (react.dev/blog)
- Vue Blog (blog.vuejs.org)
- TypeScript Blog (devblogs.microsoft.com/typescript)

---

## User Story 1.6: 外部工具整合

### 描述
```
作為一個第三方開發者
我想要透過 API 將爬取內容送入平台
這樣我可以整合現有的爬蟲工具或自製腳本
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: 透過 API 送入文章
  Given 我有一個自製的爬蟲腳本
  And 本地服務正在運行
  When 我呼叫 POST /api/v1/articles
  And 送入符合格式的 JSON
  Then 文章被儲存到資料庫
  And 回傳成功結果與 article_id

Scenario: 批量送入文章
  Given 我有 20 篇文章要匯入
  When 我呼叫 POST /api/v1/articles/batch
  And 送入文章陣列
  Then 系統批量處理並回傳統計
  And 顯示「新增 15，更新 3，跳過 2」

Scenario: 查詢 API 文件
  Given 我想了解 API 規格
  When 我訪問 /docs 或 /redoc
  Then 看到完整的 OpenAPI 文件
  And 可以直接測試 API
```

### API 規格

```yaml
# 單篇文章
POST /api/v1/articles
Content-Type: application/json

{
  "source_type": "web",           # 必填：notion | medium | docs | web
  "source_id": "unique-id",       # 必填：來源唯一識別
  "title": "文章標題",             # 必填
  "content": "# Markdown 內容",   # 必填
  "url": "https://...",           # 選填
  "author": "作者",               # 選填
  "tags": ["tag1", "tag2"],       # 選填
  "published_at": "2024-01-01"    # 選填
}

# 批量文章
POST /api/v1/articles/batch
{
  "articles": [ /* 同上格式 */ ]
}
```

### 錯誤回應格式

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "source_type is required",
    "details": { "field": "source_type" }
  }
}
```

---

## 優先級（調整後）

| User Story | 優先級 | Phase | 說明 |
|------------|--------|-------|------|
| 1.1 單頁抓取 | P0 | Phase 1a | 基礎功能 |
| 1.2 樹狀抓取 | **P0** | **Phase 1b** | **Notion 優先** |
| 1.6 外部整合 | P0 | Phase 1a | API 文件自動生成 |
| 1.3 批量分頁 | P1 | Phase 2 | |
| 1.4 .zip 匯入 | P1 | Phase 2 | |
| 1.5 排程爬取 | P3 | Phase 4 | |
