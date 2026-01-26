#!/bin/bash
# Knowledge Platform API 測試腳本
# 用法: ./scripts/test_api.sh

BASE_URL="http://127.0.0.1:8000/api/v1"

echo "=========================================="
echo "Knowledge Platform API 測試"
echo "=========================================="
echo ""

# 顏色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 測試函數
test_api() {
    local name="$1"
    local expected="$2"
    local result="$3"

    if echo "$result" | grep -q "$expected"; then
        echo -e "${GREEN}✓${NC} $name"
        return 0
    else
        echo -e "${RED}✗${NC} $name"
        echo "  預期包含: $expected"
        echo "  實際結果: $result"
        return 1
    fi
}

# 測試 1: Health Check
echo "--- 測試 1: Health Check ---"
result=$(curl -s "$BASE_URL/health")
test_api "GET /health" '"status":"ok"' "$result"
echo ""

# 測試 2: Stats
echo "--- 測試 2: Stats ---"
result=$(curl -s "$BASE_URL/stats")
test_api "GET /stats" '"status":"ok"' "$result"
echo ""

# 測試 3: 新增文章
echo "--- 測試 3: 新增文章 ---"
result=$(curl -s -X POST "$BASE_URL/articles" \
  -H 'Content-Type: application/json' \
  -d '{"source_type":"web","source_id":"test-script-001","title":"測試文章","content":"# 測試內容"}')
test_api "POST /articles (new)" '"status":"new"\|"status":"updated"\|"status":"skipped"' "$result"
echo "  結果: $result"
echo ""

# 測試 4: 重複新增（應該 skip）
echo "--- 測試 4: 重複新增 ---"
result=$(curl -s -X POST "$BASE_URL/articles" \
  -H 'Content-Type: application/json' \
  -d '{"source_type":"web","source_id":"test-script-001","title":"測試文章","content":"# 測試內容"}')
test_api "POST /articles (skip)" '"status":"skipped"' "$result"
echo ""

# 測試 5: 更新文章
echo "--- 測試 5: 更新文章 ---"
result=$(curl -s -X POST "$BASE_URL/articles" \
  -H 'Content-Type: application/json' \
  -d '{"source_type":"web","source_id":"test-script-001","title":"測試文章-已更新","content":"# 更新後的內容"}')
test_api "POST /articles (update)" '"status":"updated"' "$result"
echo ""

# 測試 6: 批量新增
echo "--- 測試 6: 批量新增 ---"
result=$(curl -s -X POST "$BASE_URL/articles/batch" \
  -H 'Content-Type: application/json' \
  -d '{"articles":[{"source_type":"web","source_id":"batch-test-001","title":"批量1","content":"內容1"},{"source_type":"web","source_id":"batch-test-002","title":"批量2","content":"內容2"}]}')
test_api "POST /articles/batch" '"success":true' "$result"
echo ""

# 測試 7: 列出文章
echo "--- 測試 7: 列出文章 ---"
result=$(curl -s "$BASE_URL/articles?limit=5")
test_api "GET /articles" '"success":true' "$result"
echo ""

# 測試 8: OpenAPI
echo "--- 測試 8: OpenAPI 規格 ---"
result=$(curl -s "$BASE_URL/../openapi.json" | head -c 100)
test_api "GET /openapi.json" '"openapi"' "$result"
echo ""

echo "=========================================="
echo "測試完成"
echo "=========================================="
