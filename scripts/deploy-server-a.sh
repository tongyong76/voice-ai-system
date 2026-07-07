#!/bin/bash
# ============================================================
# Server A — 应用服务器部署脚本 (无GPU)
# 包含: Nginx + FastAPI + MySQL + Redis Stack + MinIO
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

echo "============================================"
echo "  Voice AI — Server A 部署"
echo "  项目目录: $PROJECT_DIR"
echo "  推理服务器: $SERVER_B_IP:8001"
echo "============================================"
echo

# ----- 1. 系统依赖 -----
log "安装系统依赖..."
sudo apt update -qq
sudo apt install -y python3.11 python3.11-venv python3-pip \
    nginx mysql-server ffmpeg curl wget gnupg2

# ----- 2. MySQL -----
log "配置 MySQL..."
sudo systemctl start mysql
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

# ----- 3. Redis Stack Server (含 RediSearch 全文检索) -----
log "安装 Redis Stack Server..."
if ! command -v redis-stack-server &> /dev/null; then
    curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
    sudo apt update -qq
    sudo apt install -y redis-stack-server
fi

# 配置 Redis Stack (启用 RediSearch 模块)
sudo tee /etc/redis-stack.conf > /dev/null <<'EOF'
bind 127.0.0.1
port 6379
daemonize yes
loadmodule /opt/redis-stack/lib/redisearch.so
loadmodule /opt/redis-stack/lib/rejson.so
loadmodule /opt/redis-stack/lib/redistimeseries.so
loadmodule /opt/redis-stack/lib/redisbloom.so
EOF

# 启动
sudo systemctl enable redis-stack-server
sudo systemctl start redis-stack-server
sleep 2
redis-stack-server --version > /dev/null 2>&1 || redis-cli ping > /dev/null 2>&1
if redis-cli ping > /dev/null 2>&1; then
    log "Redis Stack Server 运行正常 (含 RediSearch)"
    # 验证 RediSearch 模块
    redis-cli MODULE LIST | grep -q search && log "RediSearch 模块已加载" || warn "RediSearch 模块未加载"
else
    err "Redis Stack Server 启动失败"
fi

# ----- 4. MinIO -----
log "安装 MinIO..."
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
curl -sf http://localhost:9000/minio/health > /dev/null && log "MinIO 运行正常" || err "MinIO 启动失败"

# ----- 5. Python 虚拟环境 & 后端 -----
log "配置后端 Python 环境..."
cd "$PROJECT_DIR"
if [ ! -d "venv-server" ]; then
    python3.11 -m venv venv-server
fi
source venv-server/bin/activate
cd server && pip install -q -r requirements.txt && cd ..

# 写入 .env
cat > server/.env <<EOF
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
npm run build
log "前端构建完成 → web/dist/"

# ----- 7. Nginx -----
log "配置 Nginx..."
sudo tee /etc/nginx/sites-available/voice-ai > /dev/null <<EOF
server {
    listen 80;
    server_name _;

    root $PROJECT_DIR/web/dist;
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
EOF

sudo ln -sf /etc/nginx/sites-available/voice-ai /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# ----- 8. 后端 systemd 服务 -----
sudo tee /etc/systemd/system/voice-server.service > /dev/null <<EOF
[Unit]
Description=Voice AI FastAPI Server
After=network.target mysql.service redis-server.service

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=$PROJECT_DIR/server
Environment="PATH=$PROJECT_DIR/venv-server/bin"
ExecStart=$PROJECT_DIR/venv-server/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

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
echo "  下一步: 在 Server B ($SERVER_B_IP) 运行 deploy-server-b.sh"
echo "============================================"
