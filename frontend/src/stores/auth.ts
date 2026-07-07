/**
 * 账号 Store
 * token 持久化 + 用户信息 + 登录/登出 + 历史数据绑定
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { verifyCode, getMe, bindDevice, type UserOut } from '@/api/auth'
import { useSettingsStore } from './settings'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserOut | null>(null)
  const isLoggedIn = computed(() => !!user.value)

  /** App 启动时调用：本地有 token 则拉取用户信息恢复登录态 */
  async function restore() {
    if (!uni.getStorageSync('access_token')) return
    try {
      user.value = await getMe()
    } catch {
      user.value = null
    }
  }

  /** 验证码登录，成功后自动绑定本设备历史记录 */
  async function login(phone: string, code: string) {
    const tok = await verifyCode(phone, code)
    uni.setStorageSync('access_token', tok.access_token)
    uni.setStorageSync('refresh_token', tok.refresh_token)
    user.value = await getMe()

    const settings = useSettingsStore()
    settings.initDeviceId()
    if (settings.deviceId) {
      try {
        const r = await bindDevice(settings.deviceId)
        if (r.migrated_attempts + r.migrated_favorites > 0) {
          uni.showToast({
            title: `已同步 ${r.migrated_attempts} 条记录、${r.migrated_favorites} 个收藏`,
            icon: 'none',
            duration: 2500,
          })
        }
      } catch { /* 绑定失败不阻断登录 */ }
    }
    return tok.is_new_user
  }

  function logout() {
    uni.removeStorageSync('access_token')
    uni.removeStorageSync('refresh_token')
    user.value = null
  }

  return { user, isLoggedIn, restore, login, logout }
})
