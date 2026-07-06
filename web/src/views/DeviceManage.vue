<template>
  <div class="device-manage">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>设备管理</span>
          <el-button type="primary" @click="showAddDialog = true">
            <el-icon><Plus /></el-icon>
            添加设备
          </el-button>
        </div>
      </template>

      <!-- Filters -->
      <div class="filters">
        <el-select v-model="statusFilter" placeholder="设备状态" clearable style="width: 120px">
          <el-option label="在线" value="online" />
          <el-option label="离线" value="offline" />
          <el-option label="忙碌" value="busy" />
          <el-option label="错误" value="error" />
        </el-select>
        <el-button @click="fetchDevices">刷新</el-button>
      </div>

      <!-- Device Table -->
      <el-table :data="devices" style="width: 100%" v-loading="loading">
        <el-table-column prop="device_code" label="设备编码" width="150" />
        <el-table-column prop="name" label="设备名称" width="150" />
        <el-table-column prop="location" label="位置" width="200" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" effect="dark">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="firmware_version" label="固件版本" width="120" />
        <el-table-column prop="last_heartbeat" label="最后心跳" width="180">
          <template #default="{ row }">
            {{ row.last_heartbeat ? formatTime(row.last_heartbeat) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="last_upload" label="最后上传" width="180">
          <template #default="{ row }">
            {{ row.last_upload ? formatTime(row.last_upload) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button text type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Add Device Dialog -->
    <el-dialog v-model="showAddDialog" title="添加设备" width="500px">
      <el-form :model="addForm" label-width="100px">
        <el-form-item label="设备编码" required>
          <el-input v-model="addForm.device_code" placeholder="ESP32 MAC地址" />
        </el-form-item>
        <el-form-item label="设备名称">
          <el-input v-model="addForm.name" placeholder="可选" />
        </el-form-item>
        <el-form-item label="位置">
          <el-input v-model="addForm.location" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="handleAdd">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import { deviceApi, type Device } from '@/api/device'

const devices = ref<Device[]>([])
const loading = ref(false)
const statusFilter = ref('')
const showAddDialog = ref(false)

const addForm = ref({
  device_code: '',
  name: '',
  location: '',
})

const formatTime = (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss')

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    online: 'success',
    offline: 'info',
    busy: 'warning',
    error: 'danger',
  }
  return map[status] || 'info'
}

const fetchDevices = async () => {
  loading.value = true
  try {
    devices.value = await deviceApi.list({ status: statusFilter.value || undefined })
  } catch (error) {
    // Error handled by interceptor
  } finally {
    loading.value = false
  }
}

const handleAdd = async () => {
  if (!addForm.value.device_code) {
    ElMessage.warning('请输入设备编码')
    return
  }
  try {
    await deviceApi.create(addForm.value)
    ElMessage.success('添加成功')
    showAddDialog.value = false
    addForm.value = { device_code: '', name: '', location: '' }
    fetchDevices()
  } catch (error) {
    // Error handled by interceptor
  }
}

const handleDelete = async (device: Device) => {
  await ElMessageBox.confirm('确定删除该设备？', '确认')
  try {
    await deviceApi.delete(device.id)
    ElMessage.success('删除成功')
    fetchDevices()
  } catch (error) {
    // Error handled by interceptor
  }
}

watch(statusFilter, () => fetchDevices())

onMounted(() => fetchDevices())
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
}
</style>
