<!--
  错题本 — 每题以最近一次作答为准，答对自动移出
-->
<template>
  <view class="wrong-page">
    <view v-if="loading" class="loading-text">加载中...</view>

    <view v-else-if="items.length === 0">
      <EmptyState text="没有错题，继续保持！" icon="🎉" />
    </view>

    <view v-else>
      <view class="count-bar">共 {{ items.length }} 道错题 · 重新答对自动移出</view>
      <view v-for="item in items" :key="item.question.id" class="wrong-item">
        <QuestionCard :question="item.question" @click="goDetail" />
        <text class="wrong-meta">错 {{ item.wrong_count }} 次 · {{ fmtDate(item.last_wrong_at) }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { getWrongQuestions, type WrongQuestionItem } from '@/api/user'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'
import QuestionCard from '@/components/QuestionCard.vue'
import EmptyState from '@/components/EmptyState.vue'

const auth = useAuthStore()
const settings = useSettingsStore()
const items = ref<WrongQuestionItem[]>([])
const loading = ref(true)

function fmtDate(s: string) {
  const d = new Date(s)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

function goDetail(id: number) {
  uni.navigateTo({ url: `/pages/detail/index?id=${id}` })
}

onShow(async () => {
  settings.initDeviceId()
  loading.value = true
  try {
    const res = await getWrongQuestions(auth.isLoggedIn ? undefined : settings.deviceId)
    items.value = res.items
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.wrong-page {
  min-height: 100vh;
  background: var(--bg-page, #f7f9fc);
  padding: 24rpx;
}

.loading-text {
  text-align: center;
  padding: 80rpx 0;
  color: var(--text-secondary, #9ca3af);
  font-size: 28rpx;
}

.count-bar {
  font-size: 26rpx;
  color: var(--text-secondary, #6b7280);
  padding: 8rpx 8rpx 20rpx;
}

.wrong-item {
  margin-bottom: 8rpx;
}

.wrong-meta {
  display: block;
  font-size: 22rpx;
  color: #e24b4a;
  padding: 0 16rpx 16rpx;
}
</style>
