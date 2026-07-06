import request from './request'

export interface Task {
  id: number
  name: string
  description: string | null
  target_device_ids: number[] | string[]
  config: Record<string, any> | null
  status: 'pending' | 'dispatched' | 'running' | 'completed' | 'failed'
  scheduled_at: string | null
  started_at: string | null
  completed_at: string | null
  created_by: number | null
  created_at: string
}

export interface TaskCreate {
  name: string
  description?: string
  target_device_ids: number[] | string[]
  config?: Record<string, any>
  scheduled_at?: string
}

export const taskApi = {
  list(params?: { status?: string; skip?: number; limit?: number }) {
    return request.get<Task[]>('/task/list', { params })
  },

  get(id: number) {
    return request.get<Task>(`/task/${id}`)
  },

  create(data: TaskCreate) {
    return request.post<Task>('/task', data)
  },

  dispatch(id: number) {
    return request.put(`/task/${id}/dispatch`)
  },
}
