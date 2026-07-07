<!--
  设置页 — 夜间模式 + 字体大小调节
-->
<template>
  <view class="settings-page">
    <!-- 账号 -->
    <view class="settings-group">
      <text class="group-title">账号</text>
      <view v-if="auth.isLoggedIn" class="settings-item">
        <text class="item-label">{{ auth.user?.nickname || auth.user?.phone }}</text>
        <text class="item-value">{{ auth.user?.phone }}</text>
      </view>
      <view v-if="auth.isLoggedIn" class="settings-item danger" @click="confirmLogout">
        <text class="item-label danger-text">退出登录</text>
        <text class="item-arrow">→</text>
      </view>
      <view v-else class="settings-item" @click="goLogin">
        <text class="item-label">登录 / 注册</text>
        <text class="item-arrow">→</text>
      </view>
    </view>

    <!-- 主题设置 -->
    <view class="settings-group">
      <text class="group-title">显示设置</text>
      <view class="settings-item">
        <text class="item-label">夜间模式</text>
        <switch :checked="settings.isDark" @change="onToggleTheme" color="#1e3a5f" />
      </view>
    </view>

    <!-- 字体大小 -->
    <view class="settings-group">
      <text class="group-title">字体大小</text>
      <view class="font-size-options">
        <view
          v-for="opt in fontOptions"
          :key="opt.value"
          class="font-option"
          :class="{ active: settings.fontSize === opt.value }"
          @click="onSetFontSize(opt.value)"
        >
          <text :style="{ fontSize: opt.size }">A</text>
          <text class="font-label">{{ opt.label }}</text>
        </view>
      </view>
    </view>

    <!-- 数据管理 -->
    <view class="settings-group">
      <text class="group-title">数据管理</text>
      <view class="settings-item">
        <text class="item-label">已做题目</text>
        <text class="item-value">{{ attemptedCount }} 道</text>
      </view>
      <view class="settings-item danger" @click="confirmReset">
        <text class="item-label danger-text">重置做题记录</text>
        <text class="item-arrow">→</text>
      </view>
    </view>

    <!-- 关于 -->
    <view class="settings-group">
      <text class="group-title">关于</text>
      <view class="settings-item">
        <text class="item-label">版本</text>
        <text class="item-value">v0.1.0</text>
      </view>
      <view class="settings-item">
        <text class="item-label">设备 ID</text>
        <text class="item-value device-id">{{ settings.deviceId?.slice(0, 8) }}...</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useSettingsStore, type FontSize } from '@/stores/settings'
import { useAttemptStore } from '@/stores/attempt'
import { useAuthStore } from '@/stores/auth'

const settings = useSettingsStore()
const attemptStore = useAttemptStore()
const auth = useAuthStore()

function goLogin() {
  uni.navigateTo({ url: '/pages/login/index' })
}

function confirmLogout() {
  uni.showModal({
    title: '退出登录',
    content: '本机做题记录仍会保留，确认退出？',
    confirmColor: '#e24b4a',
    success(res) {
      if (res.confirm) {
        auth.logout()
        uni.showToast({ title: '已退出', icon: 'success' })
      }
    },
  })
}

const attemptedCount = computed(() => attemptStore.attemptedCount)

const fontOptions = [
  { value: 'small' as FontSize, label: '小', size: '14px' },
  { value: 'medium' as FontSize, label: '中', size: '16px' },
  { value: 'large' as FontSize, label: '大', size: '18px' },
]

function onToggleTheme() {
  settings.toggleTheme()
}

function onSetFontSize(size: FontSize) {
  settings.setFontSize(size)
}

function confirmReset() {
  uni.showModal({
    title: '重置做题记录',
    content: '清除后所有题目变为"未做"状态，收藏不受影响。确认？',
    confirmText: '确认重置',
    confirmColor: '#e24b4a',
    success(res) {
      if (res.confirm) {
        attemptStore.reset()
        uni.showToast({ title: '已重置', icon: 'success' })
      }
    },
  })
}

onMounted(() => {
  settings.initDeviceId()
  settings.applyTheme()
  attemptStore.init()
})
</script>

<style scoped>
.settings-page {
  min-height: 100vh;
  background: var(--bg-page, #f7f9fc);
  padding: 12px;
}

.settings-group {
  background: var(--bg-card, #fff);
  border-radius: 12px;
  padding: 4px 16px;
  margin-bottom: 12px;
}
.group-title {
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
  padding: 10px 0 6px;
  display: block;
}
.settings-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-top: 1px solid var(--border-color, #f0f0f0);
}
.item-label {
  font-size: 15px;
  color: var(--text-primary, #2c3338);
}
.item-value {
  font-size: 14px;
  color: var(--text-secondary, #6b7280);
}
.device-id {
  font-family: monospace;
}

/* 字体大小选项 */
.font-size-options {
  display: flex;
  gap: 10px;
  padding: 12px 0;
}
.font-option {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 0;
  border: 2px solid var(--border-color, #e0e0e0);
  border-radius: 10px;
  color: var(--text-primary, #2c3338);
}
.font-option.active {
  border-color: var(--primary-color, #1e3a5f);
  background: var(--bg-primary-light, #e8f0fe);
}
.font-label {
  font-size: 12px;
  color: var(--text-secondary, #6b7280);
}
.settings-item.danger { cursor: pointer; }
.danger-text { color: #e24b4a; }
.item-arrow { font-size: 14px; color: var(--text-secondary, #ccc); }
</style>
