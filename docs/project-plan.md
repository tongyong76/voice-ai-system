# 智能语音采集与AI识别系统 - 项目文档

> **创建日期**: 2026-07-04
> **最后更新**: 2026-07-22
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
- **RAG 知识库问答**：基于向量检索 + 本地 LLM 的语音内容智能问答

---

## 二、技术方案确认

### 2.1 部署环境

| 项目 | 决定 |
|------|------|
| GPU | RTX 4090 24GB |
| 推理方式 | 自有GPU服务器本地推理 |
| **部署方式** | **双服务器裸机部署 (弃用Docker)** |
| **Python 环境** | **Miniconda, conda 环境名 `voice`** |

**双服务器架构**:
- **Server A (192.168.31.45)**: Nginx + FastAPI + MySQL + Redis + MinIO
- **Server B (192.168.31.4)**: AI Engine (FunASR + CAM++ + emotion2vec + NLU)，RTX 4090

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
| 情感分析 | emotion2vec | 通过 funasr AutoModel 加载 |
| **文本向量化** | **text2vec-base-chinese** | 768维中文语义向量，sentence-transformers 加载 |
| **向量检索** | **FAISS (文本索引)** | 复用已有依赖，独立于说话人索引 |
| **LLM 问答** | **llama.cpp + Qwen2.5-7B-Instruct** | Q4_K_M 量化 (~5GB)，本地离线推理 |
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
│        Server A — 192.168.31.45 (应用服务器, 无GPU)       │
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
                                     http://192.168.31.4:8001
                                                  │
┌─────────────────────────────────────────────────┼───────┐
│          Server B — 192.168.31.4 (推理服务器, RTX 4090)   │
│                                                  ▼       │
│  ┌──────────────────────────────────────────────────┐   │
│  │              AI Engine (FastAPI :8001)             │   │
│  │  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────────┐│   │
│  │  │FunASR    │ │ CAM++    │ │emotion │ │  NLU   ││   │
│  │  │Paraformer│ │ 说话人    │ │2vec    │ │ 关键词  ││   │
│  │  └──────────┘ └──────────┘ └────────┘ └────────┘│   │
│  │  ┌──────────┐ ┌──────────────────────────────────┐│   │
│  │  │text2vec  │ │ RAG Pipeline (检索+生成)          ││   │
│  │  │文本向量化 │ │ FAISS文本索引 + llama.cpp LLM     ││   │
│  │  └──────────┘ └──────────────────────────────────┘│   │
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

┌─────────────────────────────────────────────────────────┐
│              ESP32S3 设备 (200台)                        │
│   麦克风采集 → Opus编码 → Wi-Fi HTTP上传                  │
│   目标: http://192.168.31.45:8000/api/audio/upload       │
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

# RAG 知识库问答
POST   /api/rag/query               # RAG 问答 (代理到 AI Engine)
POST   /api/rag/index               # 触发转写文本索引
GET    /api/rag/stats               # 索引统计 (文档数、索引大小)

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
| `pipeline/emotion_engine.py` | emotion2vec 情感分析 (funasr AutoModel 加载) |
| `pipeline/nlu_engine.py` | NLU关键词/意图提取 |
| `pipeline/pipeline.py` | 推理流水线串联 |
| `pipeline/text_embedder.py` | **text2vec 中文文本向量化 (768维)** |
| `speaker_db/search.py` | FAISS 说话人检索 (10万规模) |
| `speaker_db/enroll.py` | 声纹注册 |
| `rag/vector_store.py` | **FAISS 文本向量存储 (转写知识库)** |
| `rag/retriever.py` | **向量检索器：query → Top-K** |
| `rag/generator.py` | **llama.cpp 客户端 → LLM 生成回答** |
| `rag/config.py` | **RAG 配置 (LLM、Top-K、阈值)** |
| `main.py` | FastAPI入口 (端口8001，从项目根目录以 `ai_engine.main:app` 启动) |

**RTX 4090 推理能力**:

| 模型 | 显存占用 | 用途 |
|------|----------|------|
| SenseVoice (ASR+情感) | ~2.0GB | 语音识别 + 情感分析 |
| CAM++ | ~0.8GB | 说话人识别 |
| text2vec-base-chinese | ~0.5GB | 文本向量化 (RAG) |
| Qwen2.5-7B Q4_K_M (llama.cpp) | ~5.0GB | LLM 问答生成 (RAG) |
| **总计** | **~8.3GB** | 24GB 裕量充足，可满足200台并发 |

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
| **RAGQuery** | **语音知识库问答 (基于向量检索 + LLM)** |

### 4.5 数据库设计

**核心表**:

| 表名 | 说明 |
|------|------|
| `devices` | 设备表 |
| `tasks` | 采集任务表 |
| `audio_records` | 音频记录表 |
| `transcripts` | ASR转写结果表 (含 `rag_indexed` 字段标记是否已入向量库) |
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
- [x] `services/inference_worker.py` — **新建**，后台 Worker 消费 Redis 队列，调用 AI 引擎 `/inference` 接口
- [x] `main.py` — lifespan 中启动 Worker 和 WebSocket 订阅者两个后台任务
- [x] `core/redis.py` — 新增 `redis_subscriber_task()`，订阅 Redis 频道广播到 WebSocket 客户端

**新增后端 API 端点**:
- [x] `api/v1/stats.py` — Dashboard 统计 API
- [x] `api/v1/speaker.py` — 说话人管理 API
- [x] `api/v1/settings.py` — 系统设置 API

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
- [x] MinIO — 健康检查通过
- [x] FastAPI 后端 — `{"status":"ok"}`
- [x] Nginx 前端 — HTTP 200

**前端构建修复**:
- [x] `vue-tsc` 兼容性问题 — 跳过类型检查，直接 `vite build`
- [x] ECharts 按需引入 — Dashboard.vue 改用 `echarts/core` 按需加载

### 5.4 2026-07-11 开发进展

**Server B 部署完成** ✅:
- [x] NVIDIA 驱动安装 (595.71.05, CUDA 13.2)
- [x] PyTorch 2.5.1+cu124 安装，CUDA 验证通过
- [x] AI 引擎依赖安装 (funasr, modelscope, faiss-cpu)
- [x] 三个模型全部下载到本地缓存:
  - FunASR Paraformer-zh (ASR)
  - CAM++ (说话人识别)
  - emotion2vec (情感分析)
- [x] AI Engine 手动启动测试通过，三个模型全部加载到 CUDA
- [x] Systemd 服务配置完成，`curl http://localhost:8001/health` 返回 `{"status":"ok"}`
- [x] Server A → Server B 连通性验证通过 (`curl http://192.168.31.4:8001/health`)

**Server B 环境配置调整**:
- [x] 使用 Miniconda conda 环境 `voice`（非 venv）
- [x] `ai_engine/requirements.txt` 版本锁定解除（torch/faiss-gpu/funasr/modelscope）
- [x] `faiss-gpu` 改为 `faiss-cpu`（避免 CUDA 版本冲突）
- [x] AI Engine 启动命令: `uvicorn ai_engine.main:app`（从项目根目录运行，非相对导入）
- [x] emotion2vec 改用 `funasr.AutoModel` 加载（modelscope pipeline 有版本兼容问题）

**IP 地址确认**:
| 服务器 | IP | 用途 |
|--------|-----|------|
| Server A (G-ITX) | 192.168.31.45 | 应用服务器 |
| Server B (WORKSERVER) | 192.168.31.4 | 推理服务器 |

### 5.5 部署踩坑记录

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| Systemd `status=200/CHDIR` | heredoc 变量被展开为空路径 | 使用 `<<'EOF'`（单引号） |
| passlib bcrypt 报错 | bcrypt>=4.1 与 passlib 不兼容 | `pip install bcrypt==4.0.1` |
| Nginx 端口 80 占用 | Apache 占用 | `sudo systemctl stop apache2` |
| Nginx 500 Permission denied | www-data 无权访问 home 目录 | `chmod 755 /home/guwenjun` |
| MinIO AccessDenied | Snap 版路径不同 | `snap disable minio`，用独立二进制 |
| vue-tsc 构建失败 | TypeScript 版本不兼容 | `npx vite build` 跳过类型检查 |
| `@tsconfig/node24` 缺失 | Node 24 tsconfig 包未安装 | `pnpm add -D @tsconfig/node24` |
| faiss-gpu 版本冲突 | 与 torch CUDA 版本不兼容 | 改用 `faiss-cpu` |
| modelscope pipeline 报错 | emotion2vec 注册表不匹配 | 改用 `funasr.AutoModel` 加载 |
| AI Engine 相对导入失败 | `uvicorn main:app` 无法解析相对导入 | 从项目根目录运行 `uvicorn ai_engine.main:app` |

### 5.6 文件清单

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
- `scripts/deploy-server-b.sh` - Server B 部署脚本 (Miniconda)
- `scripts/check-status.sh` - 服务状态检查脚本
- `scripts/init-db.sql` - 数据库初始化

### 5.7 RAG 知识库问答功能设计 (2026-07-22)

**目标**: 将所有转写文本构建为向量知识库，支持语义搜索 + LLM 智能问答。

**技术选型**:

| 组件 | 方案 | 说明 |
|------|------|------|
| Embedding 模型 | text2vec-base-chinese | 768维中文语义向量，~400MB |
| 向量存储 | FAISS (独立索引) | 复用已有依赖，与说话人索引独立 |
| LLM | llama.cpp + Qwen2.5-7B-Instruct | Q4_K_M 量化 (~5GB)，本地离线 |
| LLM API | llama.cpp server :8080 | OpenAI 兼容 API |

**GPU 显存预算 (RTX 4090 24GB)**:

| 模型 | 显存 |
|------|------|
| SenseVoice (ASR+情感) | ~2.0 GB |
| CAM++ (说话人) | ~0.8 GB |
| text2vec (文本向量化) | ~0.5 GB |
| Qwen2.5-7B Q4_K_M (LLM) | ~5.0 GB |
| **合计** | **~8.3 GB** |

**新增文件**:
- `ai_engine/pipeline/text_embedder.py` — text2vec 文本向量化引擎
- `ai_engine/rag/vector_store.py` — FAISS 文本向量存储
- `ai_engine/rag/retriever.py` — 向量检索器
- `ai_engine/rag/generator.py` — llama.cpp 客户端
- `ai_engine/rag/config.py` — RAG 配置
- `server/app/api/v1/rag.py` — Server A RAG 路由
- `web/src/api/rag.ts` — 前端 RAG API
- `web/src/views/RAGQuery.vue` — 问答页面
- `scripts/setup-llama-cpp.sh` — llama.cpp 编译安装脚本
- `scripts/download-llm.sh` — 下载 Qwen2.5-7B GGUF 模型
- `scripts/start-llama-server.sh` — llama-server 启动脚本

**AI Engine 新增端点**:

| 端点 | 方法 | 说明 |
|------|------|------|
| `/embed` | POST | 文本向量化 `{"texts": [...]}` → `{"embeddings": [...]}` |
| `/rag/query` | POST | RAG 问答 `{"query", "top_k}` → `{"answer", "sources"}` |
| `/rag/index` | POST | 索引转写 `{"transcript_ids": [...]}` → `{"indexed": N}` |
| `/rag/stats` | GET | 索引统计 `{"total_vectors", "index_size_mb"}` |

**索引策略**:
- 新音频推理完成后，Worker 自动调用 `/rag/index` 索引转写文本
- Transcript 表新增 `rag_indexed` (Boolean) 和 `rag_indexed_at` (DateTime) 字段
- 索引前检查 `rag_indexed`，已索引则跳过，避免重复
- 历史数据通过批量脚本一次性索引

**核心流程**:
```
索引: 音频推理完成 → Worker 调用 /rag/index → text2vec 向量化 → 存入 FAISS → 标记 rag_indexed=True

查询: 用户提问 → text2vec 向量化 → FAISS 检索 Top-K → 构建 Prompt → llama.cpp LLM → 生成回答
```

---

## 六、部署方案 (双服务器)

### 6.1 服务器信息

| 项目 | Server A (应用服务器) | Server B (推理服务器) |
|------|----------------------|----------------------|
| **主机名** | G-ITX | WORKSERVER |
| **IP** | 192.168.31.45 | 192.168.31.4 |
| **用途** | 前端 + 后端 + 存储 | AI推理 |
| **GPU** | 无 | RTX 4090 24GB |
| **OS** | Ubuntu 26.04 | Ubuntu 26.04 |
| **Python** | Miniconda, conda `voice` | Miniconda, conda `voice` |
| **驱动** | - | NVIDIA 595.71.05, CUDA 13.2 |

### 6.2 Server A 已验证配置

**服务状态** (2026-07-11):
```
✓ MySQL:      运行中 (10张表)
✓ Redis:      运行中 (PONG)
✓ MinIO:      运行中 (health live)
✓ FastAPI:    运行中 (health ok)
✓ Nginx:      运行中 (HTTP 200)
```

**后端 Systemd 服务**:
```
ExecStart=/home/guwenjun/miniconda3/envs/voice/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
WorkingDirectory=/home/guwenjun/code/voice-ai-system/server
```

### 6.3 Server B 已验证配置

**服务状态** (2026-07-11):
```
✓ AI Engine:  运行中 (health ok)
✓ GPU:        RTX 4090, CUDA True
✓ 模型加载:   ASR + Speaker + Emotion 全部加载到 CUDA
✓ 内存占用:   ~2.8GB
```

**AI Engine Systemd 服务**:
```
ExecStart=/home/guwenjun/miniconda3/envs/voice/bin/uvicorn ai_engine.main:app --host 0.0.0.0 --port 8001
WorkingDirectory=/home/guwenjun/code/voice-ai-system
Environment="CUDA_VISIBLE_DEVICES=0"
```

**环境变量** (`ai_engine/.env`):
```
MINIO_ENDPOINT=192.168.31.45:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=voice-audio
CUDA_VISIBLE_DEVICES=0
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
| llama.cpp Server | 8080 | Server B | ❌ (内网, 仅AI Engine调用) |

### 6.5 防火墙配置

**Server A**:
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow from 192.168.31.4 to any port 9000  # MinIO
sudo ufw enable
```

**Server B**:
```bash
sudo ufw allow from 192.168.31.45 to any port 8001  # AI Engine
sudo ufw allow from 127.0.0.1 to any port 8080      # llama.cpp (本机)
sudo ufw enable
```

---

## 七、待办事项

### 7.1 高优先级 ✅ 已完成

- [x] 测试后端API是否正常启动 (2026-07-06)
- [x] 完善前端WebSocket实时推送功能 (2026-07-06)
- [x] 添加音频上传后自动触发推理的逻辑 (2026-07-06)
- [x] 添加数据统计和报表功能 (2026-07-06)
- [x] Server A 双服务器部署验证 (2026-07-08)
- [x] 前端构建优化 — ECharts 按需引入 (2026-07-08)
- [x] Server B 推理服务器部署 (2026-07-11)
- [x] AI Engine 三个模型加载验证 (2026-07-11)
- [x] Server A ↔ Server B 连通性验证 (2026-07-11)

### 7.2 中优先级

- [ ] 端到端集成测试 — 上传音频 → AI 推理 → 结果入库 → 前端展示
- [ ] 完善任务调度系统 — 任务下发后通知设备执行采集
- [ ] 实现说话人库的批量导入功能 (后端 bulk_enroll API 已有，前端待开发)
- [ ] 音频详情页 AudioDetail — WaveSurfer 波形播放 + AI 结果展示联调
- [ ] 前端分页 total 计数 — AudioList 的 total 目前写死 100

### 7.3 RAG 知识库问答 (规划中)

- [ ] Phase 1: llama.cpp 编译安装 + Qwen2.5-7B GGUF 模型下载
- [ ] Phase 1: Transcript 表新增 `rag_indexed`/`rag_indexed_at` 字段
- [ ] Phase 2: `text_embedder.py` — text2vec 文本向量化引擎
- [ ] Phase 2: `vector_store.py` — FAISS 文本向量存储
- [ ] Phase 2: AI Engine `/embed` + `/rag/index` 端点
- [ ] Phase 2: Worker 推理完成后自动索引转写文本
- [ ] Phase 3: `retriever.py` — 向量检索器
- [ ] Phase 3: `generator.py` — llama.cpp 客户端
- [ ] Phase 3: AI Engine `/rag/query` 端点
- [ ] Phase 3: Server A `/api/rag/query` 代理
- [ ] Phase 4: `RAGQuery.vue` — 前端问答页面
- [ ] Phase 4: 历史数据批量索引脚本
- [ ] Phase 5: 对话历史、过滤条件、增量更新优化

### 7.4 低优先级

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
| Python | 3.11 (Miniconda) |
| FastAPI | 0.109.0 |
| PyTorch | 2.5.1+cu124 |
| FunASR | 1.3.14 |
| FAISS | 1.14.3 (cpu) |
| **text2vec-base-chinese** | **shibing624/text2vec-base-chinese (sentence-transformers)** |
| **llama.cpp** | **latest (CUDA build)** |
| **Qwen2.5-7B-Instruct** | **Q4_K_M GGUF 量化** |
| Vue | 3.5 |
| Element Plus | 2.5 |
| MySQL | 8.0 |
| Redis | 8.0 |
| MinIO | latest |
| NVIDIA Driver | 595.71.05 |

### 8.2 参考文档

- FunASR: https://github.com/modelscope/FunASR
- CAM++: https://modelscope.cn/models/iic/speech_campplus_sv_zh-cn_16k-common
- emotion2vec: https://modelscope.cn/models/iic/emotion2vec_base_finetuned
- FAISS: https://github.com/facebookresearch/faiss
- text2vec-base-chinese: https://huggingface.co/shibing624/text2vec-base-chinese
- llama.cpp: https://github.com/ggerganov/llama.cpp
- Qwen2.5-7B-Instruct-GGUF: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF
- ESP-IDF: https://docs.espressif.com/projects/esp-idf/

---

*文档结束*
