<template>
  <div class="speaker-manage">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>说话人库</span>
          <el-button type="primary" @click="showEnrollDialog = true">
            <el-icon><Plus /></el-icon>
            注册说话人
          </el-button>
        </div>
      </template>

      <!-- Stats -->
      <div class="stats">
        <el-statistic title="已注册说话人" :value="speakers.length" />
      </div>

      <!-- Speaker Table -->
      <el-table :data="speakers" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="姓名" width="150" />
        <el-table-column label="标签" width="200">
          <template #default="{ row }">
            <el-tag v-for="tag in row.tags" :key="tag" size="small" class="tag-item">
              {{ tag }}
            </el-tag>
            <span v-if="!row.tags || row.tags.length === 0">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button text type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Enroll Dialog -->
    <el-dialog v-model="showEnrollDialog" title="注册说话人" width="500px">
      <el-form :model="enrollForm" label-width="100px">
        <el-form-item label="姓名" required>
          <el-input v-model="enrollForm.name" />
        </el-form-item>
        <el-form-item label="标签">
          <el-select
            v-model="enrollForm.tags"
            multiple
            filterable
            allow-create
            placeholder="输入标签后回车"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="音频文件" required>
          <el-upload
            :auto-upload="false"
            :on-change="handleFileChange"
            :file-list="fileList"
            accept="audio/*"
            multiple
          >
            <el-button type="primary">选择文件</el-button>
            <template #tip>
              <div class="el-upload__tip">上传1-3段该说话人的音频样本</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEnrollDialog = false">取消</el-button>
        <el-button type="primary" :loading="enrolling" @click="handleEnroll">注册</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type UploadFile, type UploadFiles } from 'element-plus'
import dayjs from 'dayjs'
import { speakerApi, type Speaker } from '@/api/speaker'

const speakers = ref<Speaker[]>([])
const loading = ref(false)
const showEnrollDialog = ref(false)
const enrolling = ref(false)
const fileList = ref<UploadFiles>([])

const enrollForm = ref({
  name: '',
  tags: [] as string[],
  files: [] as File[],
})

const formatTime = (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss')

const handleFileChange = (file: UploadFile, uploadFiles: UploadFiles) => {
  fileList.value = uploadFiles
  enrollForm.value.files = uploadFiles.map(f => f.raw!).filter(Boolean)
}

const fetchSpeakers = async () => {
  loading.value = true
  try {
    speakers.value = await speakerApi.list()
  } catch (error) {
    // Error handled
  } finally {
    loading.value = false
  }
}

const handleEnroll = async () => {
  if (!enrollForm.value.name) {
    ElMessage.warning('请输入姓名')
    return
  }
  if (enrollForm.value.files.length === 0) {
    ElMessage.warning('请上传音频文件')
    return
  }

  enrolling.value = true
  try {
    await speakerApi.enroll({
      name: enrollForm.value.name,
      tags: enrollForm.value.tags,
      files: enrollForm.value.files,
    })
    ElMessage.success('注册成功')
    showEnrollDialog.value = false
    enrollForm.value = { name: '', tags: [], files: [] }
    fileList.value = []
    fetchSpeakers()
  } catch (error) {
    // Error handled
  } finally {
    enrolling.value = false
  }
}

const handleDelete = async (speaker: Speaker) => {
  await ElMessageBox.confirm('确定删除该说话人？', '确认')
  try {
    await speakerApi.delete(speaker.id)
    ElMessage.success('删除成功')
    fetchSpeakers()
  } catch (error) {
    // Error handled
  }
}

onMounted(() => fetchSpeakers())
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stats {
  margin-bottom: 16px;
}

.tag-item {
  margin-right: 4px;
}
</style>
