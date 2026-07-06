<template>
  <div class="realtime-monitor">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>实时监控</span>
          <div class="status-indicator">
            <span :class="['dot', connected ? 'connected' : 'disconnected']"></span>
            {{ connected ? '已连接' : '未连接' }}
          </div>
        </div>
      </template>

      <!-- Device Selector -->
      <div class="device-selector">
        <el-select
          v-model="selectedDevices"
          multiple
          placeholder="选择监控设备"
          style="width: 100%"
        >
          <el-option
            v-for="device in onlineDevices"
            :key="device.id"
            :label="`${device.name || device.device_code} (${device.status})`"
            :value="device.id"
          />
        </el-select>
      </div>

      <!-- Realtime Text Stream -->
      <div class="stream-container">
        <div v-for="msg in messages" :key="msg.id" class="stream-item">
          <div class="stream-header">
            <el-tag size="small">{{ msg.deviceName }}</el-tag>
            <span class="stream-time">{{ formatTime(msg.timestamp) }}</span>
          </div>
          <div class="stream-text">{{ msg.text }}</div>
          <div class="stream-meta">
            <el-tag v-if="msg.emotion" size="small" :type="getEmotionType(msg.emotion)">
              {{ msg.emotion }}
            </el-tag>
            <el-tag v-if="msg.speaker" size="small" type="info">
              {{ msg.speaker }}
            </el-tag>
          </div>
        </div>
        <el-empty v-if="messages.length === 0" description="等待实时数据..." />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import dayjs from 'dayjs'
import { deviceApi, type Device } from '@/api/device'

interface StreamMessage {
  id: number
  deviceId: number
  deviceName: string
  text: string
  emotion?: string
  speaker?: string
  timestamp: string
}

const onlineDevices = ref<Device[]>([])
const selectedDevices = ref<number[]>([])
const messages = ref<StreamMessage[]>([])
const connected = ref(false)

let ws: WebSocket | null = null
let msgId = 0

const formatTime = (time: string) => dayjs(time).format('HH:mm:ss')

const getEmotionType = (emotion: string) => {
  const map: Record<string, string> = {
    positive: 'success',
    negative: 'danger',
    neutral: 'info',
    angry: 'danger',
    happy: 'success',
    sad: 'warning',
  }
  return map[emotion] || 'info'
}

const connectWebSocket = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  ws = new WebSocket(`${protocol}//${window.location.host}/ws/realtime`)

  ws.onopen = () => {
    connected.value = true
    console.log('WebSocket connected')
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      messages.value.unshift({
        id: ++msgId,
        deviceId: data.device_id,
        deviceName: data.device_name || `Device ${data.device_id}`,
        text: data.text,
        emotion: data.emotion,
        speaker: data.speaker,
        timestamp: new Date().toISOString(),
      })
      // Keep only last 100 messages
      if (messages.value.length > 100) {
        messages.value.pop()
      }
    } catch (e) {
      console.error('Failed to parse message:', e)
    }
  }

  ws.onclose = () => {
    connected.value = false
    // Reconnect after 3 seconds
    setTimeout(connectWebSocket, 3000)
  }

  ws.onerror = () => {
    connected.value = false
  }
}

const fetchOnlineDevices = async () => {
  try {
    onlineDevices.value = await deviceApi.list({ status: 'online' })
  } catch (error) {
    // Error handled
  }
}

onMounted(() => {
  fetchOnlineDevices()
  connectWebSocket()
})

onUnmounted(() => {
  ws?.close()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot.connected {
  background: #67c23a;
}

.dot.disconnected {
  background: #f56c6c;
}

.device-selector {
  margin-bottom: 16px;
}

.stream-container {
  max-height: 600px;
  overflow-y: auto;
}

.stream-item {
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 12px;
}

.stream-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.stream-time {
  font-size: 12px;
  color: #999;
}

.stream-text {
  font-size: 16px;
  line-height: 1.6;
  margin-bottom: 8px;
}

.stream-meta {
  display: flex;
  gap: 8px;
}
</style>
