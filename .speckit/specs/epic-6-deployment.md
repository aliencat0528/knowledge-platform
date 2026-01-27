# Epic 6: 部署與維運 (Deployment & Operations)

> 本文件定義平台的部署、維運和擴展相關規格。

---

## 概述

Knowledge Platform 支援多種部署方式：
- **Zeabur**：快速雲端部署（Phase 6 主要方案）
- **Docker Compose**：自架 VPS 部署
- **Terraform**：雲端自動化部署（Phase 7 選用）

核心原則：
- 容器化部署，環境一致
- CI/CD 自動化
- 資料持久化與備份
- 健康監控

---

## User Story 6.1: 一鍵雲端部署

### 描述
```
作為開發者
我想要一鍵部署到雲端平台
這樣我可以快速上線使用
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: Zeabur 部署
  Given 我有 Zeabur 帳號
  And 我 Fork 了專案到 GitHub
  When 我在 Zeabur 建立專案並連結 Repository
  And 設定必要的環境變數
  Then 服務自動部署並運行
  And 我可以透過網域存取 API

Scenario: 環境變數設定
  Given 我在 Zeabur Dashboard
  When 我設定 OPENAI_API_KEY
  Then 服務可正常使用 Chat 功能

Scenario: 持久化儲存
  Given 服務運行中
  When 我新增文章到知識庫
  And 服務重新部署
  Then 之前的資料仍然存在
```

### 部署需求

| 需求 | 說明 |
|------|------|
| 運算資源 | 1 vCPU, 512MB RAM（最低）|
| 儲存空間 | 1GB Volume（SQLite + ChromaDB）|
| 網路 | HTTPS、自訂網域支援 |
| 環境變數 | OPENAI_API_KEY（必要）|

---

## User Story 6.2: 自動化部署流程

### 描述
```
作為開發者
我想要 Push 程式碼後自動部署
這樣我不需要手動操作
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: PR 自動測試
  Given 我建立一個 Pull Request
  When GitHub Actions 執行
  Then 自動執行單元測試
  And 自動執行 Docker Build
  And 顯示測試結果

Scenario: Merge 自動部署
  Given PR 已通過測試
  When PR Merge 到 main 分支
  Then 自動觸發部署到 Zeabur
  And 部署完成後可驗證新功能

Scenario: 部署失敗回滾
  Given 新版本部署失敗
  When 健康檢查未通過
  Then 自動回滾到上一個版本
  And 通知開發者
```

### CI/CD 流程

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  Push   │───►│  Build  │───►│  Test   │───►│ Deploy  │
│         │    │         │    │         │    │         │
│  PR     │    │ Docker  │    │ pytest  │    │ Zeabur  │
│  Main   │    │ Vue     │    │ vue-tsc │    │         │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
```

---

## User Story 6.3: 健康監控

### 描述
```
作為運維人員
我想要監控服務健康狀態
這樣我可以及時發現問題
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: 基本健康檢查
  Given 服務運行中
  When 我呼叫 /api/v1/health
  Then 回傳 {"status": "ok"}

Scenario: 就緒檢查
  Given 服務啟動中
  When 資料庫連線成功
  Then /api/v1/health/ready 回傳 ready
  And Zeabur 開始接收流量

Scenario: 存活檢查
  Given 服務運行中
  When 每 30 秒執行存活檢查
  Then 確認服務仍在運行
  And 若失敗則重啟容器
```

### 健康檢查端點

| 端點 | 用途 | 檢查項目 |
|------|------|----------|
| `/api/v1/health` | 基本檢查 | 服務存活 |
| `/api/v1/health/ready` | 就緒檢查 | 資料庫連線 |
| `/api/v1/health/live` | 存活檢查 | 程序運行 |

---

## User Story 6.4: 資料備份

### 描述
```
作為使用者
我想要定期備份我的知識庫
這樣我不會遺失重要資料
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: 手動備份
  Given 知識庫有 100 篇文章
  When 我執行備份腳本
  Then 產生包含 SQLite 和 ChromaDB 的備份檔
  And 備份檔可下載

Scenario: 還原備份
  Given 我有一個備份檔
  When 我執行還原腳本
  Then 知識庫恢復到備份時的狀態
  And 所有文章和向量索引都存在

Scenario: 備份驗證
  Given 備份完成
  When 執行驗證
  Then 確認備份完整性
  And 記錄備份狀態
```

### 備份策略

| 類型 | 頻率 | 保留 |
|------|------|------|
| 每日備份 | 每天 00:00 | 7 天 |
| 每週備份 | 每週日 | 4 週 |
| 手動備份 | 依需求 | 永久 |

---

## User Story 6.5: 自架部署（Docker Compose）

### 描述
```
作為進階使用者
我想要在自己的伺服器部署
這樣我可以完全控制資料
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: Docker Compose 部署
  Given 我有一台 VPS
  And 安裝了 Docker
  When 我執行 docker compose up -d
  Then API 和 Web UI 服務啟動
  And 可透過 IP 或網域存取

Scenario: HTTPS 設定
  Given 我有自訂網域
  When 我設定 DOMAIN 環境變數
  And 使用 docker-compose.prod.yml
  Then Caddy 自動申請 SSL 憑證
  And 服務使用 HTTPS

Scenario: 資料持久化
  Given Docker Compose 運行中
  When 我停止並重啟容器
  Then 資料 Volume 保持不變
  And 所有資料仍然存在
```

---

## User Story 6.6: 雲端自動化部署（Phase 7 選用）

### 描述
```
作為 DevOps 工程師
我想要使用 Terraform 管理基礎設施
這樣我可以版本控制並自動化部署
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: Terraform 部署
  Given 我設定了雲端 Provider 憑證
  When 我執行 terraform apply
  Then 自動建立 VM、網路、儲存
  And 部署應用程式

Scenario: 多環境管理
  Given 我有 dev 和 prod 環境設定
  When 我切換到 prod 環境
  And 執行 terraform apply
  Then 只影響 prod 環境的資源

Scenario: 基礎設施變更
  Given 我修改了 Terraform 設定
  When 我執行 terraform plan
  Then 顯示將要變更的資源
  And 確認後才執行變更
```

### 支援的雲端平台

| 平台 | 狀態 | Phase |
|------|------|-------|
| DigitalOcean | 📋 規劃 | 7B |
| AWS | 📋 規劃 | 7C |
| GCP | 📋 規劃 | 7C |

---

## User Story 6.7: 監控與告警（Phase 7 選用）

### 描述
```
作為運維人員
我想要完整的監控儀表板
這樣我可以追蹤系統效能和問題
```

### 驗收條件 (Acceptance Criteria)

```gherkin
Scenario: Metrics 收集
  Given Prometheus 運行中
  When 應用程式處理請求
  Then 記錄請求數、延遲、錯誤率

Scenario: 儀表板
  Given Grafana 運行中
  When 我開啟儀表板
  Then 顯示 API 請求統計
  And 顯示資源使用量
  And 顯示錯誤趨勢

Scenario: 告警通知
  Given 設定了告警規則
  When 錯誤率超過閾值
  Then 發送 Slack/Email 通知
  And 記錄告警歷史
```

---

## 優先級

| User Story | 優先級 | Phase |
|------------|--------|-------|
| 6.1 一鍵雲端部署 | P1 | Phase 6 |
| 6.2 自動化部署流程 | P1 | Phase 6 |
| 6.3 健康監控 | P1 | Phase 6 |
| 6.4 資料備份 | P2 | Phase 6 |
| 6.5 自架部署 | P2 | Phase 6 |
| 6.6 雲端自動化部署 | P3 | Phase 7（選用）|
| 6.7 監控與告警 | P3 | Phase 7（選用）|
