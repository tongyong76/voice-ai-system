import request from './request'

export interface AudioRecord {
  id: number
  device_id: number
  task_id: number | null
  file_path: string
  file_size: number | null
  duration_ms: number | null
  sample_rate: number
  format: string
  upload_time: string
  inference_status: 'pending' | 'processing' | 'completed' | 'failed'
}

export interface Transcript {
  id: number
  audio_id: number
  full_text: string | null
  language: string
  segments: Array<{
    start: number
    end: number
    text: string
    confidence: number
  }> | null
}

export interface SpeakerRecord {
  id: number
  audio_id: number
  speaker_label: string | null
  speaker_id: number | null
  confidence: number | null
  start_ms: number | null
  end_ms: number | null
}

export interface EmotionRecord {
  id: number
  audio_id: number
  label: string | null
  confidence: number | null
  start_ms: number | null
  end_ms: number | null
}

export interface NLUResult {
  id: number
  audio_id: number
  keywords: string[] | null
  intent: string | null
  entities: Record<string, any> | null
}

export const audioApi = {
  list(params?: {
    device_id?: number
    task_id?: number
    inference_status?: string
    start_time?: string
    end_time?: string
    skip?: number
    limit?: number
  }) {
    return request.get<AudioRecord[]>('/audio/list', { params })
  },

  get(id: number) {
    return request.get<AudioRecord>(`/audio/${id}`)
  },

  download(id: number) {
    return request.get<{ url: string }>(`/audio/${id}/download`)
  },

  upload(file: File, deviceCode: string) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/audio/upload', formData, {
      params: { device_code: deviceCode },
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

export const resultApi = {
  getTranscript(audioId: number) {
    return request.get<Transcript[]>(`/result/transcript/${audioId}`)
  },

  getSpeakers(audioId: number) {
    return request.get<SpeakerRecord[]>(`/result/speaker/${audioId}`)
  },

  getEmotions(audioId: number) {
    return request.get<EmotionRecord[]>(`/result/emotion/${audioId}`)
  },

  getNLU(audioId: number) {
    return request.get<NLUResult[]>(`/result/nlu/${audioId}`)
  },
}
