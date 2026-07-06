<template>
  <div class="dashboard">
    <!-- Stats Cards -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #409eff">
            <el-icon :size="28"><Monitor /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.onlineDevices }}</div>
            <div class="stat-label">在线设备</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #67c23a">
            <el-icon :size="28"><Headset /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.todayAudio }}</div>
            <div class="stat-label">今日采集(小时)</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #e6a23c">
            <el-icon :size="28"><User /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.speakerCount }}</div>
            <div class="stat-label">已注册说话人</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #f56c6c">
            <el-icon :size="28"><Bell /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.alertCount }}</div>
            <div class="stat-label">今日告警</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Charts Row -->
    <el-row :gutter="16" class="chart-row">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>采集趋势 (24小时)</template>
          <div ref="trendChart" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>情感分布</template>
          <div ref="emotionChart" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Recent Audio & Alerts -->
    <el-row :gutter="16">
      <el-col :span="14">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>最近音频</span>
              <el-button text type="primary" @click="$router.push('/audio')">查看全部</el-button>
            </div>
          </template>
          <el-table :data="recentAudio" style="width: 100%">
            <el-table-column prop="device_id" label="设备" width="80" />
            <el-table-column prop="upload_time" label="时间" width="180">
              <template #default="{ row }">
                {{ formatTime(row.upload_time) }}
              </template>
            </el-table-column>
            <el-table-column prop="duration_ms" label="时长" width="100">
              <template #default="{ row }">
                {{ formatDuration(row.duration_ms) }}
              </template>
            </el-table-column>
            <el-table-column prop="inference_status" label="状态">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.inference_status)">
                  {{ row.inference_status }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>最近告警</span>
              <el-button text type="primary" @click="$router.push('/alerts')">查看全部</el-button>
            </div>
          </template>
          <div class="alert-list">
            <div v-for="alert in recentAlerts" :key="alert.id" class="alert-item">
              <el-icon :size="16" color="#f56c6c"><WarningFilled /></el-icon>
              <span class="alert-text">{{ alert.message }}</span>
              <span class="alert-time">{{ formatTime(alert.time) }}</span>
            </div>
            <el-empty v-if="recentAlerts.length === 0" description="暂无告警" />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import * as echarts from 'echarts'
import dayjs from 'dayjs'

const stats = reactive({
  onlineDevices: 0,
  todayAudio: 0,
  speakerCount: 0,
  alertCount: 0,
})

const recentAudio = ref([])
const recentAlerts = ref([])

const trendChart = ref<HTMLElement>()
const emotionChart = ref<HTMLElement>()

const formatTime = (time: string) => dayjs(time).format('MM-DD HH:mm')
const formatDuration = (ms: number) => {
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  return `${minutes}:${(seconds % 60).toString().padStart(2, '0')}`
}

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    pending: 'info',
    processing: 'warning',
    completed: 'success',
    failed: 'danger',
  }
  return map[status] || 'info'
}

const initTrendChart = () => {
  if (!trendChart.value) return
  const chart = echarts.init(trendChart.value)
  const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: hours },
    yAxis: { type: 'value', name: '小时' },
    series: [{
      data: Array.from({ length: 24 }, () => Math.floor(Math.random() * 100)),
      type: 'line',
      smooth: true,
      areaStyle: { opacity: 0.3 },
    }],
  })
}

const initEmotionChart = () => {
  if (!emotionChart.value) return
  const chart = echarts.init(emotionChart.value)
  chart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: [
        { value: 45, name: '中性' },
        { value: 25, name: '积极' },
        { value: 15, name: '消极' },
        { value: 10, name: '愤怒' },
        { value: 5, name: '其他' },
      ],
    }],
  })
}

onMounted(() => {
  // TODO: Fetch real data
  stats.onlineDevices = 156
  stats.todayAudio = 1280
  stats.speakerCount = 85420
  stats.alertCount = 12

  initTrendChart()
  initEmotionChart()
})
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stats-row .stat-card {
  display: flex;
  align-items: center;
  padding: 20px;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #333;
}

.stat-label {
  font-size: 14px;
  color: #999;
  margin-top: 4px;
}

.chart-container {
  height: 300px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alert-list {
  max-height: 300px;
  overflow-y: auto;
}

.alert-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}

.alert-text {
  flex: 1;
  font-size: 14px;
}

.alert-time {
  font-size: 12px;
  color: #999;
}
</style>
