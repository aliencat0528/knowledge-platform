# 部署指南

> 本文件說明 Knowledge Platform 的各種部署方式。

---

## 目錄

1. [快速部署（Zeabur）](#1-快速部署zeabur)
2. [本地開發](#2-本地開發)
3. [Docker Compose 部署](#3-docker-compose-部署)
4. [進階部署（Terraform）](#4-進階部署terraform)
5. [環境變數說明](#5-環境變數說明)
6. [故障排除](#6-故障排除)

---

## 1. 快速部署（Zeabur）

### 前置需求
- GitHub 帳號
- Zeabur 帳號（[註冊](https://zeabur.com)）
- OpenAI API Key

### 部署步驟

#### Step 1: Fork 專案
1. 前往 [knowledge-platform](https://github.com/aliencat0528/knowledge-platform)
2. 點擊 Fork

#### Step 2: 建立 Zeabur 專案
1. 登入 [Zeabur Dashboard](https://dash.zeabur.com)
2. 點擊「New Project」
3. 選擇區域（建議：Singapore 或 Tokyo）

#### Step 3: 部署服務
1. 點擊「Add Service」>「Git」
2. 選擇你 Fork 的 Repository
3. Zeabur 會自動偵測 `zeabur.json` 設定

#### Step 4: 設定環境變數
在 Zeabur Dashboard 中設定以下變數：

| 變數 | 必要 | 說明 |
|------|------|------|
| `OPENAI_API_KEY` | ✅ | OpenAI API 金鑰 |
| `ANTHROPIC_API_KEY` | ❌ | Anthropic API 金鑰 |
| `NOTION_API_KEY` | ❌ | Notion 整合金鑰 |
| `NOTION_DATABASE_ID` | ❌ | Notion 資料庫 ID |

#### Step 5: 綁定網域（選用）
1. 在 Zeabur Dashboard 點擊「Networking」
2. 新增自訂網域或使用 Zeabur 提供的子網域

#### Step 6: 驗證部署
```bash
curl https://your-domain.zeabur.app/api/v1/health
# 應回傳: {"status": "ok", "version": "0.1.0"}
```

---

## 2. 本地開發

### 前置需求
- Python 3.11+
- Node.js 18+
- Git

### 啟動步驟

```bash
# 1. Clone 專案
git clone https://github.com/aliencat0528/knowledge-platform.git
cd knowledge-platform

# 2. 設定環境變數
cp .env.example .env
# 編輯 .env 填入 API Keys

# 3. 安裝後端依賴
pip install -r packages/server/requirements.txt

# 4. 啟動後端
python -m uvicorn packages.server.main:app --reload

# 5. 安裝前端依賴（另開終端機）
cd packages/web-ui
npm install

# 6. 啟動前端
npm run dev
```

### 存取
- API: http://localhost:8000
- Web UI: http://localhost:5173
- API Docs: http://localhost:8000/docs

---

## 3. Docker Compose 部署

### 開發環境

```bash
cd deploy

# 設定環境變數
export OPENAI_API_KEY=sk-your-key

# 啟動服務
docker compose up -d

# 查看日誌
docker compose logs -f
```

存取：http://localhost

### 生產環境（含 HTTPS）

```bash
cd deploy

# 設定環境變數
export DOMAIN=knowledge.yourdomain.com
export OPENAI_API_KEY=sk-your-key

# 使用生產設定啟動
docker compose -f docker-compose.prod.yml up -d
```

存取：https://knowledge.yourdomain.com

### 注意事項
- 確保 DNS 已指向伺服器
- 確保 80/443 port 已開放
- Caddy 會自動申請 Let's Encrypt 憑證

---

## 4. 進階部署（Terraform）

詳見 [deploy/terraform/README.md](../deploy/terraform/README.md)

### 簡要說明

Terraform 適用於：
- 需要多環境（dev/staging/prod）
- 團隊協作管理基礎設施
- 需要自動化災難恢復

目前支援規劃：
- DigitalOcean Droplet
- AWS EC2
- GCP Compute Engine

---

## 5. 環境變數說明

### 必要變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `OPENAI_API_KEY` | - | OpenAI API 金鑰（Chat/Embedding 必要）|

### 選用變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `ANTHROPIC_API_KEY` | - | Anthropic Claude API 金鑰 |
| `NOTION_API_KEY` | - | Notion Integration Token |
| `NOTION_DATABASE_ID` | - | Notion Database ID |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 服務位址 |

### 系統變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `ENVIRONMENT` | `development` | 環境標記 |
| `DEBUG` | `true` | 除錯模式 |
| `DATABASE_PATH` | `./data/knowledge.db` | SQLite 路徑 |
| `CHROMA_PATH` | `./data/chroma` | ChromaDB 路徑 |
| `HOST` | `127.0.0.1` | 伺服器綁定位址 |
| `PORT` | `8000` | 伺服器埠號 |

### Provider 變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `LLM_PROVIDER` | `openai` | LLM 提供者 |
| `LLM_MODEL` | `gpt-4o-mini` | LLM 模型 |
| `EMBEDDING_PROVIDER` | `openai` | Embedding 提供者 |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding 模型 |

---

## 6. 故障排除

### 常見問題

#### Q: 部署後 API 回傳 500 錯誤
**A:** 檢查環境變數是否正確設定，特別是 `OPENAI_API_KEY`。

```bash
# Zeabur: 在 Dashboard 檢查 Variables
# Docker: 檢查 .env 檔案
docker compose logs api
```

#### Q: 資料庫找不到
**A:** 確認 Volume 正確掛載：

```bash
# Docker
docker volume ls
docker volume inspect deploy_api_data
```

#### Q: HTTPS 憑證申請失敗
**A:** 確認：
1. DNS 已正確指向伺服器
2. 80/443 port 已開放
3. 網域格式正確

```bash
# 檢查 Caddy 日誌
docker compose -f docker-compose.prod.yml logs caddy
```

#### Q: ChromaDB 初始化失敗
**A:** 可能是記憶體不足，增加容器記憶體限制：

```yaml
# docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 1G
```

### 取得協助

- [GitHub Issues](https://github.com/aliencat0528/knowledge-platform/issues)
- [API 文件](http://localhost:8000/docs)

---

## 部署方式比較

| 方式 | 複雜度 | 成本 | 適用場景 |
|------|--------|------|----------|
| Zeabur | ⭐ | $5-15/月 | 快速上線、小團隊 |
| Docker Compose | ⭐⭐ | $5-10/月 | 自主控制 |
| Terraform | ⭐⭐⭐ | 變動 | 多環境、企業 |
