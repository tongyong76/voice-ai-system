# 智能语音采集与AI识别系统

基于 ESP32 + FunASR + 说话人识别 + 情感分析的智能语音采集与分析系统。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Vue3 前端管理平台                            │
│   实时监控  │  任务管理  │  设备管理  │  数据检索  │  看板统计       │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FastAPI 中心服务 (CPU)                           │
│  设备管理  │  任务调度  │  文件接收  │  结果查询  │  WebSocket推送   │
└─────────────────────────────────────────────────────────────────────┘
     │              │              │               │
     ▼              ▼              ▼               ▼
┌─────────┐  ┌───────────┐  ┌──────────┐  ┌────────────────┐
│  MySQL   │  │   Redis   │  │  MinIO   │  │ Elasticsearch  │
│ 业务数据  │  │  缓存/队列 │  │ 音频存储  │  │  全文检索       │
└─────────┘  └───────────┘  └──────────┘  └────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    GPU 推理服务器 (RTX 4090 24G)                      │
│  ┌──────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────────┐  │
│  │ ASR 引擎  │  │ 说话人识别    │  │  情感分析   │  │   NLU 提取   │  │
│  │FunASR    │  │ CAM++        │  │ emotion2vec│  │  关键词/意图  │  │
│  └──────────┘  └──────────────┘  └────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              ▲
┌─────────────────────────────────────────────────────────────────────┐
│              XIAO ESP32S3 + ReSpeaker Lite (200台)                   │
│   麦克风采集  →  Opus编码  →  Wi-Fi HTTP 定时上传                      │
└─────────────────────────────────────────────────────────────────────┘
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 边缘端 | ESP-IDF (C), Opus 编码, HTTP 上传 |
| 后端服务 | Python 3.11, FastAPI, SQLAlchemy, Redis |
| AI 推理 | PyTorch, FunASR, CAM++, emotion2vec, FAISS |
| 数据库 | MySQL 8.0, Redis 7, Elasticsearch 8, MinIO |
| 前端 | Vue 3, TypeScript, Element Plus, ECharts |
| 部署 | Docker Compose, Nginx |

## 快速开始

### 1. 环境要求

- Docker & Docker Compose
- NVIDIA GPU (RTX 4090 或更高)
- NVIDIA Container Toolkit

### 2. 启动服务

```bash
# 克隆项目
cd voice-ai-system

# 复制环境变量
cp .env.example .env

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 3. 访问系统

- 前端: http://localhost:3000
- 后端 API: http://localhost:8000/docs
- AI 引擎: http://localhost:8001/docs
- MinIO 控制台: http://localhost:9001

### 4. 默认账号

- 前端: admin / admin123
- MinIO: minioadmin / minioadmin

## 开发指南

### 后端开发

```bash
cd server
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### AI 引擎开发

```bash
cd ai_engine
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

### 前端开发

```bash
cd web
npm install
npm run dev
```

## API 文档

启动服务后访问:
- 后端 API: http://localhost:8000/docs
- AI 引擎: http://localhost:8001/docs

## 目录结构

```
voice-ai-system/
├── server/                 # 后端服务
│   ├── app/
│   │   ├── api/           # API 路由
│   │   ├── models/        # 数据库模型
│   │   ├── services/      # 业务逻辑
│   │   └── core/          # 核心配置
│   └── requirements.txt
├── ai_engine/             # AI 推理引擎
│   ├── pipeline/          # 推理流水线
│   ├── speaker_db/        # 说话人数据库
│   └── requirements.txt
├── web/                   # Vue3 前端
│   ├── src/
│   │   ├── views/         # 页面组件
│   │   ├── api/           # API 调用
│   │   └── components/    # 公共组件
│   └── package.json
├── esp32-firmware/        # ESP32 固件
├── docker-compose.yml     # Docker 编排
└── README.md
```

## 性能参数

| 参数 | 值 |
|------|-----|
| GPU | RTX 4090 24GB |
| ASR | FunASR Paraformer-zh |
| 说话人库 | 10万规模 |
| 并发设备 | 200 台 |
| 日均音频 | 1,600 小时 |

## License

MIT
