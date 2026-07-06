<template>
  <div class="audio-list">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>音频列表</span>
        </div>
      </template>

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
        <el-select v-model="filters.inference_status" placeholder="推理状态" clearable style="width: 120px">
          <el-option label="待处理" value="pending" />
          <el-option label="处理中" value="processing" />
          <el-option label="已完成" value="completed" />
          <el-option label="失败" value="failed" />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 300px"
        />
        <el-button type="primary" @click="fetchAudioList">查询</el-button>
      </div>

      <!-- Audio Table -->
      <el-table :data="audioList" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="device_id" label="设备" width="100" />
        <el-table-column prop="upload_time" label="上传时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.upload_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="duration_ms" label="时长" width="100">
          <template #default="{ row }">
            {{ formatDuration(row.duration_ms) }}
          </template>
        </el-table-column>
        <el-table-column prop="file_size" label="大小" width="100">
          <template #default="{ row }">
            {{ formatSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="format" label="格式" width="80" />
        <el-table-column prop="inference_status" label="推理状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.inference_status)">
              {{ row.inference_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="goToDetail(row)">详情</el-button>
            <el-button text @click="handleDownload(row)">下载</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- Pagination -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @size-change="fetchAudioList"
          @current-change="fetchAudioList"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import { audioApi, type AudioRecord } from '@/api/audio'
import { deviceApi, type Device } from '@/api/device'

const router = useRouter()
const audioList = ref<AudioRecord[]>([])
const devices = ref<Device[]>([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const dateRange = ref<[Date, Date] | null>(null)

const filters = reactive({
  device_id: undefined as number | undefined,
  inference_status: undefined as string | undefined,
})

const formatTime = (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss')

const formatDuration = (ms: number | null) => {
  if (!ms) return '-'
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  return `${minutes}:${(seconds % 60).toString().padStart(2, '0')}`
}

const formatSize = (bytes: number | null) => {
  if (!bytes) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
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

const fetchAudioList = async () => {
  loading.value = true
  try {
    const params: any = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
      ...filters,
    }
    if (dateRange.value) {
      params.start_time = dateRange.value[0].toISOString()
      params.end_time = dateRange.value[1].toISOString()
    }
    audioList.value = await audioApi.list(params)
    // TODO: Get total from API
    total.value = audioList.value.length > 0 ? 100 : 0
  } catch (error) {
    // Error handled
  } finally {
    loading.value = false
  }
}

const fetchDevices = async () => {
  try {
    devices.value = await deviceApi.list()
  } catch (error) {
    // Error handled
  }
}

const goToDetail = (audio: AudioRecord) => {
  router.push(`/audio/${audio.id}`)
}

const handleDownload = async (audio: AudioRecord) => {
  try {
    const { url } = await audioApi.download(audio.id)
    window.open(url, '_blank')
  } catch (error) {
    // Error handled
  }
}

onMounted(() => {
  fetchAudioList()
  fetchDevices()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filters {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
