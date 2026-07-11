#!/bin/bash
# ============================================================
# Server B — 推理服务器部署脚本 (RTX 4090)
# 包含: AI Engine (FunASR + CAM++ + emotion2vec + NLU)
# 环境: Miniconda, conda 环境名 voice
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
SERVER_A_IP="${1:?用法: $0 <Server_A_IP>}"

echo "============================================"
echo "  Voice AI — Server B 部署 (推理服务器)"
echo "  项目目录: $PROJECT_DIR"
echo "  应用服务器: $SERVER_A_IP"
echo "============================================"
echo

# ----- 1. 检查 GPU -----
log "检查 GPU 环境..."
if ! command -v nvidia-smi &> /dev/null; then
    err "未检测到 nvidia-smi, 请先安装 NVIDIA 驱动"
fi
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
log "GPU 检测通过"

# ----- 2. 系统依赖 -----
log "安装系统依赖..."
sudo apt update -qq
sudo apt install -y libsndfile1 ffmpeg curl

# ----- 3. Conda 环境 -----
log "配置 Conda 环境..."
source ~/miniconda3/etc/profile.d/conda.sh
conda activate voice

# 安装 PyTorch CUDA 版本
log "安装 PyTorch..."
pip install -q torch==2.5.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124

# 安装 AI 引擎依赖
log "安装 AI 引擎依赖..."
cd "$PROJECT_DIR/ai_engine"
# 修改 requirements.txt 中的版本锁定
sed -i 's/faiss-gpu==.*/faiss-cpu/' requirements.txt
sed -i 's/funasr==.*/funasr/' requirements.txt
sed -i 's/modelscope==.*/modelscope/' requirements.txt
sed -i '/^torch/d' requirements.txt
pip install -q -r requirements.txt
log "Python 依赖安装完成"

# ----- 4. 环境变量 -----
cat > "$PROJECT_DIR/ai_engine/.env" <<EOF
MINIO_ENDPOINT=${SERVER_A_IP}:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=voice-audio
CUDA_VISIBLE_DEVICES=0
EOF
log "AI Engine .env 已生成 (MinIO → $SERVER_A_IP:9000)"

# ----- 5. 预下载模型 -----
log "预下载 AI 模型 (首次约5GB, 请耐心等待)..."
cd "$PROJECT_DIR/ai_engine"
python -c "
print('下载 FunASR Paraformer 模型...')
from funasr import AutoModel
AutoModel(model='iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch')
print('✓ ASR 模型下载完成')

print('下载 CAM++ 说话人模型...')
from modelscope.pipelines import pipeline
pipeline('speaker-verification', model='iic/speech_campplus_sv_zh-cn_16k-common')
print('✓ 说话人模型下载完成')

print('下载 emotion2vec 模型...')
pipeline('speech-emotion-recognition', model='iic/emotion2vec_base_finetuned')
print('✓ 情感模型下载完成')

print('所有模型预下载完成!')
" || warn "部分模型下载失败, 首次启动时会自动重试"

# ----- 6. systemd 服务 -----
UVICORN_PATH=$(conda run -n voice which uvicorn)
log "uvicorn 路径: $UVICORN_PATH"

cat <<SVCCONF | sudo tee /etc/systemd/system/voice-ai-engine.service > /dev/null
[Unit]
Description=Voice AI Inference Engine (GPU)
After=network.target

[Service]
Type=simple
User=$(whoami)
Group=$(whoami)
WorkingDirectory=${PROJECT_DIR}/ai_engine
Environment="CUDA_VISIBLE_DEVICES=0"
ExecStart=${UVICORN_PATH} main:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCCONF

sudo systemctl daemon-reload
sudo systemctl enable --now voice-ai-engine
log "AI Engine 服务已启动"

# ----- 7. 防火墙 -----
log "配置防火墙..."
sudo ufw allow from "$SERVER_A_IP" to any port 8001
# sudo ufw enable  # 取消注释以启用防火墙

# ----- 8. 验证 -----
sleep 3
if curl -sf http://localhost:8001/health > /dev/null; then
    log "AI Engine 健康检查通过"
else
    warn "AI Engine 启动中, 可能需要更长时间加载模型..."
fi

echo
echo "============================================"
echo -e "  ${GREEN}Server B 部署完成!${NC}"
echo "============================================"
echo "  AI Engine: http://$(hostname -I | awk '{print $1}'):8001"
echo "  API 文档:  http://$(hostname -I | awk '{print $1}'):8001/docs"
echo
echo "  验证连通性 (在 Server A 上执行):"
echo "    curl http://$(hostname -I | awk '{print $1}'):8001/health"
echo "============================================"
