# 智能语音采集与AI识别系统

基于 ESP32 + FunASR + 说话人识别 + 情感分析的智能语音采集与分析系统。

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│              Server A — 应用服务器 (无GPU)                │
│                                                         │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐             │
│  │  Nginx   │  │  FastAPI   │  │  Vue3    │             │
│  │  :80     │  │  :8000     │  │  构建产物 │             │
│  └──────────┘  └───────────┘  └──────────┘             │
│       │              │                                   │
│       ▼              ▼                                   │
│  ┌──────────┐  ┌───────────────────┐  ┌──────────┐│
│  │  MySQL   │  │   Redis Stack     │  │  MinIO   ││
│  │  :3306   │  │  :6379            │  │ :9000    ││
│  └──────────┘  │  (含RediSearch)   │  └──────────┘│
│                └───────────────────┘               │
│                     │                                   │
│                     │ Redis队列                          │
│                     ▼                                   │
│              ┌─────────────┐                            │
│              │  Worker 消费  │──── HTTP 调用 ────┐       │
│              └─────────────┘                    │       │
└─────────────────────────────────────────────────┼───────┘
                                                  │
                                          http://Server_B_IP:8001
                                                  │
┌─────────────────────────────────────────────────┼───────┐
│              Server B — 推理服务器 (RTX 4090)     │       │
│                                                  ▼      │
│  ┌──────────────────────────────────────────────────┐   │
│  │              AI Engine (FastAPI :8001)           │   │
│  │  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────────┐ │   │
│  │  │FunASR    │ │ CAM++    │ │emotion │ │  NLU   │ │   │
│  │  │Paraformer│ │ 说话人    │ │2vec    │ │ 关键词  │ │   │
│  │  └──────────┘ └──────────┘ └────────┘ └────────┘ │   │
│  └──────────────────────────────────────────────────┘   │
│           │                                             │
│           │ 从 Server A 的 MinIO 下载音频                 │
│           ▼                                             │
│     Server_A_IP:9000 (MinIO)                            │
└─────────────────────────────────────────────────────────┘
                                                  ▲
┌─────────────────────────────────────────────────┼───────┐
│              XIAO ESP32S3 + ReSpeaker Lite (200台)      │
│   麦克风采集  →  Opus编码  →  Wi-Fi HTTP 上传              │
│   目标: http://Server_A_IP:8000/api/audio/upload         │
└─────────────────────────────────────────────────────────┘
```

## 技术栈

| 层级     | 技术                                       |
| -------- | ------------------------------------------ |
| 边缘端   | ESP-IDF (C), Opus 编码, HTTP 上传          |
| 后端服务 | Python 3.11, FastAPI, SQLAlchemy, Redis    |
| AI 推理  | PyTorch, FunASR, CAM++, emotion2vec, FAISS |
| 数据库   | MySQL 8.0, Redis Stack (含 RediSearch), MinIO |
| 前端     | Vue 3, TypeScript, Element Plus, ECharts   |
| 部署     | 双服务器裸机部署, Nginx, Systemd           |

## 快速开始

### 1. 服务器规划

| 服务器       | 用途                            | 最低配置                         |
| ------------ | ------------------------------- | -------------------------------- |
| **Server A** | 应用服务器 (前端 + 后端 + 存储) | 8核 CPU, 32GB RAM, 1TB SSD       |
| **Server B** | 推理服务器 (AI引擎)             | 8核 CPU, 32GB RAM, RTX 4090 24GB |

两台服务器需内网互通。

### 2. 部署 Server A (应用服务器)

```bash
# 登录 Server A
cd /home/guwenjun/code/voice-ai-system

# 一键部署 (参数为 Server B 的 IP)
chmod +x scripts/deploy-server-a.sh
./scripts/deploy-server-a.sh 192.168.1.100
```

该脚本自动安装并配置:

- MySQL 8.0 + 建表
- Redis Stack Server (含 RediSearch 全文检索模块)
- MinIO (对象存储)
- FastAPI 后端 (Uvicorn + Systemd)
- Vue3 前端构建 + Nginx 反向代理

### 3. 部署 Server B (推理服务器)

```bash
# 登录 Server B
cd /home/guwenjun/code/voice-ai-system

# 一键部署 (参数为 Server A 的 IP)
chmod +x scripts/deploy-server-b.sh
./scripts/deploy-server-b.sh 192.168.1.50
```

该脚本自动安装并配置:

- CUDA 环境检查
- Python 3.11 + 虚拟环境
- AI 模型预下载 (~5GB)
- AI Engine Systemd 服务

### 4. 验证部署

```bash
# 在 Server A 上执行
chmod +x scripts/check-status.sh
./scripts/check-status.sh 192.168.1.100
```

预期输出:

```
📦 Server A (本机) 服务:
  ✓ MySQL: 运行中
  ✓ Redis Stack: 运行中 (PONG)
  ✓ MinIO: 运行中
  ✓ RediSearch 模块: 已加载
  ✓ FastAPI 后端: 运行中
  ✓ Nginx: 运行中

🧠 Server B (192.168.1.100) 服务:
  ✓ AI Engine: 运行中
```

### 5. 访问系统

| 服务         | 地址                           |
| ------------ | ------------------------------ |
| 前端         | `http://SERVER_A_IP`           |
| API 文档     | `http://SERVER_A_IP:8000/docs` |
| MinIO 控制台 | `http://SERVER_A_IP:9001`      |
| AI 引擎文档  | `http://SERVER_B_IP:8001/docs` |

### 6. 默认账号

- 前端: `admin` / `admin123`
- MinIO: `minioadmin` / `minioadmin`

## 开发指南

### 后端开发 (Server A)

```bash
cd server
python3.11 -m venv venv-server
source venv-server/bin/activate
pip install -r requirements.txt

# 创建 .env (参考 .env.example)
cp ../.env.example .env
# 编辑 .env, 设置 AI_ENGINE_URL=http://SERVER_B_IP:8001

uvicorn app.main:app --reload --port 8000
```

### AI 引擎开发 (Server B)

```bash
cd ai_engine
python3.11 -m venv venv-ai
source venv-ai/bin/activate
pip install -r requirements.txt

# 创建 .env
echo "MINIO_ENDPOINT=SERVER_A_IP:9000" > .env
echo "MINIO_ACCESS_KEY=minioadmin" >> .env
echo "MINIO_SECRET_KEY=minioadmin" >> .env
echo "MINIO_BUCKET=voice-audio" >> .env
echo "CUDA_VISIBLE_DEVICES=0" >> .env

uvicorn main:app --reload --port 8001
```

### 前端开发

```bash
cd web
npm install
npm run dev
# 访问 http://localhost:5173
```

## API 文档

启动服务后访问:

- 后端 API: `http://SERVER_A_IP:8000/docs`
- AI 引擎: `http://SERVER_B_IP:8001/docs`

## 目录结构

```
voice-ai-system/
├── server/                     # 后端服务
│   ├── app/
│   │   ├── api/               # API 路由 (10个模块)
│   │   ├── models/            # 数据库模型
│   │   ├── services/          # 业务逻辑 (Worker)
│   │   └── core/              # 核心配置
│   ├── requirements.txt
│   └── Dockerfile
├── ai_engine/                  # AI 推理引擎
│   ├── pipeline/              # 推理流水线
│   │   ├── asr_engine.py      # FunASR 语音识别
│   │   ├── speaker_engine.py  # CAM++ 说话人识别
│   │   ├── emotion_engine.py  # emotion2vec 情感分析
│   │   └── nlu_engine.py      # NLU 关键词/意图
│   ├── speaker_db/            # FAISS 说话人检索
│   ├── requirements.txt
│   └── Dockerfile
├── web/                        # Vue3 前端
│   ├── src/
│   │   ├── views/             # 页面 (10个)
│   │   ├── api/               # API 调用
│   │   └── components/        # 公共组件
│   └── package.json
├── esp32-firmware/             # ESP32 固件
├── scripts/
│   ├── deploy-server-a.sh     # Server A 部署脚本 ✨
│   ├── deploy-server-b.sh     # Server B 部署脚本 ✨
│   ├── check-status.sh        # 服务状态检查 ✨
│   ├── init-db.sql            # 数据库初始化
│   ├── start.sh               # 旧Docker启动脚本
│   └── stop.sh                # 旧Docker停止脚本
├── docker-compose.yml          # (已弃用, 改用双服务器部署)
├── docs/project-plan.md        # 详细项目文档
└── README.md
```

## 性能参数

| 参数     | 值                                |
| -------- | --------------------------------- |
| GPU      | RTX 4090 24GB                     |
| ASR      | FunASR Paraformer-zh, 实时率 1:50 |
| 说话人库 | 10万规模, FAISS 检索 <1ms         |
| 情感分析 | emotion2vec                       |
| 并发设备 | 200 台                            |
| 日均音频 | 1,600 小时 (~25GB)                |

## 端口清单

| 服务          | 端口 | 服务器   | 说明                        |
| ------------- | ---- | -------- | --------------------------- |
| Nginx         | 80   | Server A | 前端 + API 反向代理         |
| FastAPI       | 8000 | Server A | 后端 API (仅 Nginx 代理)    |
| MySQL         | 3306 | Server A | 数据库 (仅本机)             |
| Redis Stack   | 6379 | Server A | 缓存/队列/全文检索 (仅本机) |
| MinIO         | 9000 | Server A | 对象存储 (内网)             |
| MinIO Console | 9001 | Server A | 管理控制台                  |
| AI Engine     | 8001 | Server B | 推理服务 (仅 Server A 调用) |

## License

MIT
