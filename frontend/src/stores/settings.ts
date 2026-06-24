/**
 * 设置 Store
 * 主题（夜间模式）/ 字体大小 / device_id
 * 全部持久化到 uni.storage
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getDeviceId } from '@/utils/device'

export type Theme = 'light' | 'dark'
export type FontSize = 'small' | 'medium' | 'large'

export const useSettingsStore = defineStore('settings', () => {
  // ---------- State ----------
  const theme = ref<Theme>(uni.getStorageSync('theme') || 'light')
  const fontSize = ref<FontSize>(uni.getStorageSync('font_size') || 'medium')
  const deviceId = ref<string>('')

  // ---------- Getters ----------
  const isDark = computed(() => theme.value === 'dark')

  // ---------- Actions ----------
  function initDeviceId() {
    if (!deviceId.value) {
      deviceId.value = getDeviceId()
    }
  }

  function toggleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
    uni.setStorageSync('theme', theme.value)
    applyTheme()
  }

  function setFontSize(size: FontSize) {
    fontSize.value = size
    uni.setStorageSync('font_size', size)
  }

  /** 应用主题到 DOM（H5 端） */
  function applyTheme() {
    // #ifdef H5
    if (typeof document !== 'undefined') {
      document.documentElement.setAttribute('data-theme', theme.value)
    }
    // #endif
  }

  return {
    theme,
    fontSize,
    deviceId,
    isDark,
    initDeviceId,
    toggleTheme,
    setFontSize,
    applyTheme,
  }
})
