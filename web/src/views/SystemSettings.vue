<template>
  <div class="system-settings">
    <el-card shadow="hover">
      <template #header>系统设置</template>

      <el-form :model="settings" label-width="150px" style="max-width: 600px">
        <el-divider content-position="left">服务器配置</el-divider>

        <el-form-item label="AI推理服务地址">
          <el-input v-model="settings.aiEngineUrl" placeholder="http://localhost:8001" />
        </el-form-item>

        <el-form-item label="MinIO地址">
          <el-input v-model="settings.minioEndpoint" placeholder="localhost:9000" />
        </el-form-item>

        <el-divider content-position="left">音频配置</el-divider>

        <el-form-item label="默认采样率">
          <el-select v-model="settings.sampleRate" style="width: 100%">
            <el-option label="8000 Hz" :value="8000" />
            <el-option label="16000 Hz" :value="16000" />
            <el-option label="44100 Hz" :value="44100" />
          </el-select>
        </el-form-item>

        <el-form-item label="音频格式">
          <el-select v-model="settings.audioFormat" style="width: 100%">
            <el-option label="Opus" value="opus" />
            <el-option label="WAV" value="wav" />
            <el-option label="MP3" value="mp3" />
          </el-select>
        </el-form-item>

        <el-form-item label="分片时长(秒)">
          <el-input-number v-model="settings.segmentDuration" :min="1" :max="30" />
        </el-form-item>

        <el-divider content-position="left">ASR配置</el-divider>

        <el-form-item label="热词">
          <el-input
            v-model="settings.hotwords"
            type="textarea"
            :rows="3"
            placeholder="每行一个热词"
          />
        </el-form-item>

        <el-form-item label="说话人识别阈值">
          <el-slider v-model="settings.speakerThreshold" :min="0" :max="1" :step="0.05" show-input />
        </el-form-item>

        <el-divider content-position="left">存储配置</el-divider>

        <el-form-item label="音频保留天数">
          <el-input-number v-model="settings.retentionDays" :min="7" :max="365" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSave">保存设置</el-button>
          <el-button @click="fetchSettings">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const settings = ref({
  aiEngineUrl: 'http://localhost:8001',
  minioEndpoint: 'localhost:9000',
  sampleRate: 16000,
  audioFormat: 'opus',
  segmentDuration: 5,
  hotwords: '',
  speakerThreshold: 0.6,
  retentionDays: 90,
})

const fetchSettings = async () => {
  // TODO: Fetch from API
  ElMessage.info('设置已重置')
}

const handleSave = async () => {
  // TODO: Save to API
  ElMessage.success('设置已保存')
}

onMounted(() => fetchSettings())
</script>

<style scoped>
.system-settings {
  max-width: 800px;
}
</style>
