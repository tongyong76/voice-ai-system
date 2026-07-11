# 音频上传测试指南

> 终端设备（ESP32S3）尚未实现前，使用以下方法手动上传音频进行测试。

---

## 方法一：Python 脚本（推荐）

### 安装依赖

```bash
pip install requests
```

### 使用方法

```bash
# 基本用法
python scripts/test-audio-upload.py --audio /path/to/your/audio.wav

# 指定服务器地址（远程服务器）
python scripts/test-audio-upload.py --audio /path/to/audio.wav --server http://192.168.1.100:8000

# 等待推理完成并查看结果
python scripts/test-audio-upload.py --audio /path/to/audio.wav --wait

# 指定设备编码
python scripts/test-audio-upload.py --audio /path/to/audio.wav --device MY_DEVICE_001
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--audio` | 音频文件路径（必填） | - |
| `--device` | 测试设备编码 | `TEST_DEVICE_001` |
| `--device-name` | 设备名称 | `测试设备 + 编码` |
| `--server` | 服务器地址 | `http://localhost:8000` |
| `--wait` | 等待推理完成 | `false` |
| `--username` | 登录用户名 | `admin` |
| `--password` | 登录密码 | `admin123` |

---

## 方法二：cURL 命令

### 1. 登录获取 Token

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

响应示例：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. 注册测试设备

```bash
# 将 <TOKEN> 替换为上一步获取的 token
curl -X POST http://localhost:8000/api/device/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "device_code": "TEST_DEVICE_001",
    "name": "测试设备 001",
    "location": "测试环境",
    "firmware_version": "test-1.0.0"
  }'
```

### 3. 上传音频文件

```bash
# 上传音频文件
curl -X POST "http://localhost:8000/api/audio/upload?device_code=TEST_DEVICE_001" \
  -F "file=@/path/to/your/audio.wav"
```

响应示例：
```json
{
  "id": 1,
  "file_path": "audio/TEST_DEVICE_001/20260708/abc123.wav",
  "status": "uploaded"
}
```

### 4. 查询推理状态

```bash
# 查询音频详情（包含推理状态）
curl -X GET http://localhost:8000/api/audio/1 \
  -H "Authorization: Bearer <TOKEN>"
```

### 5. 获取转写结果

```bash
# 获取 ASR 转写结果
curl -X GET http://localhost:8000/api/result/transcript/1 \
  -H "Authorization: Bearer <TOKEN>"

# 获取说话人识别结果
curl -X GET http://localhost:8000/api/result/speaker/1 \
  -H "Authorization: Bearer <TOKEN>"

# 获取情感分析结果
curl -X GET http://localhost:8000/api/result/emotion/1 \
  -H "Authorization: Bearer <TOKEN>"
```

---

## 方法三：Postman / Apifox

### 请求配置

**1. 登录**
- Method: `POST`
- URL: `http://localhost:8000/api/auth/login`
- Body (JSON):
  ```json
  {
    "username": "admin",
    "password": "admin123"
  }
  ```

**2. 注册设备**
- Method: `POST`
- URL: `http://localhost:8000/api/device/register`
- Headers: `Authorization: Bearer <TOKEN>`
- Body (JSON):
  ```json
  {
    "device_code": "TEST_DEVICE_001",
    "name": "测试设备 001"
  }
  ```

**3. 上传音频**
- Method: `POST`
- URL: `http://localhost:8000/api/audio/upload?device_code=TEST_DEVICE_001`
- Body: `form-data`
  - Key: `file`
  - Type: `File`
  - Value: 选择音频文件

---

## 测试流程图

```
┌─────────────────────────────────────────────────────────┐
│                    测试流程                               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. 登录获取 Token                                       │
│     POST /api/auth/login                                │
│                 ↓                                       │
│  2. 注册测试设备                                         │
│     POST /api/device/register                           │
│                 ↓                                       │
│  3. 上传音频文件                                         │
│     POST /api/audio/upload?device_code=xxx              │
│                 ↓                                       │
│  4. 系统自动处理                                         │
│     ├─ 保存到 MinIO                                     │
│     ├─ 写入 MySQL                                       │
│     └─ 推送到 Redis 队列                                │
│                 ↓                                       │
│  5. Worker 消费队列                                      │
│     └─ 调用 AI 引擎推理                                 │
│                 ↓                                       │
│  6. 查看结果                                             │
│     ├─ GET /api/result/transcript/{id}  # 转写          │
│     ├─ GET /api/result/speaker/{id}     # 说话人        │
│     └─ GET /api/result/emotion/{id}     # 情感          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 音频文件要求

| 项目 | 要求 |
|------|------|
| 格式 | WAV, MP3, OGG, OPUS 等常见格式 |
| 采样率 | 16kHz（推荐） |
| 时长 | 建议 10-60 秒 |
| 大小 | < 100MB |
| 内容 | 中文语音（系统主要支持中文识别） |

---

## 常见问题

### Q1: 上传失败，提示 "Device not found"
**原因**: 设备未注册
**解决**: 先调用设备注册接口

### Q2: 上传失败，提示 "Device already registered"
**原因**: 设备编码已存在
**解决**: 使用其他设备编码，或直接使用已注册的设备编码

### Q3: 推理状态一直是 "pending"
**原因**: AI 引擎（Server B）未启动或无法连接
**解决**:
1. 检查 Server B 是否运行: `curl http://SERVER_B_IP:8001/health`
2. 检查 Server A 的 `.env` 中 `AI_ENGINE_URL` 配置是否正确
3. 查看 Worker 日志: `journalctl -u voice-server -f`

### Q4: 推理失败
**原因**: 可能是音频格式不支持或 AI 引擎错误
**解决**:
1. 检查音频文件是否正常
2. 查看 AI 引擎日志: `journalctl -u voice-ai-engine -f`
3. 确保音频是 16kHz 采样率

### Q5: 无法连接到服务器
**原因**: 服务未启动或网络不通
**解决**:
1. 检查服务状态: `scripts/check-status.sh`
2. 检查防火墙: `sudo ufw status`
3. 确认端口 8000 是否监听: `netstat -tlnp | grep 8000`

---

## 快速测试命令

```bash
# 一键测试（需要先安装 requests）
# 1. 准备一个测试音频文件
# 2. 运行以下命令

# 本地测试
python scripts/test-audio-upload.py --audio test.wav --wait

# 远程服务器测试
python scripts/test-audio-upload.py \
  --audio test.wav \
  --server http://YOUR_SERVER_IP:8000 \
  --wait
```

---

## 生成测试音频

如果没有现成的音频文件，可以用以下方法生成：

### 方法 1: 使用 ffmpeg 生成静音音频

```bash
# 生成 10 秒的静音 WAV 文件
ffmpeg -f lavfi -i anullsrc=r=16000:cl=mono -t 10 -q:a 9 -acodec pcm_s16le test_silence.wav
```

### 方法 2: 使用 Python 生成测试音频

```python
import numpy as np
from scipy.io import wavfile

# 生成 16kHz 采样率，5 秒的正弦波
sample_rate = 16000
duration = 5  # 秒
frequency = 440  # Hz (A4 音符)

t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
audio_data = np.sin(2 * np.pi * frequency * t) * 32767
audio_data = audio_data.astype(np.int16)

wavfile.write('test_tone.wav', sample_rate, audio_data)
print("已生成 test_tone.wav")
```

### 方法 3: 录制真实语音

```bash
# 使用 arecord 录制 (Linux)
arecord -f S16_LE -r 16000 -c 1 -d 10 test_voice.wav

# 使用 sox 录制
rec -r 16000 -c 1 test_voice.wav trim 0 10
```

---

*文档更新时间: 2026-07-08*
