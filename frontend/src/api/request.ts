/**
 * HTTP 请求统一封装
 * 基于 uni.request（H5 底层 XHR，小程序原生），双端通用
 * 统一错误处理、baseURL 管理
 */
import type { PageResponse } from '@/types/api'

// H5 开发走 vite 代理（/api → localhost:8000）
// H5 生产由 VITE_API_BASE 环境变量注入后端 URL（例: https://quantquiz-api.vercel.app）
// 小程序端需在 manifest.json 中配置 request 合法域名
const BASE_URL = (import.meta.env.VITE_API_BASE ?? '') + '/api'

/** API 错误类型 */
export interface ApiError {
  statusCode: number
  message: string
  detail?: string
}

/** 构建带 query 参数的 URL */
function buildUrl(path: string, params?: Record<string, any>): string {
  if (!params) return path
  const query = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    .join('&')
  return query ? `${path}?${query}` : path
}

/** 统一错误归一化 */
function normalizeError(res: UniApp.RequestSuccessCallbackResult): ApiError {
  const data = res.data as Record<string, any>
  // 后端有两种错误格式：HTTPException {"detail":"..."} / 500 {"code":500,"message":"..."}
  const message = data?.detail || data?.message || `请求失败 (${res.statusCode})`
  return { statusCode: res.statusCode, message, detail: data?.detail }
}

/**
 * 统一请求方法
 * @param opts.url 接口路径（不含 /api 前缀）
 * @param opts.method GET | POST
 * @param opts.data POST 请求体
 * @param opts.params GET query 参数
 */
export function request<T>(opts: {
  url: string
  method?: 'GET' | 'POST'
  data?: Record<string, any>
  params?: Record<string, any>
}): Promise<T> {
  return doRequest<T>(opts, true)
}

/** 401 时用 refresh_token 换新 access_token */
async function tryRefresh(): Promise<boolean> {
  const refreshToken = uni.getStorageSync('refresh_token')
  if (!refreshToken) return false
  try {
    const res = await new Promise<UniApp.RequestSuccessCallbackResult>((resolve, reject) => {
      uni.request({
        url: BASE_URL + '/auth/refresh',
        method: 'POST',
        data: { refresh_token: refreshToken },
        header: { 'Content-Type': 'application/json' },
        success: resolve,
        fail: reject,
      })
    })
    if (res.statusCode === 200) {
      uni.setStorageSync('access_token', (res.data as any).access_token)
      return true
    }
  } catch { /* 网络失败按刷新失败处理 */ }
  uni.removeStorageSync('access_token')
  uni.removeStorageSync('refresh_token')
  return false
}

function doRequest<T>(
  opts: { url: string; method?: 'GET' | 'POST'; data?: Record<string, any>; params?: Record<string, any> },
  allowRetry: boolean,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const header: Record<string, string> = { 'Content-Type': 'application/json' }
    const token = uni.getStorageSync('access_token')
    if (token) header.Authorization = `Bearer ${token}`

    uni.request({
      url: BASE_URL + buildUrl(opts.url, opts.params),
      method: opts.method || 'GET',
      data: opts.data,
      header,
      success: async (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data as T)
        } else if (res.statusCode === 401 && allowRetry && token && !opts.url.startsWith('/auth/')) {
          if (await tryRefresh()) {
            doRequest<T>(opts, false).then(resolve, reject)
          } else {
            reject(normalizeError(res))
          }
        } else {
          const err = normalizeError(res)
          uni.showToast({ title: err.message, icon: 'none' })
          reject(err)
        }
      },
      fail: (err) => {
        const apiErr: ApiError = { statusCode: 0, message: '网络请求失败', detail: err.errMsg }
        uni.showToast({ title: apiErr.message, icon: 'none' })
        reject(apiErr)
      },
    })
  })
}

/** 分页响应快捷类型 */
export type Paginated<T> = PageResponse<T>
