#!/bin/bash
# ============================================================
# Server A — 应用服务器部署脚本 (无GPU)
# 包含: Nginx + FastAPI + MySQL + Redis + MinIO
# ============================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVER_B_IP="${1:?用法: $0 <Server_B_IP>}"
CURRENT_USER="$(whoami)"

echo "============================================"
echo "  Voice AI — Server A 部署"
echo "  项目目录: $PROJECT_DIR"
echo "  推理服务器: $SERVER_B_IP:8001"
echo "  运行用户: $CURRENT_USER"
echo "============================================"
echo

# ----- 1. 系统依赖 -----
log "安装系统依赖..."
sudo apt update -qq
sudo apt install -y python3.11 python3.11-venv python3-pip \
    nginx mysql-server redis-server ffmpeg curl wget

# ----- 2. MySQL -----
log "配置 MySQL..."
sudo systemctl start mysql
sudo systemctl enable mysql
sudo mysql -e "
CREATE DATABASE IF NOT EXISTS voice_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'voice_user'@'localhost' IDENTIFIED BY 'voice_pass';
CREATE USER IF NOT EXISTS 'voice_user'@'%' IDENTIFIED BY 'voice_pass';
GRANT ALL ON voice_ai.* TO 'voice_user'@'localhost';
GRANT ALL ON voice_ai.* TO 'voice_user'@'%';
FLUSH PRIVILEGES;
"
if [ -f "$PROJECT_DIR/scripts/init-db.sql" ]; then
    mysql -u voice_user -pvoice_pass voice_ai < "$PROJECT_DIR/scripts/init-db.sql"
    log "数据库表已初始化"
else
    warn "未找到 init-db.sql, 跳过建表"
fi

# ----- 3. Redis -----
log "启动 Redis..."
sudo systemctl enable redis-server
sudo systemctl start redis-server
redis-cli ping > /dev/null && log "Redis 运行正常" || err "Redis 启动失败"

# ----- 4. MinIO -----
log "安装 MinIO..."
# 停掉 Snap 版 MinIO (如有)
sudo snap stop minio 2>/dev/null || true
sudo snap disable minio 2>/dev/null || true

if ! command -v minio &> /dev/null; then
    wget -q https://dl.min.io/server/minio/release/linux-amd64/minio -O /tmp/minio
    sudo mv /tmp/minio /usr/local/bin/
    sudo chmod +x /usr/local/bin/minio
fi

sudo mkdir -p /data/minio

sudo tee /etc/systemd/system/minio.service > /dev/null <<'EOF'
[Unit]
Description=MinIO Object Storage
After=network.target

[Service]
Type=simple
User=root
Environment="MINIO_ROOT_USER=minioadmin"
Environment="MINIO_ROOT_PASSWORD=minioadmin"
ExecStart=/usr/local/bin/minio server /data/minio --console-address ":9001"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now minio
sleep 2
curl -sf http://localhost:9000/minio/health/live > /dev/null && log "MinIO 运行正常" || err "MinIO 启动失败"

# ----- 5. Python 虚拟环境 & 后端 -----
log "配置后端 Python 环境..."
cd "$PROJECT_DIR"
if [ ! -d "venv-server" ]; then
    python3.11 -m venv venv-server
fi
source venv-server/bin/activate
cd server && pip install -q -r requirements.txt && cd ..

# 修复 passlib + bcrypt 兼容问题
pip install -q bcrypt==4.0.1

# 写入 .env (SERVER_B_IP 通过变量展开写入实际值)
cat > "$PROJECT_DIR/server/.env" <<EOF
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=voice_user
MYSQL_PASSWORD=voice_pass
MYSQL_DATABASE=voice_ai
REDIS_HOST=localhost
REDIS_PORT=6379
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
AI_ENGINE_URL=http://${SERVER_B_IP}:8001
SECRET_KEY=$(openssl rand -hex 32)
EOF
log "后端 .env 已生成"

# ----- 6. 前端构建 -----
log "构建前端..."
cd "$PROJECT_DIR/web"
if [ ! -d "node_modules" ]; then
    npm install
fi
# 跳过 vue-tsc 类型检查 (TypeScript 版本兼容问题), 直接 vite 构建
npx vite build
log "前端构建完成 → web/dist/"

# ----- 7. Nginx -----
log "配置 Nginx..."
# 停掉 Apache (如占用 80 端口)
sudo systemctl stop apache2 2>/dev/null || true

# 使用 cat + sudo tee 写入, 避免 heredoc 变量展开问题
cat <<NGINXCONF | sudo tee /etc/nginx/sites-available/voice-ai > /dev/null
server {
    listen 80;
    server_name _;

    root ${PROJECT_DIR}/web/dist;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        client_max_body_size 100M;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_read_timeout 86400;
    }
}
NGINXCONF

sudo ln -sf /etc/nginx/sites-available/voice-ai /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl start nginx
sudo systemctl enable nginx
log "Nginx 配置完成"

# ----- 8. 后端 systemd 服务 -----
log "配置后端 Systemd 服务..."
cat <<SVCCONF | sudo tee /etc/systemd/system/voice-server.service > /dev/null
[Unit]
Description=Voice AI FastAPI Server
After=network.target mysql.service redis-server.service

[Service]
Type=simple
User=${CURRENT_USER}
Group=${CURRENT_USER}
WorkingDirectory=${PROJECT_DIR}/server
ExecStart=${PROJECT_DIR}/venv-server/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCCONF

sudo systemctl daemon-reload
sudo systemctl enable --now voice-server

# ----- 9. 防火墙 -----
log "配置防火墙..."
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow from "$SERVER_B_IP" to any port 9000
# sudo ufw enable  # 取消注释以启用防火墙

echo
echo "============================================"
echo -e "  ${GREEN}Server A 部署完成!${NC}"
echo "============================================"
echo "  前端:    http://$(hostname -I | awk '{print $1}')"
echo "  API:     http://$(hostname -I | awk '{print $1}'):8000/docs"
echo "  MinIO:   http://$(hostname -I | awk '{print $1}'):9001"
echo "  默认账号: admin / admin123"
echo
echo "  验证: curl http://localhost:8000/health"
echo "  下一步: 在 Server B ($SERVER_B_IP) 运行 deploy-server-b.sh"
echo "============================================"
