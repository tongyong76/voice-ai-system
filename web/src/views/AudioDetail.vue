<template>
  <div class="audio-detail">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>音频详情 #{{ audioId }}</span>
          <el-button @click="$router.back()">返回</el-button>
        </div>
      </template>

      <!-- Audio Player -->
      <div class="player-section">
        <div ref="waveformRef" class="waveform"></div>
        <div class="player-controls">
          <el-button @click="togglePlay" :icon="isPlaying ? 'VideoPause' : 'VideoPlay'" circle />
          <span class="time">{{ currentTime }} / {{ totalTime }}</span>
        </div>
      </div>

      <!-- Info Tabs -->
      <el-tabs v-model="activeTab" class="detail-tabs">
        <el-tab-pane label="转写结果" name="transcript">
          <div v-if="transcripts.length > 0" class="transcript-content">
            <div v-for="t in transcripts" :key="t.id" class="transcript-item">
              <div class="transcript-text">{{ t.full_text }}</div>
              <div v-if="t.segments" class="segments">
                <div v-for="(seg, idx) in t.segments" :key="idx" class="segment">
                  <span class="seg-time">{{ formatTime(seg.start) }} - {{ formatTime(seg.end) }}</span>
                  <span class="seg-text">{{ seg.text }}</span>
                </div>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无转写结果" />
        </el-tab-pane>

        <el-tab-pane label="说话人" name="speaker">
          <div v-if="speakerRecords.length > 0">
            <el-table :data="speakerRecords">
              <el-table-column prop="speaker_label" label="标签" />
              <el-table-column prop="speaker_id" label="说话人ID" />
              <el-table-column prop="confidence" label="置信度">
                <template #default="{ row }">
                  {{ (row.confidence * 100).toFixed(1) }}%
                </template>
              </el-table-column>
              <el-table-column label="时间段">
                <template #default="{ row }">
                  {{ formatTime(row.start_ms / 1000) }} - {{ formatTime(row.end_ms / 1000) }}
                </template>
              </el-table-column>
            </el-table>
          </div>
          <el-empty v-else description="暂无说话人数据" />
        </el-tab-pane>

        <el-tab-pane label="情感分析" name="emotion">
          <div v-if="emotions.length > 0">
            <el-table :data="emotions">
              <el-table-column prop="label" label="情感" />
              <el-table-column prop="confidence" label="置信度">
                <template #default="{ row }">
                  {{ (row.confidence * 100).toFixed(1) }}%
                </template>
              </el-table-column>
              <el-table-column label="时间段">
                <template #default="{ row }">
                  {{ formatTime(row.start_ms / 1000) }} - {{ formatTime(row.end_ms / 1000) }}
                </template>
              </el-table-column>
            </el-table>
          </div>
          <el-empty v-else description="暂无情感数据" />
        </el-tab-pane>

        <el-tab-pane label="NLU分析" name="nlu">
          <div v-if="nluResults.length > 0">
            <div v-for="nlu in nluResults" :key="nlu.id" class="nlu-item">
              <div><strong>意图：</strong>{{ nlu.intent }}</div>
              <div><strong>关键词：</strong>{{ nlu.keywords?.join(', ') }}</div>
              <div v-if="nlu.entities"><strong>实体：</strong>{{ JSON.stringify(nlu.entities) }}</div>
            </div>
          </div>
          <el-empty v-else description="暂无NLU数据" />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import WaveSurfer from 'wavesurfer.js'
import { audioApi, resultApi, type Transcript, type SpeakerRecord, type EmotionRecord, type NLUResult } from '@/api/audio'

const route = useRoute()
const audioId = computed(() => Number(route.params.id))

const waveformRef = ref<HTMLElement>()
const isPlaying = ref(false)
const currentTime = ref('0:00')
const totalTime = ref('0:00')
const activeTab = ref('transcript')

const transcripts = ref<Transcript[]>([])
const speakerRecords = ref<SpeakerRecord[]>([])
const emotions = ref<EmotionRecord[]>([])
const nluResults = ref<NLUResult[]>([])

let wavesurfer: WaveSurfer | null = null

const formatTime = (seconds: number) => {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

const togglePlay = () => {
  wavesurfer?.playPause()
}

const initWaveform = async () => {
  if (!waveformRef.value) return

  try {
    const { url } = await audioApi.download(audioId.value)
    wavesurfer = WaveSurfer.create({
      container: waveformRef.value,
      waveColor: '#409eff',
      progressColor: '#79bbff',
      cursorColor: '#337ecc',
      height: 80,
    })
    wavesurfer.load(url)
    wavesurfer.on('play', () => { isPlaying.value = true })
    wavesurfer.on('pause', () => { isPlaying.value = false })
    wavesurfer.on('audioprocess', () => {
      currentTime.value = formatTime(wavesurfer?.getCurrentTime() || 0)
    })
    wavesurfer.on('ready', () => {
      totalTime.value = formatTime(wavesurfer?.getDuration() || 0)
    })
  } catch (error) {
    console.error('Failed to load audio:', error)
  }
}

const fetchResults = async () => {
  try {
    const [t, s, e, n] = await Promise.all([
      resultApi.getTranscript(audioId.value),
      resultApi.getSpeakers(audioId.value),
      resultApi.getEmotions(audioId.value),
      resultApi.getNLU(audioId.value),
    ])
    transcripts.value = t
    speakerRecords.value = s
    emotions.value = e
    nluResults.value = n
  } catch (error) {
    // Error handled
  }
}

onMounted(() => {
  initWaveform()
  fetchResults()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.player-section {
  margin-bottom: 24px;
}

.waveform {
  margin-bottom: 12px;
}

.player-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.time {
  font-size: 14px;
  color: #666;
}

.detail-tabs {
  margin-top: 16px;
}

.transcript-item {
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 12px;
}

.transcript-text {
  font-size: 16px;
  line-height: 1.6;
  margin-bottom: 12px;
}

.segments {
  border-top: 1px solid #e4e7ed;
  padding-top: 12px;
}

.segment {
  display: flex;
  gap: 12px;
  padding: 8px 0;
}

.seg-time {
  color: #409eff;
  font-size: 13px;
  min-width: 120px;
}

.seg-text {
  flex: 1;
}

.nlu-item {
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 12px;
}

.nlu-item div {
  margin-bottom: 8px;
}
</style>
