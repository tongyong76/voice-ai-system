import request from './request'

export interface Speaker {
  id: number
  name: string
  tags: string[] | null
  created_at: string
}

export const speakerApi = {
  list(params?: { skip?: number; limit?: number }) {
    return request.get<Speaker[]>('/speaker/list', { params })
  },

  get(id: number) {
    return request.get<Speaker>(`/speaker/${id}`)
  },

  enroll(data: { name: string; tags: string; files: File[] }) {
    const formData = new FormData()
    formData.append('name', data.name)
    formData.append('tags', data.tags.join(','))
    data.files.forEach((file) => {
      formData.append('files', file)
    })
    return request.post('/speaker/enroll', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  update(id: number, data: { name?: string; tags?: string[] }) {
    return request.put(`/speaker/${id}`, data)
  },

  delete(id: number) {
    return request.delete(`/speaker/${id}`)
  },
}
