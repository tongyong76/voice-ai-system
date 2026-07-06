<template>
  <div class="search-page">
    <el-card shadow="hover">
      <template #header>
        <span>全文检索</span>
      </template>

      <!-- Search Input -->
      <div class="search-bar">
        <el-input
          v-model="searchQuery"
          placeholder="输入关键词搜索转写文本..."
          size="large"
          clearable
          @keyup.enter="handleSearch"
        >
          <template #append>
            <el-button :icon="SearchIcon" @click="handleSearch" />
          </template>
        </el-input>
      </div>

      <!-- Filters -->
      <div class="filters">
        <el-select v-model="filters.device_id" placeholder="设备" clearable style="width: 150px">
          <el-option
            v-for="device in devices"
            :key="device.id"
            :label="device.name || device.device_code"
            :value="device.id"
          />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 300px"
        />
      </div>

      <!-- Results -->
      <div v-if="searched" class="results">
        <div class="results-header">
          找到 <strong>{{ results.length }}</strong> 条结果
        </div>
        <div v-for="item in results" :key="item.transcript_id" class="result-item" @click="goToAudio(item.audio_id)">
          <div class="result-text" v-html="highlightText(item.text)"></div>
          <div class="result-meta">
            <span>音频ID: {{ item.audio_id }}</span>
            <el-button text type="primary" size="small">查看详情</el-button>
          </div>
        </div>
        <el-empty v-if="results.length === 0" description="未找到匹配结果" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search as SearchIcon } from '@element-plus/icons-vue'
import { deviceApi, type Device } from '@/api/device'
import request from '@/api/request'

const router = useRouter()
const searchQuery = ref('')
const searched = ref(false)
const results = ref<Array<{ transcript_id: number; audio_id: number; text: string }>>([])
const devices = ref<Device[]>([])
const dateRange = ref<[Date, Date] | null>(null)

const filters = ref({
  device_id: undefined as number | undefined,
})

const highlightText = (text: string) => {
  if (!searchQuery.value) return text
  const regex = new RegExp(`(${searchQuery.value})`, 'gi')
  return text.replace(regex, '<mark>$1</mark>')
}

const handleSearch = async () => {
  if (!searchQuery.value.trim()) return

  try {
    const params: any = {
      q: searchQuery.value,
      ...filters.value,
    }
    if (dateRange.value) {
      params.start_time = dateRange.value[0].toISOString()
      params.end_time = dateRange.value[1].toISOString()
    }
    results.value = await request.get('/search/transcript', { params })
    searched.value = true
  } catch (error) {
    // Error handled
  }
}

const goToAudio = (audioId: number) => {
  router.push(`/audio/${audioId}`)
}

const fetchDevices = async () => {
  try {
    devices.value = await deviceApi.list()
  } catch (error) {
    // Error handled
  }
}

onMounted(() => fetchDevices())
</script>

<style scoped>
.search-bar {
  margin-bottom: 16px;
}

.filters {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.results-header {
  margin-bottom: 16px;
  color: #666;
}

.result-item {
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.result-item:hover {
  background: #ecf5ff;
}

.result-text {
  font-size: 15px;
  line-height: 1.6;
  margin-bottom: 8px;
}

.result-text :deep(mark) {
  background: #ffd666;
  padding: 0 2px;
  border-radius: 2px;
}

.result-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #999;
}
</style>
