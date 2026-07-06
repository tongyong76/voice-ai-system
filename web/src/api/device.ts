import request from './request'

export interface Device {
  id: number
  device_code: string
  name: string | null
  location: string | null
  firmware_version: string | null
  status: 'online' | 'offline' | 'busy' | 'error'
  last_heartbeat: string | null
  last_upload: string | null
  created_at: string
}

export interface DeviceCreate {
  device_code: string
  name?: string
  location?: string
  firmware_version?: string
}

export const deviceApi = {
  list(params?: { status?: string; skip?: number; limit?: number }) {
    return request.get<Device[]>('/device/list', { params })
  },

  get(id: number) {
    return request.get<Device>(`/device/${id}`)
  },

  create(data: DeviceCreate) {
    return request.post<Device>('/device/register', data)
  },

  delete(id: number) {
    return request.delete(`/device/${id}`)
  },

  heartbeat(deviceCode: string, status: string = 'online') {
    return request.post('/device/heartbeat', { device_code: deviceCode, status })
  },
}
