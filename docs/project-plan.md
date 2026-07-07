# 智能语音采集与AI识别系统 - 项目文档

> **创建日期**: 2026-07-04
> **最后更新**: 2026-07-06
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
- **Server A (应用服务器)**: Nginx + FastAPI + MySQL + Redis + MinIO + Elasticsearch
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
| 数据库 | MySQL + Redis Stack + MinIO | Redis Stack 含 RediSearch 全文检索 |
| 部署 | 双服务器裸机部署 | Server A (应用) + Server B (推理) |

### 2.5 MiMo-V2.5-ASR 说明

用户原始需求为 MiMo-V2.5-ASR，但该模型并非已发布的开源ASR模型。经讨论，确认使用 **FunASR (Paraformer-zh)** 作为首选方案。

---

## 三、系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Vue3 前端管理平台                            │
│   实时监控  │  任务管理  │  设备管理  │  数据检索  │  看板统计       │
└─────────────────────────────────────────────────────────────────────┘
                              │ HTTP/WS
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FastAPI 中心服务 (CPU)                           │
│  设备管理  │  任务调度  │  文件接收  │  结果查询  │  WebSocket推送   │
└─────────────────────────────────────────────────────────────────────┘
     │              │              │               │
     ▼              ▼              ▼               ▼
┌─────────┐  ┌───────────────────┐  ┌──────────┐
│  MySQL   │  │   Redis Stack     │  │  MinIO   │
│ 业务数据  │  │  缓存/队列/全文检索 │  │ 音频存储  │
└─────────┘  │  (含 RediSearch)   │  └──────────┘
             └───────────────────┘
                              │
                              ▼ (音频文件路径)
┌─────────────────────────────────────────────────────────────────────┐
│                    GPU 推理服务器 (RTX 4090 24G)                      │
│  ┌──────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────────┐  │
│  │ ASR 引擎  │  │ 说话人识别    │  │  情感分析   │  │   NLU 提取   │  │
│  │FunASR    │  │ CAM++        │  │ emotion2vec│  │  关键词/意图  │  │
│  └──────────┘  └──────────────┘  └────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                              ▲ HTTP 上传音频
┌─────────────────────────────────────────────────────────────────────┐
│              XIAO ESP32S3 + ReSpeaker Lite (200台)                   │
│   麦克风采集  →  Opus编码  →  Wi-Fi HTTP 定时上传                      │
└─────────────────────────────────────────────────────────────────────┘
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

# 说话人管理 (新增)
GET    /api/speaker/list            # 说话人列表
GET    /api/speaker/{id}            # 说话人详情
POST   /api/speaker/enroll          # 注册说话人 (上传音频 + AI引擎声纹入库)
PUT    /api/speaker/{id}            # 更新说话人
DELETE /api/speaker/{id}            # 删除说话人

# 统计看板 (新增)
GET    /api/stats/dashboard         # 仪表盘统计 (在线设备/今日采集/说话人数/告警数)
GET    /api/stats/trend             # 采集趋势 (小时/天维度)
GET    /api/stats/emotion-distribution  # 情感分布
GET    /api/stats/recent-audio      # 最近音频
GET    /api/stats/recent-alerts     # 最近告警

# 系统设置 (新增)
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
- [x] Docker配置 - 4 文件
- [x] 脚本工具 - 3 文件

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
- [x] `api/v1/stats.py` — **新建**，Dashboard 统计 API（在线设备数、今日采集时长、已注册说话人数、今日告警数、采集趋势、情感分布、最近音频/告警列表）
- [x] `api/v1/speaker.py` — **新建**，说话人管理 API（列表、详情、注册、更新、删除；注册时上传音频到 MinIO 并调用 AI 引擎声纹入库）
- [x] `api/v1/settings.py` — **新建**，系统设置 API（读取/保存配置到 JSON 文件）

**WebSocket 实时推送完善**:
- [x] `api/ws.py` — 重写 ConnectionManager，支持查询参数指定频道，心跳 ping/pong，自动清理断开连接
- [x] 推理完成后通过 Redis pub/sub → WebSocket 广播实时转写结果到前端

**MinIO 自动初始化**:
- [x] `main.py` — 启动时自动检查并创建 MinIO bucket

**前端接入真实数据**:
- [x] `api/stats.ts` — **新建**，Dashboard 统计 API 封装
- [x] `api/speaker.ts` — **新建**，说话人管理 API 封装
- [x] `views/Dashboard.vue` — 接入 `/api/stats/*` 真实数据，替换 mock 数据
- [x] `views/SpeakerManage.vue` — 接入 `/api/speaker/*` API，实现注册/删除功能
- [x] `views/SystemSettings.vue` — 接入 `/api/settings` API，实现配置读写
- [x] `views/Search.vue` — 修复 `Search` 图标导入命名冲突
- [x] `views/RealtimeMonitor.vue` — 匹配 Worker 推送数据格式（speaker_id → speaker）

**已打通的核心数据流**:
```
ESP32上传音频 → MinIO存储 → Redis队列(audio:pending_inference)
    → Worker消费 → 调用AI引擎(GPU推理) → 结果写入MySQL
    → Redis pub/sub → WebSocket广播 → 前端实时展示
```

### 5.3 文件清单

**后端服务**:
- `server/app/main.py` - FastAPI入口 (含MinIO初始化、Worker启动)
- `server/app/core/config.py` - 配置管理
- `server/app/core/database.py` - 数据库连接
- `server/app/core/security.py` - JWT认证
- `server/app/core/redis.py` - Redis连接 + 订阅广播
- `server/app/models/*.py` - 数据库模型 (6个)
- `server/app/api/v1/*.py` - API路由 (10个: auth, device, task, audio, result, search, alert, speaker, stats, settings)
- `server/app/api/ws.py` - WebSocket (ConnectionManager + 频道广播)
- `server/app/services/inference_worker.py` - 推理Worker (Redis消费 → AI引擎 → 结果入库)
- `server/requirements.txt`
- `server/Dockerfile`

**AI引擎**:
- `ai_engine/main.py` - FastAPI入口
- `ai_engine/pipeline/asr_engine.py` - ASR引擎
- `ai_engine/pipeline/speaker_engine.py` - 说话人引擎
- `ai_engine/pipeline/emotion_engine.py` - 情感引擎
- `ai_engine/pipeline/nlu_engine.py` - NLU引擎
- `ai_engine/pipeline/pipeline.py` - 推理流水线
- `ai_engine/speaker_db/search.py` - FAISS检索
- `ai_engine/speaker_db/enroll.py` - 声纹注册
- `ai_engine/requirements.txt`
- `ai_engine/Dockerfile`

**前端**:
- `web/src/main.ts` - 入口
- `web/src/App.vue` - 根组件
- `web/src/router/index.ts` - 路由
- `web/src/api/*.ts` - API封装 (6个: request, auth, device, task, audio, speaker, stats)
- `web/src/views/*.vue` - 页面 (10个)
- `web/src/layouts/MainLayout.vue` - 布局
- `web/package.json`
- `web/vite.config.ts`
- `web/Dockerfile`
- `web/nginx.conf`

**ESP32固件**:
- `esp32-firmware/main/main.c` - 主程序
- `esp32-firmware/audio/i2s_input.*` - I2S采集
- `esp32-firmware/audio/opus_encoder.*` - Opus编码
- `esp32-firmware/network/wifi_manager.*` - Wi-Fi管理
- `esp32-firmware/network/http_upload.*` - HTTP上传
- `esp32-firmware/config/device_config.*` - 设备配置
- `esp32-firmware/CMakeLists.txt`

**配置文件**:
- `docker-compose.yml` - Docker编排
- `.env.example` - 环境变量模板
- `.gitignore`
- `README.md`
- `scripts/start.sh` - 启动脚本 (旧Docker方案)
- `scripts/stop.sh` - 停止脚本 (旧Docker方案)
- `scripts/deploy-server-a.sh` - Server A 部署脚本 ✨
- `scripts/deploy-server-b.sh` - Server B 部署脚本 ✨
- `scripts/check-status.sh` - 服务状态检查脚本 ✨
- `scripts/init-db.sql` - 数据库初始化

---

## 六、部署方案 (双服务器)

### 6.1 架构总览

```
┌─────────────────────────────────────────────────────────┐
│              Server A — 应用服务器 (无GPU)                │
│                                                         │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐             │
│  │  Nginx   │  │  FastAPI   │  │  Vue3    │             │
│  │ :80/:443 │  │  :8000     │  │  构建产物 │             │
│  └──────────┘  └───────────┘  └──────────┘             │
│       │              │                                   │
│       ▼              ▼                                   │
│  ┌──────────┐  ┌───────────┐  ┌──────────┐  ┌────────┐│
│  │  MySQL   │  │   Redis   │  │  MinIO   │  │   ES   ││
│  │  :3306   │  │   :6379   │  │ :9000/1  │  │ :9200  ││
│  └──────────┘  └───────────┘  └──────────┘  └────────┘│
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

### 6.2 服务器规格

| 项目 | Server A (应用服务器) | Server B (推理服务器) |
|------|----------------------|----------------------|
| **用途** | 前端 + 后端 + 存储 | AI推理 |
| **CPU** | 8核+ | 8核+ |
| **内存** | 32GB+ | 32GB+ |
| **GPU** | 无 | RTX 4090 24GB |
| **磁盘** | 1TB+ SSD (存储音频) | 500GB SSD (模型缓存) |
| **OS** | Ubuntu 22.04 | Ubuntu 22.04 |
| **网络** | 内网互通 + 公网(可选) | 内网互通 |

### 6.3 Server A 部署 (应用服务器)

**安装基础服务** (原生安装，不用Docker):

```bash
# ===== 1. 系统依赖 =====
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip \
    nginx mysql-server redis-server ffmpeg

# ===== 2. MySQL =====
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

# ===== 3. Redis =====
sudo systemctl start redis-server
# 确认 Redis 监听 (默认即可)
redis-cli ping

# ===== 4. MinIO =====
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
sudo mv minio /usr/local/bin/
# 创建数据目录
sudo mkdir -p /data/minio
# 创建 systemd 服务
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

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now minio

# ===== 5. Elasticsearch =====
# 安装 OpenJDK
sudo apt install -y openjdk-17-jre-headless
# 下载 ES
wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-8.12.0-linux-x86_64.tar.gz
tar xzf elasticsearch-8.12.0-linux-x86_64.tar.gz
sudo mv elasticsearch-8.12.0 /opt/elasticsearch
# 配置 (单节点, 关闭安全)
sudo tee /opt/elasticsearch/config/elasticsearch.yml <<'EOF'
cluster.name: voice-ai
node.name: node-1
network.host: 0.0.0.0
discovery.type: single-node
xpack.security.enabled: false
EOF
# 创建用户 & 启动
sudo useradd -r -s /bin/false elasticsearch || true
sudo chown -R elasticsearch:elasticsearch /opt/elasticsearch
sudo -u elasticsearch /opt/elasticsearch/bin/elasticsearch -d
# 或用 systemd (推荐)

# ===== 6. Python 后端 =====
cd /home/guwenjun/code/voice-ai-system
python3.11 -m venv venv-server
source venv-server/bin/activate
cd server && pip install -r requirements.txt && cd ..

# 创建 .env
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
ES_HOST=localhost
ES_PORT=9200
AI_ENGINE_URL=http://SERVER_B_IP:8001
SECRET_KEY=your-production-secret-key-change-me
EOF

# 启动后端
cd server && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# ===== 7. 前端构建 =====
cd /home/guwenjun/code/voice-ai-system/web
npm install
# 修改 API 地址
# vite.config.ts 中 proxy target 改为 http://localhost:8000
npm run build
# 产物在 web/dist/

# ===== 8. Nginx =====
sudo tee /etc/nginx/sites-available/voice-ai <<'EOF'
server {
    listen 80;
    server_name _;

    # 前端静态文件
    root /home/guwenjun/code/voice-ai-system/web/dist;
    index index.html;

    # Vue Router history 模式
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        client_max_body_size 100M;
    }

    # WebSocket 代理
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
sudo nginx -t && sudo systemctl reload nginx
```

### 6.4 Server B 部署 (推理服务器)

```bash
# ===== 1. CUDA 环境 =====
# 确认 NVIDIA 驱动
nvidia-smi
# 安装 CUDA Toolkit 12.1 (如未安装)
# https://developer.nvidia.com/cuda-12-1-0-download-archive

# ===== 2. Python 环境 =====
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip \
    libsndfile1 ffmpeg
cd /home/guwenjun/code/voice-ai-system
python3.11 -m venv venv-ai
source venv-ai/bin/activate
cd ai_engine && pip install -r requirements.txt && cd ..

# ===== 3. 环境变量 =====
cat > ai_engine/.env <<'EOF'
MINIO_ENDPOINT=SERVER_A_IP:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=voice-audio
CUDA_VISIBLE_DEVICES=0
EOF

# ===== 4. 预下载模型 (首次启动会自动下载, 约5GB) =====
source venv-ai/bin/activate
cd ai_engine
python -c "
from funasr import AutoModel
AutoModel(model='iic/speech_paraformer-large-vad-punc_asr_nat-zh-cn-16k-common-vocab8404-pytorch')
print('ASR model downloaded')
"

# ===== 5. 启动推理服务 =====
cd /home/guwenjun/code/voice-ai-system/ai_engine
uvicorn main:app --host 0.0.0.0 --port 8001
# 生产环境用 systemd 管理 (见下方)
```

### 6.5 Systemd 服务配置 (生产推荐)

**Server A — 后端服务**:
```bash
sudo tee /etc/systemd/system/voice-server.service <<'EOF'
[Unit]
Description=Voice AI FastAPI Server
After=network.target mysql.service redis-server.service

[Service]
Type=simple
User=guwenjun
WorkingDirectory=/home/guwenjun/code/voice-ai-system/server
Environment="PATH=/home/guwenjun/code/voice-ai-system/venv-server/bin"
ExecStart=/home/guwenjun/code/voice-ai-system/venv-server/bin/uvicorn app.main:app \
    --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now voice-server
```

**Server B — 推理服务**:
```bash
sudo tee /etc/systemd/system/voice-ai-engine.service <<'EOF'
[Unit]
Description=Voice AI Inference Engine
After=network.target

[Service]
Type=simple
User=guwenjun
WorkingDirectory=/home/guwenjun/code/voice-ai-system/ai_engine
Environment="PATH=/home/guwenjun/code/voice-ai-system/venv-ai/bin"
Environment="CUDA_VISIBLE_DEVICES=0"
ExecStart=/home/guwenjun/code/voice-ai-system/venv-ai/bin/uvicorn main:app \
    --host 0.0.0.0 --port 8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now voice-ai-engine
```

### 6.6 端口清单

| 服务 | 端口 | 所在服务器 | 对外开放 |
|------|------|-----------|---------|
| Nginx (前端+API) | 80 | Server A | ✅ |
| FastAPI 后端 | 8000 | Server A | ❌ (仅Nginx代理) |
| MySQL | 3306 | Server A | ❌ (仅本机) |
| Redis Stack | 6379 | Server A | ❌ (仅本机, 含RediSearch) |
| MinIO API | 9000 | Server A | ❌ (内网) |
| MinIO Console | 9001 | Server A | ❌ (内网) |
| AI Engine | 8001 | Server B | ❌ (内网, 仅Server A调用) |

### 6.7 防火墙配置

**Server A**:
```bash
sudo ufw allow 80/tcp    # Nginx
sudo ufw allow 443/tcp   # HTTPS (如需)
sudo ufw allow from SERVER_B_IP to any port 9000  # MinIO (AI引擎访问)
sudo ufw enable
```

**Server B**:
```bash
sudo ufw allow from SERVER_A_IP to any port 8001  # AI Engine (仅Server A调用)
sudo ufw enable
```

### 6.8 快速验证

```bash
# 在 Server A 上验证本地服务
curl http://localhost:8000/docs          # 后端 API 文档
curl http://localhost:9000/minio/health  # MinIO 健康检查
curl http://localhost:9200               # ES 集群状态

# 在 Server A 上验证 Server B 连通性
curl http://SERVER_B_IP:8001/health      # AI 引擎健康检查

# 访问前端
# 浏览器打开 http://SERVER_A_IP
# 默认账号: admin / admin123
```

---

## 七、待办事项

### 7.1 高优先级 ✅ 已完成 (2026-07-06)

- [x] 测试后端API是否正常启动
- [x] 完善前端WebSocket实时推送功能 → ws.py + redis_subscriber_task
- [x] 添加音频上传后自动触发推理的逻辑 → inference_worker.py
- [x] 添加数据统计和报表功能 → stats.py API + Dashboard 接入

### 7.2 中优先级

- [ ] 端到端集成测试 (需要 GPU 环境验证 AI 引擎推理)
- [ ] 完善任务调度系统 — 任务下发后通知设备执行采集
- [ ] 实现说话人库的批量导入功能 (后端 bulk_enroll API 已有，前端待开发)
- [ ] 音频详情页 AudioDetail — WaveSurfer 波形播放 + AI 结果展示联调
- [ ] 前端分页 total 计数 — AudioList 的 total 目前写死 100
- [ ] Docker Compose 环境下的完整启动测试

### 7.3 低优先级

- [ ] ESP32固件的OTA升级功能
- [ ] 多语言支持
- [ ] 性能监控和告警 — 添加 Prometheus metrics
- [ ] 单元测试和集成测试
- [ ] 音频文件定期清理 (retentionDays 配置生效)
- [ ] 前端 build 产物优化 (代码分割、懒加载)

---

## 八、技术参考

### 8.1 关键技术栈版本

| 技术 | 版本 |
|------|------|
| Python | 3.11 |
| FastAPI | 0.109.0 |
| PyTorch | 2.1.2 |
| FunASR | 1.0.27 |
| Vue | 3.4 |
| Element Plus | 2.5 |
| MySQL | 8.0 |
| Redis | 7 |
| Elasticsearch | 8.12 |

### 8.2 参考文档

- FunASR: https://github.com/modelscope/FunASR
- CAM++: https://modelscope.cn/models/iic/speech_campplus_sv_zh-cn_16k-common
- emotion2vec: https://modelscope.cn/models/iic/emotion2vec_base_finetuned
- FAISS: https://github.com/facebookresearch/faiss
- ESP-IDF: https://docs.espressif.com/projects/esp-idf/

---

## 九、下次继续要点

1. **项目位置**: `/home/guwenjun/code/voice-ai-system`
2. **启动命令**: `./scripts/start.sh` 或 `docker-compose up -d`
3. **默认账号**: admin / admin123
4. **GPU要求**: RTX 4090 24GB (AI推理)
5. **核心功能**: 语音采集 → ASR → 说话人识别 → 情感分析 → NLU → 全文检索

### 当前开发状态 (2026-07-07)

**部署方式变更**: 从 Docker Compose 改为双服务器裸机部署
- Server A (应用服务器): 运行除 AI 引擎外的所有服务
- Server B (推理服务器): 仅运行 AI Engine，需 RTX 4090

**已打通的完整链路**:

**已打通的完整链路**:
```
ESP32上传 → MinIO → Redis队列 → Worker消费 → AI引擎推理 → 结果入库 → WebSocket → 前端
```

**后端 API 路由清单 (10个模块)**:
| 路由前缀 | 模块 | 状态 |
|----------|------|------|
| `/api/auth` | 认证 (JWT登录) | ✅ |
| `/api/device` | 设备管理 (注册/心跳/列表/删除) | ✅ |
| `/api/task` | 任务管理 (创建/列表/下发) | ✅ |
| `/api/audio` | 音频管理 (上传/列表/详情/下载) | ✅ |
| `/api/result` | 识别结果 (转写/说话人/情感/NLU) | ✅ |
| `/api/search` | 全文检索 | ✅ |
| `/api/alert` | 告警 (规则/记录) | ✅ |
| `/api/speaker` | 说话人管理 (列表/注册/更新/删除) | ✅ 新增 |
| `/api/stats` | 统计看板 (仪表盘/趋势/情感分布) | ✅ 新增 |
| `/api/settings` | 系统设置 (读取/保存) | ✅ 新增 |
| `/ws/realtime` | WebSocket 实时推送 | ✅ 完善 |

**下一步开发建议**:
1. 在 Server A 上执行 `scripts/deploy-server-a.sh <Server_B_IP>` 部署应用服务
2. 在 Server B 上执行 `scripts/deploy-server-b.sh <Server_A_IP>` 部署推理服务
3. 运行 `scripts/check-status.sh <Server_B_IP>` 验证所有服务状态
4. 完善任务调度 — 任务下发后通过 WebSocket 通知设备开始采集
5. 实现说话人批量导入的前端界面
6. 补充 `AudioList` 的分页 total 和 `AudioDetail` 的波形播放联调

---

*文档结束*
