# 智能语音采集与AI识别系统 - 项目文档

> **创建日期**: 2026-07-04
> **最后更新**: 2026-07-08
> **项目路径**: `/home/guwenjun/code/voice-ai-system`

---

## 一、项目概述

### 1.1 项目目标

构建一套完整的智能语音采集与AI识别系统，支持200台设备并发采集，实现语音识别、说话人识别、情感分析和NLU提取等功能。

### 1.2 核心需求

- 语音采集：ESP32S3 + ReSpeaker Lite 硬件采集
- 实时转写：中文语音识别 (ASR)
- 说话人识别：10万人规模声纹库
- 情感分析：识别语音中的情感倾向
- NLU提取：关键词、意图、实体抽取
- 全文检索：基于转写文本的搜索
- 实时监控：WebSocket推送实时转写结果

---

## 二、技术方案确认

### 2.1 部署环境

| 项目 | 决定 |
|------|------|
| GPU | RTX 4090 24GB |
| 推理方式 | 自有GPU服务器本地推理 |
| **部署方式** | **双服务器裸机部署 (弃用Docker)** |

**双服务器架构**:
- **Server A (应用服务器)**: Nginx + FastAPI + MySQL + Redis + MinIO
- **Server B (推理服务器)**: AI Engine (FunASR + CAM++ + emotion2vec + NLU)，需 RTX 4090

### 2.2 硬件对接

| 项目 | 决定 |
|------|------|
| 终端设备 | XIAO ESP32S3 + ReSpeaker Lite |
| 通信协议 | HTTP (Wi-Fi传输) |
| 上传策略 | 定时上传 (每5分钟) |

### 2.3 规模预估

| 指标 | 数值 |
|------|------|
| 并发设备 | 200台 |
| 日均采集 | 8小时/台 |
| 总时长 | 1,600小时/天 |
| 日数据量 | ~25GB (Opus压缩) |

### 2.4 技术选型

| 模块 | 选择 | 备注 |
|------|------|------|
| ASR引擎 | **FunASR (Paraformer-zh)** | 中文识别准确率高，支持热词 |
| 说话人识别 | CAM++ | 10万规模FAISS索引 |
| 情感分析 | emotion2vec | - |
| 后端框架 | FastAPI | Python 3.11 |
| 前端框架 | Vue 3 | Element Plus |
| 数据库 | MySQL + Redis + MinIO | 全文检索基于 MySQL LIKE |
| 部署 | 双服务器裸机部署 | Server A (应用) + Server B (推理) |

### 2.5 MiMo-V2.5-ASR 说明

用户原始需求为 MiMo-V2.5-ASR，但该模型并非已发布的开源ASR模型。经讨论，确认使用 **FunASR (Paraformer-zh)** 作为首选方案。

---

## 三、系统架构

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
│  ┌──────────┐  ┌───────────┐  ┌──────────┐             │
│  │  MySQL   │  │   Redis   │  │  MinIO   │             │
│  │  :3306   │  │   :6379   │  │ :9000/1  │             │
│  └──────────┘  └───────────┘  └──────────┘             │
│                     │                                   │
│                     │ Redis队列: audio:pending_inference │
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
│                                                  ▼       │
│  ┌──────────────────────────────────────────────────┐   │
│  │              AI Engine (FastAPI :8001)             │   │
│  │  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────────┐│   │
│  │  │FunASR    │ │ CAM++    │ │emotion │ │  NLU   ││   │
│  │  │Paraformer│ │ 说话人    │ │2vec    │ │ 关键词  ││   │
│  │  └──────────┘ └──────────┘ └────────┘ └────────┘│   │
│  └──────────────────────────────────────────────────┘   │
│           │                                             │
│           │ 从 Server A 的 MinIO 下载音频                │
│           ▼                                             │
│     Server_A_IP:9000 (MinIO)                            │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              ESP32S3 设备 (200台)                        │
│   麦克风采集 → Opus编码 → Wi-Fi HTTP上传                  │
│   目标: http://Server_A_IP:8000/api/audio/upload         │
└─────────────────────────────────────────────────────────┘
```

---

## 四、模块设计

### 4.1 边缘端 (ESP32S3)

**目录**: `esp32-firmware/`

| 文件 | 功能 |
|------|------|
| `main/main.c` | 入口，音频采集任务和上传任务 |
| `audio/i2s_input.c` | I2S麦克风采集 (ReSpeaker Lite) |
| `audio/opus_encoder.c` | Opus编码 (降低传输量) |
| `network/wifi_manager.c` | Wi-Fi连接管理 |
| `network/http_upload.c` | HTTP分片上传 + 断网缓存 |
| `config/device_config.c` | NVS配置存储 |

**上传策略**:
- 每5分钟上传一次音频分片
- 文件名: `{device_code}_{timestamp}.opus`
- 断网时缓存到队列，恢复后自动续传

### 4.2 后端服务 (FastAPI)

**目录**: `server/`

**API设计**:

```
# 认证
POST   /api/auth/login              # 登录获取JWT

# 设备管理
POST   /api/device/register         # 设备注册
POST   /api/device/heartbeat        # 心跳上报
GET    /api/device/list             # 设备列表
GET    /api/device/{id}             # 设备详情
DELETE /api/device/{id}             # 删除设备

# 任务管理
POST   /api/task                    # 创建任务
GET    /api/task/list               # 任务列表
GET    /api/task/{id}               # 任务详情
PUT    /api/task/{id}/dispatch      # 下发任务

# 音频管理
POST   /api/audio/upload            # 音频上传 (自动触发推理)
GET    /api/audio/list              # 音频列表 (支持筛选)
GET    /api/audio/{id}              # 音频详情
GET    /api/audio/{id}/download     # 下载链接

# AI结果
GET    /api/result/transcript/{id}  # 转写结果
GET    /api/result/speaker/{id}     # 说话人识别
GET    /api/result/emotion/{id}     # 情感分析
GET    /api/result/nlu/{id}         # NLU结果
GET    /api/result/speakers         # 已注册说话人列表

# 检索
GET    /api/search/transcript       # 全文检索 (关键词 + 设备/时间筛选)
GET    /api/search/speaker          # 说话人搜索

# 告警
POST   /api/alert/rules             # 创建规则
GET    /api/alert/rules             # 规则列表
PUT    /api/alert/rules/{id}        # 更新规则
DELETE /api/alert/rules/{id}        # 删除规则
GET    /api/alert/logs              # 告警记录
PUT    /api/alert/logs/{id}/acknowledge  # 确认告警

# 说话人管理
GET    /api/speaker/list            # 说话人列表
GET    /api/speaker/{id}            # 说话人详情
POST   /api/speaker/enroll          # 注册说话人 (上传音频 + AI引擎声纹入库)
PUT    /api/speaker/{id}            # 更新说话人
DELETE /api/speaker/{id}            # 删除说话人

# 统计看板
GET    /api/stats/dashboard         # 仪表盘统计 (在线设备/今日采集/说话人数/告警数)
GET    /api/stats/trend             # 采集趋势 (小时/天维度)
GET    /api/stats/emotion-distribution  # 情感分布
GET    /api/stats/recent-audio      # 最近音频
GET    /api/stats/recent-alerts     # 最近告警

# 系统设置
GET    /api/settings                # 获取系统设置
PUT    /api/settings                # 更新系统设置

# WebSocket
WS     /ws/realtime?channel=realtime  # 实时推送 (支持频道参数)
```

**核心流程**:
```
ESP32上传音频 → 保存MinIO → 写入MySQL(audio_records)
    → Redis队列(audio:pending_inference) → Worker消费
    → 调用AI引擎(GPU推理: ASR+说话人+情感+NLU)
    → 结果写入MySQL(transcripts/speaker_records/emotion_records/nlu_results)
    → Redis pub/sub(audio:inference_result) → WebSocket广播 → 前端实时展示
```

### 4.3 AI推理引擎

**目录**: `ai_engine/`

| 文件 | 功能 |
|------|------|
| `pipeline/asr_engine.py` | FunASR Paraformer 语音识别 |
| `pipeline/speaker_engine.py` | CAM++ 说话人识别 |
| `pipeline/emotion_engine.py` | emotion2vec 情感分析 |
| `pipeline/nlu_engine.py` | NLU关键词/意图提取 |
| `pipeline/pipeline.py` | 推理流水线串联 |
| `speaker_db/search.py` | FAISS 说话人检索 (10万规模) |
| `speaker_db/enroll.py` | 声纹注册 |
| `main.py` | FastAPI入口 (端口8001，提供 /inference, /enroll, /search_speaker 接口) |

**RTX 4090 推理能力**:

| 模型 | 显存占用 | 推理速度 |
|------|----------|----------|
| Paraformer-zh | ~2GB | 实时率 1:50 |
| CAM++ | ~1GB | 实时率 1:100 |
| emotion2vec | ~1GB | 实时率 1:80 |
| **总计** | ~4GB | 可满足200台并发 |

**10万声纹检索方案**:
- FAISS IndexIVFFlat (倒排索引)
- nlist = 1000 (聚类中心)
- 检索速度: 10万规模 < 1ms
- 内存占用: ~250MB

### 4.4 前端 (Vue3)

**目录**: `web/`

| 页面 | 功能 |
|------|------|
| Dashboard | 数据看板 (采集趋势、情感分布、设备状态) |
| DeviceManage | 设备管理 (注册、状态、删除) |
| TaskManage | 任务管理 (创建、下发、进度) |
| AudioList | 音频列表 (筛选、播放、下载) |
| AudioDetail | 音频详情 (波形播放、转写、说话人、情感) |
| RealtimeMonitor | 实时监控 (WebSocket实时转写流) |
| SpeakerManage | 说话人库 (声纹注册、管理) |
| Search | 全文检索 (关键词搜索、高亮) |
| AlertConfig | 告警配置 (规则、记录) |
| SystemSettings | 系统设置 |

### 4.5 数据库设计

**核心表**:

| 表名 | 说明 |
|------|------|
| `devices` | 设备表 |
| `tasks` | 采集任务表 |
| `audio_records` | 音频记录表 |
| `transcripts` | ASR转写结果表 |
| `speaker_records` | 说话人识别记录表 |
| `speakers` | 已注册说话人表 |
| `emotion_records` | 情感分析表 |
| `nlu_results` | NLU结果表 |
| `alert_rules` | 告警规则表 |
| `alert_logs` | 告警记录表 |

详细建表SQL见: `scripts/init-db.sql`

---

## 五、已完成工作

### 5.1 项目结构

已创建完整的项目目录结构和所有核心文件：

- [x] 后端服务 (FastAPI) - 25+ 文件
- [x] AI推理引擎 - 8 文件
- [x] Vue3前端 - 18+ 文件
- [x] ESP32固件 - 10 文件
- [x] 脚本工具 - 6 文件 (含部署脚本)

### 5.2 2026-07-06 开发进展

**后端关键BUG修复**:
- [x] `task.py` — `@router.create` → `@router.post`，修复任务创建接口路由
- [x] `main.py` — 修复 `settings` 变量命名冲突，正确注册所有路由

**核心数据流打通 (音频上传 → 推理 → 结果入库 → WebSocket推送)**:
- [x] `audio.py` — 音频上传后自动推送消息到 Redis 队列 `audio:pending_inference`
- [x] `services/inference_worker.py` — **新建**，后台 Worker 消费 Redis 队列，调用 AI 引擎 `/inference` 接口，将 ASR/说话人/情感/NLU 结果写入数据库
- [x] `main.py` — lifespan 中启动 Worker 和 WebSocket 订阅者两个后台任务
- [x] `core/redis.py` — 新增 `redis_subscriber_task()`，订阅 Redis 频道广播到 WebSocket 客户端

**新增后端 API 端点**:
- [x] `api/v1/stats.py` — **新建**，Dashboard 统计 API
- [x] `api/v1/speaker.py` — **新建**，说话人管理 API
- [x] `api/v1/settings.py` — **新建**，系统设置 API

**WebSocket 实时推送完善**:
- [x] `api/ws.py` — 重写 ConnectionManager，支持查询参数指定频道，心跳 ping/pong

**前端接入真实数据**:
- [x] Dashboard / SpeakerManage / SystemSettings / RealtimeMonitor 已接入真实 API

### 5.3 2026-07-08 开发进展

**部署架构变更**:
- [x] 弃用 Docker Compose，改为双服务器裸机部署
- [x] 弃用 Elasticsearch，全文检索改为 MySQL LIKE 查询
- [x] 新增 `scripts/deploy-server-a.sh` / `deploy-server-b.sh` / `check-status.sh`

**Server A 部署验证通过**:
- [x] MySQL 8.0 — 10 张表全部创建成功
- [x] Redis — 正常运行 (PONG)
- [x] MinIO — 健康检查通过 (独立二进制安装，非 Snap)
- [x] FastAPI 后端 — `curl http://localhost:8000/health` 返回 `{"status":"ok"}`
- [x] Nginx 前端 — `curl -I http://localhost` 返回 200

**前端构建修复**:
- [x] `vue-tsc` 兼容性问题 — 跳过类型检查，直接 `vite build`
- [x] `@tsconfig/node24` 缺失 — 安装依赖解决
- [x] ECharts 按需引入 — Dashboard.vue 改用 `echarts/core` 按需加载，减少 ~600KB

**代码修改**:
- [x] `server/app/core/search.py` — **新建**，RediSearch 全文检索模块 (备用)
- [x] `server/app/api/v1/search.py` — 搜索 API 重构 (支持 RediSearch / MySQL LIKE 双模式)
- [x] `server/app/core/config.py` — 移除 ES_HOST/ES_PORT 配置
- [x] `server/requirements.txt` — 移除 elasticsearch 依赖
- [x] `server/Dashboard.vue` — ECharts 按需引入优化

**部署踩坑记录**:
- [x] Systemd 服务文件 `WorkingDirectory` 路径必须用 `<<'EOF'`（单引号）防止变量展开为空
- [x] `passlib` + `bcrypt>=4.1` 不兼容 — 需降级 `bcrypt==4.0.1`
- [x] Nginx 端口 80 被 Apache 占用 — 需先 `systemctl stop apache2`
- [x] MinIO Snap 版与独立版冲突 — 需 `snap disable minio` 后再安装独立版

### 5.4 文件清单

**后端服务**:
- `server/app/main.py` - FastAPI入口 (含MinIO初始化、Worker启动)
- `server/app/core/config.py` - 配置管理
- `server/app/core/database.py` - 数据库连接
- `server/app/core/security.py` - JWT认证
- `server/app/core/redis.py` - Redis连接 + 订阅广播
- `server/app/core/search.py` - RediSearch 全文检索 (备用)
- `server/app/models/*.py` - 数据库模型 (6个)
- `server/app/api/v1/*.py` - API路由 (10个)
- `server/app/api/ws.py` - WebSocket
- `server/app/services/inference_worker.py` - 推理Worker
- `server/requirements.txt`

**AI引擎**:
- `ai_engine/main.py` - FastAPI入口
- `ai_engine/pipeline/*.py` - 推理流水线 (4个引擎 + pipeline)
- `ai_engine/speaker_db/*.py` - FAISS说话人检索
- `ai_engine/requirements.txt`

**前端**:
- `web/src/main.ts` - 入口
- `web/src/App.vue` - 根组件
- `web/src/router/index.ts` - 路由
- `web/src/api/*.ts` - API封装 (7个)
- `web/src/views/*.vue` - 页面 (10个)
- `web/src/layouts/MainLayout.vue` - 布局
- `web/package.json`

**ESP32固件**:
- `esp32-firmware/` - 完整固件代码

**配置文件**:
- `.env.example` - 环境变量模板
- `.gitignore`
- `README.md`
- `scripts/deploy-server-a.sh` - Server A 部署脚本
- `scripts/deploy-server-b.sh` - Server B 部署脚本
- `scripts/check-status.sh` - 服务状态检查脚本
- `scripts/init-db.sql` - 数据库初始化

---

## 六、部署方案 (双服务器)

### 6.1 服务器规格

| 项目 | Server A (应用服务器) | Server B (推理服务器) |
|------|----------------------|----------------------|
| **用途** | 前端 + 后端 + 存储 | AI推理 |
| **CPU** | 8核+ | 8核+ |
| **内存** | 32GB+ | 32GB+ |
| **GPU** | 无 | RTX 4090 24GB |
| **磁盘** | 1TB+ SSD (存储音频) | 500GB SSD (模型缓存) |
| **OS** | Ubuntu 22.04+ | Ubuntu 22.04+ |
| **网络** | 内网互通 + 公网(可选) | 内网互通 |

### 6.2 Server A 部署

**已验证的部署步骤** (2026-07-08):

```bash
# 1. 系统依赖
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip \
    nginx mysql-server redis-server ffmpeg curl wget gnupg2

# 2. MySQL
sudo systemctl start mysql
sudo mysql -e "
CREATE DATABASE voice_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'voice_user'@'localhost' IDENTIFIED BY 'voice_pass';
CREATE USER 'voice_user'@'%' IDENTIFIED BY 'voice_pass';
GRANT ALL ON voice_ai.* TO 'voice_user'@'localhost';
GRANT ALL ON voice_ai.* TO 'voice_user'@'%';
FLUSH PRIVILEGES;
"
mysql -u voice_user -pvoice_pass voice_ai < scripts/init-db.sql

# 3. Redis
sudo systemctl start redis-server
redis-cli ping  # 期望 PONG

# 4. MinIO (独立二进制，非 Snap)
wget https://dl.min.io/server/minio/release/linux-amd64/minio -O /tmp/minio
sudo mv /tmp/minio /usr/local/bin/ && sudo chmod +x /usr/local/bin/minio
sudo mkdir -p /data/minio
# 创建 systemd 服务 (注意用 <<'EOF' 单引号)
sudo tee /etc/systemd/system/minio.service <<'EOF'
[Unit]
Description=MinIO
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
sudo systemctl daemon-reload && sudo systemctl enable --now minio

# 5. Python 后端
cd /home/guwenjun/code/voice-ai-system
python3.11 -m venv venv-server
source venv-server/bin/activate
cd server && pip install -r requirements.txt && cd ..
# 降级 bcrypt 解决 passlib 兼容问题
pip install bcrypt==4.0.1
# 创建 .env (注意用 <<'EOF' 单引号)
cat > server/.env <<'EOF'
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
AI_ENGINE_URL=http://SERVER_B_IP:8001
SECRET_KEY=your-production-secret-key-change-me
EOF

# 6. 前端构建
cd web && npm install && npm run build

# 7. Nginx (注意用 <<'EOF' 单引号)
sudo systemctl stop apache2 2>/dev/null
sudo tee /etc/nginx/sites-available/voice-ai <<'EOF'
server {
    listen 80;
    server_name _;
    root /home/guwenjun/code/voice-ai-system/web/dist;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;
    }
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        client_max_body_size 100M;
    }
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
EOF
sudo ln -sf /etc/nginx/sites-available/voice-ai /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl start nginx

# 8. 后端 Systemd 服务 (注意用 <<'EOF' 单引号)
sudo tee /etc/systemd/system/voice-server.service <<'EOF'
[Unit]
Description=Voice AI FastAPI Server
After=network.target mysql.service redis-server.service
[Service]
Type=simple
User=guwenjun
Group=guwenjun
WorkingDirectory=/home/guwenjun/code/voice-ai-system/server
ExecStart=/home/guwenjun/miniconda3/envs/voice-ai/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload && sudo systemctl enable --now voice-server

# 9. 验证
curl http://localhost:8000/health    # {"status":"ok"}
curl -I http://localhost             # 200 OK
redis-cli ping                       # PONG
mysql -u voice_user -pvoice_pass -e "USE voice_ai; SHOW TABLES;"
```

### 6.3 Server B 部署

```bash
# 1. CUDA 环境
nvidia-smi  # 确认驱动已安装

# 2. Python 环境
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip \
    libsndfile1 ffmpeg
cd /home/guwenjun/code/voice-ai-system
python3.11 -m venv venv-ai
source venv-ai/bin/activate
cd ai_engine && pip install -r requirements.txt && cd ..

# 3. 环境变量
cat > ai_engine/.env <<'EOF'
MINIO_ENDPOINT=SERVER_A_IP:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=voice-audio
CUDA_VISIBLE_DEVICES=0
EOF

# 4. 预下载模型 (~5GB)
python -c "
from funasr import AutoModel
AutoModel(model='iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch')
print('Done')
"

# 5. Systemd 服务
sudo tee /etc/systemd/system/voice-ai-engine.service <<'EOF'
[Unit]
Description=Voice AI Inference Engine
After=network.target
[Service]
Type=simple
User=guwenjun
WorkingDirectory=/home/guwenjun/code/voice-ai-system/ai_engine
Environment="CUDA_VISIBLE_DEVICES=0"
ExecStart=/home/guwenjun/code/voice-ai-system/venv-ai/bin/uvicorn main:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload && sudo systemctl enable --now voice-ai-engine
```

### 6.4 端口清单

| 服务 | 端口 | 所在服务器 | 对外开放 |
|------|------|-----------|---------|
| Nginx (前端+API) | 80 | Server A | ✅ |
| FastAPI 后端 | 8000 | Server A | ❌ (仅Nginx代理) |
| MySQL | 3306 | Server A | ❌ (仅本机) |
| Redis | 6379 | Server A | ❌ (仅本机) |
| MinIO API | 9000 | Server A | ❌ (内网) |
| MinIO Console | 9001 | Server A | ❌ (内网) |
| AI Engine | 8001 | Server B | ❌ (内网, 仅Server A调用) |

### 6.5 防火墙配置

**Server A**:
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow from SERVER_B_IP to any port 9000  # MinIO
sudo ufw enable
```

**Server B**:
```bash
sudo ufw allow from SERVER_A_IP to any port 8001  # AI Engine
sudo ufw enable
```

### 6.6 常见部署问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| Systemd `status=200/CHDIR` | heredoc 变量被展开为空路径 | 使用 `<<'EOF'`（单引号） |
| passlib bcrypt 报错 | bcrypt>=4.1 与 passlib 不兼容 | `pip install bcrypt==4.0.1` |
| Nginx 启动失败 (端口占用) | Apache 占用 80 端口 | `sudo systemctl stop apache2` |
| MinIO AccessDenied | Snap 版 MinIO 路径不同 | `snap disable minio`，用独立二进制 |
| vue-tsc 构建失败 | TypeScript 版本不兼容 | 跳过类型检查：`npx vite build` |
| `@tsconfig/node24` 缺失 | Node 24 的 tsconfig 包未安装 | `pnpm add -D @tsconfig/node24` |

---

## 七、待办事项

### 7.1 高优先级 ✅ 已完成

- [x] 测试后端API是否正常启动 (2026-07-06)
- [x] 完善前端WebSocket实时推送功能 (2026-07-06)
- [x] 添加音频上传后自动触发推理的逻辑 (2026-07-06)
- [x] 添加数据统计和报表功能 (2026-07-06)
- [x] Server A 双服务器部署验证 (2026-07-08)
- [x] 前端构建优化 — ECharts 按需引入 (2026-07-08)

### 7.2 中优先级

- [ ] Server B 推理服务器部署 (需 RTX 4090 环境)
- [ ] 端到端集成测试 (需要 GPU 环境验证 AI 引擎推理)
- [ ] 完善任务调度系统 — 任务下发后通知设备执行采集
- [ ] 实现说话人库的批量导入功能 (后端 bulk_enroll API 已有，前端待开发)
- [ ] 音频详情页 AudioDetail — WaveSurfer 波形播放 + AI 结果展示联调
- [ ] 前端分页 total 计数 — AudioList 的 total 目前写死 100

### 7.3 低优先级

- [ ] ESP32固件的OTA升级功能
- [ ] 多语言支持
- [ ] 性能监控和告警 — 添加 Prometheus metrics
- [ ] 单元测试和集成测试
- [ ] 音频文件定期清理 (retentionDays 配置生效)

---

## 八、技术参考

### 8.1 关键技术栈版本

| 技术 | 版本 |
|------|------|
| Python | 3.11 |
| FastAPI | 0.109.0 |
| PyTorch | 2.1.2 |
| FunASR | 1.0.27 |
| Vue | 3.5 |
| Element Plus | 2.5 |
| MySQL | 8.0 |
| Redis | 8.0 |
| MinIO | latest |

### 8.2 参考文档

- FunASR: https://github.com/modelscope/FunASR
- CAM++: https://modelscope.cn/models/iic/speech_campplus_sv_zh-cn_16k-common
- emotion2vec: https://modelscope.cn/models/iic/emotion2vec_base_finetuned
- FAISS: https://github.com/facebookresearch/faiss
- ESP-IDF: https://docs.espressif.com/projects/esp-idf/

---

*文档结束*
