import request from './request'

export interface LoginParams {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export const authApi = {
  login(params: LoginParams) {
    return request.post<TokenResponse>('/auth/login', params)
  },
}
