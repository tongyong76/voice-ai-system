import request from './request'

export interface DashboardStats {
  onlineDevices: number
  todayAudio: number
  speakerCount: number
  alertCount: number
}

export interface TrendItem {
  hour?: string
  date?: string
  hours: number
}

export interface EmotionDist {
  name: string
  value: number
}

export interface RecentAudio {
  id: number
  device_id: number
  upload_time: string | null
  duration_ms: number | null
  inference_status: string
}

export interface RecentAlert {
  id: number
  rule_id: number
  audio_id: number
  triggered_at: string | null
  acknowledged: boolean
  message: string
}

export const statsApi = {
  getDashboard() {
    return request.get<DashboardStats>('/stats/dashboard')
  },

  getTrend(days: number = 1) {
    return request.get<TrendItem[]>('/stats/trend', { params: { days } })
  },

  getEmotionDistribution() {
    return request.get<EmotionDist[]>('/stats/emotion-distribution')
  },

  getRecentAudio(limit: number = 10) {
    return request.get<RecentAudio[]>('/stats/recent-audio', { params: { limit } })
  },

  getRecentAlerts(limit: number = 10) {
    return request.get<RecentAlert[]>('/stats/recent-alerts', { params: { limit } })
  },
}
