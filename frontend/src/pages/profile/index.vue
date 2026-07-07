<!--
  我的 — 个人中心（tab 页）
  用户卡片 + 学习进度统计 + 错题本/收藏/设置入口
  匿名用户也能看统计（device_id 维度），登录后跨设备同步
-->
<template>
  <view class="profile-page">
    <!-- 用户卡片 -->
    <view class="user-card" @click="onUserCardTap">
      <view class="avatar">
        <text class="avatar-text">{{ avatarChar }}</text>
      </view>
      <view class="user-info">
        <text class="user-name">{{ auth.isLoggedIn ? (auth.user?.nickname || auth.user?.phone) : '点击登录' }}</text>
        <text class="user-sub">{{ auth.isLoggedIn ? auth.user?.phone : '登录后做题记录跨设备同步' }}</text>
      </view>
      <text class="edit-hint">{{ auth.isLoggedIn ? '编辑' : '' }} →</text>
    </view>

    <!-- 进度统计 -->
    <view class="stats-card">
      <view class="stats-header">
        <text class="card-title">我的进度</text>
        <text v-if="stats && stats.streak_days > 0" class="streak">🔥 连续 {{ stats.streak_days }} 天</text>
      </view>
      <view v-if="stats" class="stats-grid">
        <view class="stat-item">
          <text class="stat-value">{{ stats.attempted_questions }}</text>
          <text class="stat-label">已做题目</text>
        </view>
        <view class="stat-item">
          <text class="stat-value">{{ stats.correct_rate != null ? Math.round(stats.correct_rate * 100) + '%' : '—' }}</text>
          <text class="stat-label">正确率</text>
        </view>
        <view class="stat-item">
          <text class="stat-value">{{ stats.today_count }}</text>
          <text class="stat-label">今日做题</text>
        </view>
      </view>
      <view v-if="stats && Object.keys(stats.by_type).length" class="type-rows">
        <view v-for="(count, type) in stats.by_type" :key="type" class="type-row">
          <text class="type-name">{{ typeLabel(type as string) }}</text>
          <text class="type-count">{{ count }} 题</text>
        </view>
      </view>
      <text v-if="!stats" class="stats-empty">开始做题后这里会显示进度</text>
    </view>

    <!-- 功能入口 -->
    <view class="menu-group">
      <view class="menu-item" @click="go('/pages/wrong/index')">
        <text class="menu-icon">📕</text>
        <text class="menu-label">错题本</text>
        <text class="menu-arrow">→</text>
      </view>
      <view class="menu-item" @click="uni.switchTab({ url: '/pages/favorites/index' })">
        <text class="menu-icon">⭐</text>
        <text class="menu-label">我的收藏</text>
        <text class="menu-arrow">→</text>
      </view>
      <view class="menu-item" @click="go('/pages/settings/index')">
        <text class="menu-icon">⚙️</text>
        <text class="menu-label">设置</text>
        <text class="menu-arrow">→</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { getStats, updateMe, type StatsResponse } from '@/api/user'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'

const auth = useAuthStore()
const settings = useSettingsStore()
const stats = ref<StatsResponse | null>(null)

const avatarChar = computed(() => {
  if (!auth.isLoggedIn) return '?'
  const n = auth.user?.nickname
  return n ? n[0] : '我'
})

function typeLabel(t: string) {
  return { choice: '选择题', fill: '填空题', short: '简答题', proof: '证明题' }[t] || t
}

function go(url: string) {
  uni.navigateTo({ url })
}

function onUserCardTap() {
  if (!auth.isLoggedIn) {
    uni.navigateTo({ url: '/pages/login/index' })
    return
  }
  uni.showModal({
    title: '修改昵称',
    editable: true,
    placeholderText: auth.user?.nickname || '',
    async success(res) {
      if (res.confirm && res.content?.trim()) {
        try {
          auth.user = await updateMe({ nickname: res.content.trim() })
          uni.showToast({ title: '已更新', icon: 'success' })
        } catch { /* toast 已弹 */ }
      }
    },
  })
}

onShow(async () => {
  settings.initDeviceId()
  try {
    stats.value = await getStats(auth.isLoggedIn ? undefined : settings.deviceId)
  } catch {
    stats.value = null
  }
})
</script>

<style scoped>
.profile-page {
  min-height: 100vh;
  background: var(--bg-page, #f7f9fc);
  padding: 24rpx;
  display: flex;
  flex-direction: column;
  gap: 24rpx;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 24rpx;
  padding: 40rpx 32rpx;
  background: var(--bg-card, #fff);
  border-radius: 24rpx;
}

.avatar {
  width: 100rpx;
  height: 100rpx;
  border-radius: 50%;
  background: #1e3a5f;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.avatar-text {
  color: #fff;
  font-size: 40rpx;
}

.user-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.user-name {
  font-size: 34rpx;
  font-weight: 600;
  color: var(--text-primary, #2c3338);
}

.user-sub {
  font-size: 24rpx;
  color: var(--text-secondary, #6b7280);
}

.edit-hint {
  font-size: 24rpx;
  color: var(--text-secondary, #9ca3af);
}

.stats-card {
  padding: 32rpx;
  background: var(--bg-card, #fff);
  border-radius: 24rpx;
}

.stats-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24rpx;
}

.card-title {
  font-size: 30rpx;
  font-weight: 600;
  color: var(--text-primary, #2c3338);
}

.streak {
  font-size: 26rpx;
  color: #e07b39;
}

.stats-grid {
  display: flex;
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
}

.stat-value {
  font-size: 44rpx;
  font-weight: 700;
  color: #1e3a5f;
}

.stat-label {
  font-size: 24rpx;
  color: var(--text-secondary, #6b7280);
}

.type-rows {
  margin-top: 28rpx;
  padding-top: 24rpx;
  border-top: 2rpx solid var(--border-color, #f0f0f0);
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.type-row {
  display: flex;
  justify-content: space-between;
}

.type-name {
  font-size: 26rpx;
  color: var(--text-primary, #2c3338);
}

.type-count {
  font-size: 26rpx;
  color: var(--text-secondary, #6b7280);
}

.stats-empty {
  font-size: 26rpx;
  color: var(--text-secondary, #9ca3af);
  text-align: center;
  padding: 24rpx 0;
  display: block;
}

.menu-group {
  background: var(--bg-card, #fff);
  border-radius: 24rpx;
  padding: 0 32rpx;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 20rpx;
  padding: 32rpx 0;
  border-bottom: 2rpx solid var(--border-color, #f5f5f5);
}

.menu-item:last-child {
  border-bottom: none;
}

.menu-icon {
  font-size: 34rpx;
}

.menu-label {
  flex: 1;
  font-size: 30rpx;
  color: var(--text-primary, #2c3338);
}

.menu-arrow {
  font-size: 26rpx;
  color: var(--text-secondary, #9ca3af);
}
</style>
