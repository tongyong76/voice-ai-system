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

# Redis
if redis-cli ping > /dev/null 2>&1; then
    ok "Redis: 运行中 (PONG)"
else
    fail "Redis: 未运行"
fi

# MinIO
if curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1; then
    ok "MinIO: 运行中"
else
    fail "MinIO: 未运行"
fi

# FastAPI Backend
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    ok "FastAPI 后端: 运行中"
else
    fail "FastAPI 后端: 未运行"
fi

# Nginx
if systemctl is-active --quiet nginx 2>/dev/null; then
    ok "Nginx: 运行中"
    # 检查前端是否可访问
    HTTP_CODE=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost 2>/dev/null)
    if [ "$HTTP_CODE" = "200" ]; then
        ok "前端页面: 可访问 (HTTP $HTTP_CODE)"
    else
        warn "前端页面: HTTP $HTTP_CODE"
    fi
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
