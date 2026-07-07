/**
 * 账号认证 API
 */
import { request } from './request'

export interface TokenResponse {
  access_token: string
  refresh_token: string
  is_new_user: boolean
}

export interface UserOut {
  id: number
  phone: string
  nickname: string | null
  avatar_url: string | null
  created_at: string
}

export interface BindDeviceResponse {
  migrated_attempts: number
  migrated_favorites: number
}

export function sendCode(phone: string) {
  return request<{ sent: boolean; dev_code: string | null }>({
    url: '/auth/send-code',
    method: 'POST',
    data: { phone },
  })
}

export function verifyCode(phone: string, code: string) {
  return request<TokenResponse>({
    url: '/auth/verify',
    method: 'POST',
    data: { phone, code },
  })
}

export function getMe() {
  return request<UserOut>({ url: '/users/me' })
}

export function bindDevice(deviceId: string) {
  return request<BindDeviceResponse>({
    url: '/users/me/bind-device',
    method: 'POST',
    data: { device_id: deviceId },
  })
}
