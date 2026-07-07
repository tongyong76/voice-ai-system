#!/bin/bash
# ============================================================
# 服务状态检查脚本
# 用法: check-status.sh [server_b_ip]
# ============================================================

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok() { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
warn() { echo -e "  ${YELLOW}!${NC} $1"; }

SERVER_B_IP="${1:-}"

echo "============================================"
echo "  Voice AI System — 服务状态检查"
echo "============================================"

echo
echo "📦 Server A (本机) 服务:"
echo "--------------------------------------------"

# MySQL
if systemctl is-active --quiet mysql 2>/dev/null; then
    ok "MySQL: 运行中"
else
    fail "MySQL: 未运行"
fi

# Redis Stack (含 RediSearch)
if redis-cli ping > /dev/null 2>&1; then
    ok "Redis Stack: 运行中 (PONG)"
    if redis-cli MODULE LIST 2>/dev/null | grep -q search; then
        ok "RediSearch 模块: 已加载"
    else
        warn "RediSearch 模块: 未加载"
    fi
else
    fail "Redis Stack: 未运行"
fi

# MinIO
if curl -sf http://localhost:9000/minio/health > /dev/null 2>&1; then
    ok "MinIO: 运行中"
else
    fail "MinIO: 未运行"
fi

# Elasticsearch
if curl -sf http://localhost:9200/_cluster/health > /dev/null 2>&1; then
    ES_STATUS=$(curl -sf http://localhost:9200/_cluster/health | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null)
    if [ "$ES_STATUS" = "green" ] || [ "$ES_STATUS" = "yellow" ]; then
        ok "Elasticsearch: 运行中 ($ES_STATUS)"
    else
        warn "Elasticsearch: 状态异常 ($ES_STATUS)"
    fi
else
    fail "Elasticsearch: 未运行"
fi

# FastAPI Backend
# (Elasticsearch 已替换为 Redis Stack RediSearch，无需单独检查)
if curl -sf http://localhost:8000/docs > /dev/null 2>&1; then
    ok "FastAPI 后端: 运行中"
else
    fail "FastAPI 后端: 未运行"
fi

# Nginx
if systemctl is-active --quiet nginx 2>/dev/null; then
    ok "Nginx: 运行中"
else
    fail "Nginx: 未运行"
fi

if [ -n "$SERVER_B_IP" ]; then
    echo
    echo "🧠 Server B ($SERVER_B_IP) 服务:"
    echo "--------------------------------------------"

    if curl -sf --connect-timeout 3 "http://$SERVER_B_IP:8001/health" > /dev/null 2>&1; then
        ok "AI Engine: 运行中"
    else
        fail "AI Engine: 无法连接 (http://$SERVER_B_IP:8001)"
    fi
else
    echo
    warn "未指定 Server B IP, 跳过推理服务检查"
    echo "  用法: $0 <Server_B_IP>"
fi

echo
echo "============================================"
echo "  访问地址:"
echo "  前端:    http://$(hostname -I | awk '{print $1}')"
echo "  API文档: http://$(hostname -I | awk '{print $1}'):8000/docs"
echo "  MinIO:   http://$(hostname -I | awk '{print $1}'):9001"
echo "============================================"
