<template>
  <div class="task-manage">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>任务管理</span>
          <el-button type="primary" @click="showCreateDialog = true">
            <el-icon><Plus /></el-icon>
            创建任务
          </el-button>
        </div>
      </template>

      <!-- Task Table -->
      <el-table :data="tasks" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="任务名称" width="200" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getTaskStatusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="目标设备" width="200">
          <template #default="{ row }">
            {{ formatDeviceIds(row.target_device_ids) }}
          </template>
        </el-table-column>
        <el-table-column prop="scheduled_at" label="计划时间" width="180">
          <template #default="{ row }">
            {{ row.scheduled_at ? formatTime(row.scheduled_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'pending'"
              text
              type="primary"
              @click="handleDispatch(row)"
            >
              下发
            </el-button>
            <el-button text @click="viewDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Create Task Dialog -->
    <el-dialog v-model="showCreateDialog" title="创建任务" width="600px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="任务名称" required>
          <el-input v-model="createForm.name" />
        </el-form-item>
        <el-form-item label="任务描述">
          <el-input v-model="createForm.description" type="textarea" />
        </el-form-item>
        <el-form-item label="目标设备" required>
          <el-select
            v-model="createForm.target_device_ids"
            multiple
            placeholder="选择设备"
            style="width: 100%"
          >
            <el-option label="全部设备" :value="['all']" />
            <el-option
              v-for="device in devices"
              :key="device.id"
              :label="`${device.name || device.device_code}`"
              :value="device.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="计划时间">
          <el-date-picker
            v-model="createForm.scheduled_at"
            type="datetime"
            placeholder="选择时间"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import { taskApi, type Task } from '@/api/task'
import { deviceApi, type Device } from '@/api/device'

const tasks = ref<Task[]>([])
const devices = ref<Device[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)

const createForm = ref({
  name: '',
  description: '',
  target_device_ids: [] as (number | string)[],
  scheduled_at: '',
})

const formatTime = (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss')

const formatDeviceIds = (ids: number[] | string[] | null) => {
  if (!ids) return '-'
  if (ids.includes('all')) return '全部设备'
  return `${ids.length} 台设备`
}

const getTaskStatusType = (status: string) => {
  const map: Record<string, string> = {
    pending: 'info',
    dispatched: 'warning',
    running: '',
    completed: 'success',
    failed: 'danger',
  }
  return map[status] || 'info'
}

const fetchTasks = async () => {
  loading.value = true
  try {
    tasks.value = await taskApi.list()
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

const handleCreate = async () => {
  if (!createForm.value.name) {
    ElMessage.warning('请输入任务名称')
    return
  }
  if (createForm.value.target_device_ids.length === 0) {
    ElMessage.warning('请选择目标设备')
    return
  }
  try {
    await taskApi.create(createForm.value)
    ElMessage.success('创建成功')
    showCreateDialog.value = false
    createForm.value = { name: '', description: '', target_device_ids: [], scheduled_at: '' }
    fetchTasks()
  } catch (error) {
    // Error handled
  }
}

const handleDispatch = async (task: Task) => {
  try {
    await taskApi.dispatch(task.id)
    ElMessage.success('任务已下发')
    fetchTasks()
  } catch (error) {
    // Error handled
  }
}

const viewDetail = (task: Task) => {
  // TODO: Show task detail dialog
  ElMessage.info('功能开发中')
}

onMounted(() => {
  fetchTasks()
  fetchDevices()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
