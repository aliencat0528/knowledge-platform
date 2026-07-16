# 資料備份與還原指南

本文件說明 Knowledge Platform 的資料備份與還原機制。

---

## 快速開始

### 建立備份

```bash
# 備份到預設目錄 (./backups/)
python scripts/backup.py

# 備份到指定目錄
python scripts/backup.py --output-dir /path/to/backups
```

### 還原備份

```bash
# 從備份還原
python scripts/restore.py backups/knowledge_backup_20240126_120000.tar.gz

# 預覽模式（不實際還原）
python scripts/restore.py backups/knowledge_backup_20240126_120000.tar.gz --preview
```

---

## 備份內容

每次備份會建立一個 `.tar.gz` 壓縮檔，包含：

| 項目 | 說明 | 預設位置 |
|------|------|----------|
| SQLite 資料庫 | 所有文章、對話、設定 | `./data/knowledge.db` |
| ChromaDB | 向量索引和 embeddings | `./data/chroma/` |

### 備份檔案命名

```
knowledge_backup_YYYYMMDD_HHMMSS.tar.gz

範例：knowledge_backup_20240126_120000.tar.gz
```

---

## 備份策略建議

### 個人使用

| 類型 | 頻率 | 保留 |
|------|------|------|
| 手動備份 | 重要變更後 | 永久 |

### 團隊/生產環境

| 類型 | 頻率 | 保留 | 自動化 |
|------|------|------|--------|
| 每日備份 | 每天 00:00 | 7 天 | cron |
| 每週備份 | 每週日 | 4 週 | cron |
| 每月備份 | 每月 1 日 | 12 個月 | cron |

### Cron 設定範例

```bash
# 編輯 crontab
crontab -e

# 每日備份（每天凌晨 2 點）
0 2 * * * cd /path/to/knowledge-platform && python scripts/backup.py --output-dir /backups/daily

# 每週備份（每週日凌晨 3 點）
0 3 * * 0 cd /path/to/knowledge-platform && python scripts/backup.py --output-dir /backups/weekly
```

---

## 備份腳本參數

### backup.py

```bash
python scripts/backup.py [OPTIONS]

選項：
  -o, --output-dir DIR    輸出目錄（預設：./backups）
  --no-verify             跳過壓縮檔驗證
  --keep-temp             保留暫存檔案
  -h, --help              顯示說明
```

### restore.py

```bash
python scripts/restore.py ARCHIVE [OPTIONS]

參數：
  ARCHIVE                 備份檔案路徑 (.tar.gz)

選項：
  -p, --preview           預覽模式，不實際還原
  -f, --force             強制還原，不詢問確認
  --no-backup             跳過還原前的備份
  --no-verify             跳過還原後的驗證
  -h, --help              顯示說明
```

---

## 還原流程

### 1. 預覽備份內容

```bash
python scripts/restore.py backups/knowledge_backup_20240126_120000.tar.gz --preview
```

輸出範例：
```
Archive contents:
  - knowledge_20240126_120000.db
  - chroma_20240126_120000

Target paths:
  Database: ./data/knowledge.db
  ChromaDB: ./data/chroma

[PREVIEW MODE] No changes made.
```

### 2. 執行還原

```bash
python scripts/restore.py backups/knowledge_backup_20240126_120000.tar.gz
```

還原前會：
1. 自動備份現有資料到 `./backups/pre_restore/`
2. 詢問確認（除非使用 `--force`）
3. 還原資料
4. 驗證還原結果

### 3. 重新啟動服務

```bash
# 停止服務
# (Ctrl+C 或關閉終端機)

# 重新啟動
uvicorn packages.server.main:app --reload
```

---

## 進階用法

### 只備份資料庫

如果只需要備份 SQLite 資料庫：

```bash
cp ./data/knowledge.db ./backups/knowledge_manual_$(date +%Y%m%d).db
```

### 只備份向量庫

如果只需要備份 ChromaDB：

```bash
cp -r ./data/chroma ./backups/chroma_manual_$(date +%Y%m%d)
```

### 遠端備份（rsync）

```bash
# 同步到遠端伺服器
rsync -avz ./backups/ user@remote:/backups/knowledge-platform/
```

### 雲端備份（rclone）

```bash
# 同步到 S3
rclone sync ./backups/ s3:my-bucket/knowledge-platform/backups/

# 同步到 Google Drive
rclone sync ./backups/ gdrive:Knowledge-Platform/backups/
```

---

## 故障排除

### 備份失敗

**問題**：「Database not found」
```
解決：確認資料目錄存在
  ls -la ./data/
```

**問題**：「Permission denied」
```
解決：檢查檔案權限
  chmod -R 755 ./data/
  chmod -R 755 ./backups/
```

### 還原失敗

**問題**：「Archive not found」
```
解決：確認備份檔案路徑正確
  ls -la ./backups/
```

**問題**：還原後資料不完整
```
解決：
1. 檢查原始備份是否完整
   tar -tzf backups/knowledge_backup_xxx.tar.gz

2. 從 pre_restore 備份還原
   python scripts/restore.py backups/pre_restore/knowledge_pre_restore_xxx.tar.gz
```

### 驗證失敗

**問題**：「Database verification failed」
```
解決：
1. 檢查 SQLite 檔案完整性
   sqlite3 ./data/knowledge.db "PRAGMA integrity_check"

2. 如有損壞，從備份還原
```

---

## 安全建議

1. **加密敏感備份**
   ```bash
   gpg -c backups/knowledge_backup_xxx.tar.gz
   ```

2. **異地備份**
   - 至少保留一份備份在不同地點
   - 使用雲端儲存（加密後）

3. **定期測試還原**
   - 每月測試一次還原流程
   - 確認備份資料可用

4. **不要備份到同一磁碟**
   - 備份目錄應在不同磁碟或遠端位置

---

## Docker 環境備份

如果使用 Docker 部署，備份需要進入容器執行：

```bash
# 進入容器
docker exec -it knowledge-api bash

# 執行備份
python scripts/backup.py --output-dir /app/data/backups

# 從主機複製備份
docker cp knowledge-api:/app/data/backups ./host-backups/
```

或使用 volume 掛載：

```yaml
# docker-compose.yml
volumes:
  - ./backups:/app/data/backups
```

---

## 相關文件

- [部署指南](./DEPLOYMENT.md)
- [架構說明](./ARCHITECTURE.md)
