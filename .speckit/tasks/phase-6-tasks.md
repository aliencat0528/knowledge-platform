# Phase 6 Tasks - 部署與 DevOps

> Phase 6 實作 Zeabur 部署、CI/CD 自動化，並規劃進階擴展方案。

---

## 完成狀態總覽

| Task | 功能 | 分支 | 狀態 |
|------|------|------|------|
| 6.1 | Zeabur 專案設定 | `feature/deployment-thirteenth` | ✅ 完成 |
| 6.2 | Dockerfile 撰寫 | `feature/deployment-thirteenth` | ✅ 完成 |
| 6.3 | 環境變數管理 | `feature/deployment-thirteenth` | ⚠️ 部分（見註 1）|
| 6.4 | CI/CD Pipeline | `feature/deployment-thirteenth` | ✅ 完成 |
| 6.5 | 健康檢查與監控 | `feature/deployment-thirteenth` | ✅ 完成（見註 2）|
| 6.6 | 資料備份機制 | `feature/deployment-thirteenth` | ✅ 完成 |
| 6.7 | 部署文件 | `feature/deployment-thirteenth` | ✅ 完成 |
| 6.8 | 進階擴展規劃 | `feature/deployment-thirteenth` | ✅ 完成（見註 3）|

> **驗證日期**：2026-07-16（Docker build + 容器 health 端點實測通過、備份腳本端到端通過、ruff lint 全綠）
>
> **實作偏差註記**：
> 1. **Task 6.3 部分完成**：`.env.production.example` 已建立，但 `packages/server/config.py` 尚未加入 `environment` / `is_production` 屬性。Dockerfile 雖設定 `ENV ENVIRONMENT=production`，但 `config.py` 為 `extra="ignore"` 會忽略此變數，生產環境敏感資訊隱藏邏輯尚未實作。
> 2. **Task 6.5 位置偏差**：health 端點實作於 `packages/server/main.py`（`/api/v1/health`、`/health/ready`、`/health/live`），非計畫的獨立 `api/health.py`；功能已驗證正常。
> 3. **Task 6.8 位置偏差**：`deploy/docker-compose.yml`、`docker-compose.prod.yml`、`deploy/terraform/` 均完成；原規劃的 `docs/SCALING.md` 內容改寫至 `.speckit/tasks/phase-7-tasks.md`（Phase 7 選用方案）。

---

## 部署架構

```
                    ┌─────────────────────────────────────┐
                    │            Zeabur Platform           │
                    ├─────────────────────────────────────┤
                    │                                     │
   Internet ───────►│  ┌─────────────┐  ┌─────────────┐  │
                    │  │  Web UI     │  │  FastAPI    │  │
                    │  │  (Static)   │  │  (Python)   │  │
                    │  │  Port 80    │  │  Port 8000  │  │
                    │  └─────────────┘  └──────┬──────┘  │
                    │                          │         │
                    │                   ┌──────▼──────┐  │
                    │                   │   Volume    │  │
                    │                   │  - SQLite   │  │
                    │                   │  - ChromaDB │  │
                    │                   └─────────────┘  │
                    │                                     │
                    └─────────────────────────────────────┘
```

---

## Task 6.1: Zeabur 專案設定

### 描述
建立 Zeabur 部署設定檔，定義服務架構

### 輸出
- `zeabur.json` - Zeabur 設定檔

### 設定內容
```json
{
  "$schema": "https://zeabur.com/schemas/zeabur.json",
  "services": [
    {
      "id": "knowledge-api",
      "template": "PYTHON",
      "ports": [8000],
      "volumes": [
        {
          "id": "data",
          "dir": "/app/data"
        }
      ]
    },
    {
      "id": "knowledge-web",
      "template": "STATIC",
      "build": {
        "output": "packages/web-ui/dist"
      }
    }
  ]
}
```

### 驗證
- [ ] Zeabur 可識別設定檔
- [ ] 服務定義正確

### 相依
- 無

---

## Task 6.2: Dockerfile 撰寫

### 描述
建立後端 Dockerfile，使用多階段建置優化映像大小

### 輸出
- `packages/server/Dockerfile`
- `.dockerignore`

### Dockerfile 設計
```dockerfile
# Build stage
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY packages/server ./packages/server
COPY scripts ./scripts

# Create data directory
RUN mkdir -p /app/data

ENV PYTHONPATH=/app
ENV DATABASE_PATH=/app/data/knowledge.db
ENV CHROMA_PATH=/app/data/chroma

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "packages.server.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 驗證
```bash
docker build -t knowledge-api .
docker run -p 8000:8000 knowledge-api
curl http://localhost:8000/api/v1/health
```

### 相依
- Task 6.1

---

## Task 6.3: 環境變數管理

### 描述
建立生產環境變數設定與安全管理機制

### 輸出
- `.env.production.example`
- 更新 `packages/server/config.py`

### 環境變數分類

| 類別 | 變數 | Zeabur 設定方式 |
|------|------|----------------|
| **必要** | `OPENAI_API_KEY` | Secret |
| **選用** | `ANTHROPIC_API_KEY` | Secret |
| **選用** | `NOTION_API_KEY` | Secret |
| **系統** | `DATABASE_PATH` | 固定值 |
| **系統** | `CHROMA_PATH` | 固定值 |
| **系統** | `DEBUG` | `false` |

### 設定更新
```python
# config.py 新增
class Settings(BaseSettings):
    # 生產環境標記
    environment: str = "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"
```

### 驗證
- [ ] 生產環境不顯示敏感資訊
- [ ] API Keys 正確載入

### 相依
- Task 6.1

---

## Task 6.4: CI/CD Pipeline

### 描述
建立 GitHub Actions 自動建置與部署流程

### 輸出
- `.github/workflows/build.yml`
- `.github/workflows/deploy.yml`

### 工作流程設計

```yaml
# build.yml - PR 時觸發
name: Build & Test

on:
  pull_request:
    branches: [main]

jobs:
  build-api:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r packages/server/requirements.txt
      - name: Run tests
        run: pytest tests/

  build-web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: '18'
      - name: Install & Build
        run: |
          cd packages/web-ui
          npm ci
          npm run build
```

```yaml
# deploy.yml - Merge 到 main 時觸發
name: Deploy to Zeabur

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Zeabur
        uses: zeabur/action-deploy@v0.1.0
        with:
          project: ${{ secrets.ZEABUR_PROJECT_ID }}
          token: ${{ secrets.ZEABUR_TOKEN }}
```

### 驗證
- [ ] PR 時自動執行測試
- [ ] Merge 後自動部署

### 相依
- Task 6.2

---

## Task 6.5: 健康檢查與監控

### 描述
強化健康檢查端點，支援 Zeabur 健康偵測

### 輸出
- 更新 `packages/server/main.py`
- 新增 `packages/server/api/health.py`

### 健康檢查設計
```python
# api/health.py
from fastapi import APIRouter
from ..storage.database import get_db

router = APIRouter(tags=["Health"])

@router.get("/health")
async def health_check():
    """基本健康檢查"""
    return {"status": "ok", "version": "0.1.0"}

@router.get("/health/ready")
async def readiness_check():
    """就緒檢查 - 包含資料庫連線"""
    try:
        db = await get_db()
        await db.fetchone("SELECT 1")
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        return {"status": "not_ready", "error": str(e)}

@router.get("/health/live")
async def liveness_check():
    """存活檢查"""
    return {"status": "alive"}
```

### Zeabur 健康檢查設定
```json
{
  "healthCheck": {
    "path": "/api/v1/health/ready",
    "interval": 30
  }
}
```

### 驗證
- [ ] `/health` 回傳正常
- [ ] `/health/ready` 檢查資料庫
- [ ] Zeabur 正確偵測服務狀態

### 相依
- Task 6.2

---

## Task 6.6: 資料備份機制

### 描述
建立資料備份與還原腳本

### 輸出
- `scripts/backup.py`
- `scripts/restore.py`
- `docs/BACKUP.md`

### 備份腳本設計
```python
# scripts/backup.py
import shutil
import datetime
from pathlib import Path

def backup_data(data_dir: str, backup_dir: str):
    """備份 SQLite 和 ChromaDB 資料"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = Path(backup_dir) / f"backup_{timestamp}"
    backup_path.mkdir(parents=True, exist_ok=True)

    # 備份 SQLite
    db_path = Path(data_dir) / "knowledge.db"
    if db_path.exists():
        shutil.copy(db_path, backup_path / "knowledge.db")

    # 備份 ChromaDB
    chroma_path = Path(data_dir) / "chroma"
    if chroma_path.exists():
        shutil.copytree(chroma_path, backup_path / "chroma")

    return backup_path
```

### 備份策略
| 類型 | 頻率 | 保留 |
|------|------|------|
| 每日備份 | 每天 00:00 | 7 天 |
| 每週備份 | 每週日 | 4 週 |
| 手動備份 | 依需求 | 永久 |

### 驗證
- [ ] 備份腳本可執行
- [ ] 還原腳本可執行
- [ ] 資料完整性驗證

### 相依
- Task 6.3

---

## Task 6.7: 部署文件

### 描述
撰寫完整部署指南

### 輸出
- `docs/DEPLOYMENT.md`
- 更新 `README.md`

### 文件內容
```markdown
# 部署指南

## 快速部署（Zeabur）

1. Fork 此專案
2. 登入 Zeabur 並建立專案
3. 連結 GitHub Repository
4. 設定環境變數
5. 部署完成

## 環境變數設定

| 變數 | 必要 | 說明 |
|------|------|------|
| OPENAI_API_KEY | 是 | OpenAI API 金鑰 |
| ... | ... | ... |

## 本地開發

...

## 進階部署

- Docker Compose 部署
- VPS 部署
- Terraform 部署
```

### 驗證
- [ ] 文件完整
- [ ] 步驟可執行

### 相依
- Task 6.1 ~ 6.6

---

## Task 6.8: 進階擴展規劃

### 描述
規劃進階部署方案，支援未來擴展需求

### 輸出
- `deploy/docker-compose.yml`
- `deploy/docker-compose.prod.yml`
- `deploy/terraform/` (規劃文件)
- `docs/SCALING.md`

### Docker Compose（自架方案）
```yaml
# deploy/docker-compose.yml
version: '3.8'

services:
  api:
    build:
      context: ..
      dockerfile: packages/server/Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - api_data:/app/data
    environment:
      - DATABASE_PATH=/app/data/knowledge.db
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    restart: unless-stopped

  web:
    build:
      context: ../packages/web-ui
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - api
    restart: unless-stopped

volumes:
  api_data:
```

### Terraform 規劃（雲端方案）
```hcl
# deploy/terraform/main.tf（規劃）
#
# 支援的雲端平台：
# - DigitalOcean Droplet
# - AWS EC2 + RDS
# - GCP Compute Engine
#
# 待 Phase 7 實作
```

### 擴展路線圖
```
目前（Phase 6）：
└── Zeabur 單機部署

Phase 7（選項）：
├── A. Docker Compose + VPS（自架）
├── B. Terraform + Cloud（AWS/GCP）
└── C. Kubernetes（大規模）

擴展觸發條件：
├── 資料量 > 10GB → 考慮 PostgreSQL
├── 用戶數 > 10 → 考慮負載均衡
└── 多區域需求 → 考慮 K8s
```

### 驗證
- [ ] Docker Compose 可本地運行
- [ ] Terraform 文件完整
- [ ] 擴展路線清晰

### 相依
- Task 6.7

---

# Phase 6 完成條件

```
✅ Zeabur 設定檔完成（實際部署待雲端執行）
✅ CI/CD workflow 完成（實際觸發待 push main 驗證）
✅ 健康檢查正常（容器實測通過）
✅ 備份機制可用（端到端實測通過）
✅ 部署文件完整
✅ 進階方案規劃完成（Phase 7）
⚠️ 生產環境變數隱藏邏輯（config.py）待補 — 見狀態表註 1
```

---

# 預估時間

| Task | 時間 |
|------|------|
| 6.1 Zeabur 專案設定 | 0.5 hr |
| 6.2 Dockerfile 撰寫 | 1 hr |
| 6.3 環境變數管理 | 0.5 hr |
| 6.4 CI/CD Pipeline | 1.5 hr |
| 6.5 健康檢查與監控 | 1 hr |
| 6.6 資料備份機制 | 1 hr |
| 6.7 部署文件 | 1 hr |
| 6.8 進階擴展規劃 | 1.5 hr |
| **Phase 6 總計** | **~8 小時** |

---

# 進階擴展方案比較

| 方案 | 適用情境 | 複雜度 | 成本 |
|------|----------|--------|------|
| **Zeabur** | 快速上線、小團隊 | ⭐ | $5-15/月 |
| **Docker + VPS** | 自主控制、固定成本 | ⭐⭐ | $5-10/月 |
| **Terraform + Cloud** | 多環境、自動化 | ⭐⭐⭐ | 變動 |
| **Kubernetes** | 大規模、高可用 | ⭐⭐⭐⭐⭐ | $50+/月 |

---

# 未來 Phase 7 規劃（選用）

根據實際需求選擇：

| 選項 | 內容 |
|------|------|
| **7A** | Docker Compose 完整實作 + 自動備份 |
| **7B** | Terraform AWS/GCP 部署 |
| **7C** | PostgreSQL 遷移 + 進階查詢 |
| **7D** | 監控系統（Prometheus + Grafana）|
