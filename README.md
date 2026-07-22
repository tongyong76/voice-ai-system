# 智能语音采集与AI识别系统

基于 ESP32 + FunASR + 说话人识别 + 情感分析 + RAG 知识库问答的智能语音采集与分析系统。

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│        Server A — 192.168.31.45 (应用服务器, 无GPU)       │
│                                                         │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐              │
│  │  Nginx   │  │  FastAPI  │  │  Vue3    │              │
│  │  :80     │  │  :8000    │  │  构建产物 │              │
│  └──────────┘  └───────────┘  └──────────┘              │
│       │              │                                  │
│       ▼              ▼                                  │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐              │
│  │  MySQL   │  │   Redis   │  │  MinIO   │              │
│  │  :3306   │  │   :6379   │  │ :9000    │              │
│  └──────────┘  └───────────┘  └──────────┘              │
│                     │                                   │
│                     │ Redis队列                          │
│                     ▼                                   │
│              ┌─────────────┐                            │
│              │  Worker 消费 │ ──── HTTP 调用 ────┐       │
│              └─────────────┘                    │       │
└─────────────────────────────────────────────────┼───────┘
                                                  │
                                     http://192.168.31.4:8001
                                                  │
┌─────────────────────────────────────────────────┼───────┐
│          Server B — 192.168.31.4 (推理服务器, RTX 4090)   │
│                                                  ▼      │
│  ┌──────────────────────────────────────────────────┐   │
│  │              AI Engine (FastAPI :8001)           │   │
│  │  ┌──────────┐ ┌────────────────────────────────┐ │   │
│  │  │text2vec  │ │ RAG Pipeline (检索+生成)        │ │   │
│  │  │文本向量化 │ │ FAISS文本索引 + llama.cpp LLM   │ │   │
│  │  └──────────┘ └────────────────────────────────┘ │   │
│  │  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────────┐ │   │
│  │  │FunASR    │ │ CAM++    │ │emotion │ │  NLU   │ │   │
│  │  │Paraformer│ │ 说话人    │ │2vec    │ │ 关键词  │ │   │
│  │  └──────────┘ └──────────┘ └────────┘ └────────┘ │   │
│  └──────────────────────────────────────────────────┘   │
│           │                          ▲                   │
│           │ 从 Server A 的 MinIO     │ OpenAI 兼容 API   │
│           │ 下载音频                 │                   │
│           ▼                          │                   │
│     192.168.31.45:9000 (MinIO)  ┌────┴─────────────┐    │
│                                 │ llama.cpp :8080  │    │
│                                 │ Qwen2.5-7B Q4KM  │    │
│                                 └──────────────────┘    │
└─────────────────────────────────────────────────────────┘
                                                  ▲
┌─────────────────────────────────────────────────┼───────┐
│              XIAO ESP32S3 + ReSpeaker Lite (200台)      │
│   麦克风采集  →  Opus编码  →  Wi-Fi HTTP 上传              │
│   目标: http://192.168.31.45:8000/api/audio/upload       │
└─────────────────────────────────────────────────────────┘
```

## 技术栈

| 层级     | 技术                                                    |
| -------- | ------------------------------------------------------- |
| 边缘端   | ESP-IDF (C), Opus 编码, HTTP 上传                       |
| 后端服务 | Python 3.11, FastAPI, SQLAlchemy, Redis                 |
| AI 推理  | PyTorch 2.5.1, FunASR 1.3.14, CAM++, emotion2vec, FAISS |
| RAG 问答 | text2vec-base-chinese, FAISS (文本向量), llama.cpp + Qwen2.5-7B |
| 数据库   | MySQL 8.0, Redis 8.0, MinIO                             |
| 前端     | Vue 3, TypeScript, Element Plus, ECharts                |
| 部署     | 双服务器裸机部署, Nginx, Systemd, Miniconda             |

## 快速开始

### 1. 服务器规划

| 服务器       | IP            | 用途                            | 最低配置                         |
| ------------ | ------------- | ------------------------------- | -------------------------------- |
| **Server A** | 192.168.31.45 | 应用服务器 (前端 + 后端 + 存储) | 8核 CPU, 32GB RAM, 1TB SSD       |
| **Server B** | 192.168.31.4  | 推理服务器 (AI引擎)             | 8核 CPU, 32GB RAM, RTX 4090 24GB |

两台服务器需内网互通。Python 环境统一使用 Miniconda，conda 环境名 `voice`。

### 2. 部署 Server A (应用服务器)

```bash
cd /home/guwenjun/code/voice-ai-system
chmod +x scripts/deploy-server-a.sh
./scripts/deploy-server-a.sh 192.168.31.4
```

该脚本自动安装并配置:

- MySQL 8.0 + 建表
- Redis 8.0
- MinIO (对象存储)
- FastAPI 后端 (Uvicorn + Systemd)
- Vue3 前端构建 + Nginx 反向代理

### 3. 部署 Server B (推理服务器)

```bash
cd /home/guwenjun/code/voice-ai-system
chmod +x scripts/deploy-server-b.sh
./scripts/deploy-server-b.sh 192.168.31.45
```

该脚本自动安装并配置:

- CUDA 环境检查
- Miniconda conda 环境 (`voice`)
- PyTorch CUDA + AI 引擎依赖
- AI 模型预下载 (~5GB)
- AI Engine Systemd 服务

> **注意**: Server B 的 AI Engine 从项目根目录启动，模块路径为 `ai_engine.main:app`。

### 4. 验证部署

```bash
# 在 Server A 上
./scripts/check-status.sh 192.168.31.4
```

预期输出:

```
📦 Server A (本机) 服务:
  ✓ MySQL: 运行中
  ✓ Redis: 运行中 (PONG)
  ✓ MinIO: 运行中
  ✓ FastAPI 后端: 运行中
  ✓ Nginx: 运行中
  ✓ 前端页面: 可访问 (HTTP 200)

🧠 Server B (192.168.31.4) 服务:
  ✓ AI Engine: 运行中
```

### 5. 访问系统

| 服务         | 地址                             |
| ------------ | -------------------------------- |
| 前端         | `http://192.168.31.45`           |
| API 文档     | `http://192.168.31.45:8000/docs` |
| MinIO 控制台 | `http://192.168.31.45:9001`      |
| AI 引擎文档  | `http://192.168.31.4:8001/docs`  |

### 6. 默认账号

- 前端: `admin` / `admin123`
- MinIO: `minioadmin` / `minioadmin`

## 开发指南

### 后端开发 (Server A)

```bash
conda activate voice
cd server
pip install -r requirements.txt
pip install bcrypt==4.0.1

# 创建 .env
cat > .env <<'EOF'
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
AI_ENGINE_URL=http://192.168.31.4:8001
SECRET_KEY=dev-secret-key
EOF

uvicorn app.main:app --reload --port 8000
```

### AI 引擎开发 (Server B)

```bash
conda activate voice
cd /home/guwenjun/code/voice-ai-system

# 创建 .env
cat > ai_engine/.env <<'EOF'
MINIO_ENDPOINT=192.168.31.45:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=voice-audio
CUDA_VISIBLE_DEVICES=0
EOF

# 从项目根目录启动（重要：不能从 ai_engine 目录启动）
uvicorn ai_engine.main:app --reload --port 8001
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

- 后端 API: `http://192.168.31.45:8000/docs`
- AI 引擎: `http://192.168.31.4:8001/docs`

## 目录结构

```
voice-ai-system/
├── server/                     # 后端服务
│   ├── app/
│   │   ├── api/               # API 路由 (10个模块)
│   │   ├── models/            # 数据库模型
│   │   ├── services/          # 业务逻辑 (Worker)
│   │   └── core/              # 核心配置 (config, redis, search, security)
│   └── requirements.txt
├── ai_engine/                  # AI 推理引擎
│   ├── pipeline/              # 推理流水线
│   │   ├── asr_engine.py      # FunASR 语音识别
│   │   ├── speaker_engine.py  # CAM++ 说话人识别
│   │   ├── emotion_engine.py  # emotion2vec 情感分析
│   │   ├── nlu_engine.py      # NLU 关键词/意图
│   │   └── text_embedder.py   # text2vec 文本向量化
│   ├── speaker_db/            # FAISS 说话人检索
│   ├── rag/                   # RAG 知识库问答
│   │   ├── vector_store.py    # FAISS 文本向量存储
│   │   ├── retriever.py       # 向量检索器
│   │   └── generator.py       # llama.cpp LLM 客户端
│   └── requirements.txt
├── web/                        # Vue3 前端
│   ├── src/
│   │   ├── views/             # 页面 (11个)
│   │   ├── api/               # API 调用 (8个)
│   │   └── components/        # 公共组件
│   └── package.json
├── esp32-firmware/             # ESP32 固件
├── scripts/
│   ├── deploy-server-a.sh     # Server A 部署脚本
│   ├── deploy-server-b.sh     # Server B 部署脚本 (Miniconda)
│   ├── check-status.sh        # 服务状态检查
│   └── init-db.sql            # 数据库初始化
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
| RAG 问答 | text2vec + FAISS + Qwen2.5-7B, 本地离线推理 |
| 并发设备 | 200 台                            |
| 日均音频 | 1,600 小时 (~25GB)                |

## 端口清单

| 服务          | 端口 | 服务器   | 说明                        |
| ------------- | ---- | -------- | --------------------------- |
| Nginx         | 80   | Server A | 前端 + API 反向代理         |
| FastAPI       | 8000 | Server A | 后端 API (仅 Nginx 代理)    |
| MySQL         | 3306 | Server A | 数据库 (仅本机)             |
| Redis         | 6379 | Server A | 缓存/队列 (仅本机)          |
| MinIO         | 9000 | Server A | 对象存储 (内网)             |
| MinIO Console | 9001 | Server A | 管理控制台                  |
| AI Engine     | 8001 | Server B | 推理服务 (仅 Server A 调用) |
| llama.cpp     | 8080 | Server B | LLM 服务 (仅 AI Engine 调用) |

## 常见问题

| 问题                        | 原因                   | 解决                                          |
| --------------------------- | ---------------------- | --------------------------------------------- |
| Systemd `status=200/CHDIR`  | heredoc 变量展开为空   | 使用 `<<'EOF'` 单引号                         |
| passlib bcrypt 报错         | bcrypt>=4.1 不兼容     | `pip install bcrypt==4.0.1`                   |
| Nginx 端口 80 占用          | Apache 占用            | `sudo systemctl stop apache2`                 |
| Nginx 500 Permission denied | www-data 无权访问 home | `chmod 755 /home/用户名`                      |
| MinIO AccessDenied          | Snap 版冲突            | `snap disable minio`，用独立二进制            |
| vue-tsc 构建失败            | TS 版本不兼容          | 用 `npx vite build` 跳过类型检查              |
| faiss-gpu 版本冲突          | torch CUDA 版本不兼容  | 改用 `faiss-cpu`                              |
| AI Engine 相对导入失败      | 目录不对               | 从项目根目录运行 `uvicorn ai_engine.main:app` |
| emotion2vec 加载失败        | modelscope 版本问题    | 用 `funasr.AutoModel` 加载                    |

## License

MIT
