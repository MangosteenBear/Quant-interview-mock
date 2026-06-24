/**
 * device_id 生成与持久化
 * 一期匿名模式，前端生成唯一设备标识并存储
 */

const STORAGE_KEY = 'device_id'

/**
 * 获取或生成 device_id
 * H5: crypto.randomUUID()（现代浏览器支持）
 * 兜底: Date.now() + Math.random().toString(36)
 */
export function getDeviceId(): string {
  // 先从缓存读
  let id = uni.getStorageSync(STORAGE_KEY)
  if (id) return id

  // 生成新 ID
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    id = crypto.randomUUID()
  } else {
    id = `dev_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`
  }

  uni.setStorageSync(STORAGE_KEY, id)
  return id
}
