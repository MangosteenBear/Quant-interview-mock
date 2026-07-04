<!--
  收藏列表页
-->
<template>
  <view class="favorites-page">
    <view v-if="loading && list.length === 0" class="loading-text">加载中...</view>

    <view v-else-if="list.length === 0">
      <EmptyState text="还没有收藏题目" icon="⭐" />
    </view>

    <view v-else>
      <view class="count-bar">已收藏 {{ total }} 道题</view>
      <QuestionCard
        v-for="q in list"
        :key="q.id"
        :question="q"
        :show-favorite="true"
        :is-favorited="true"
        @click="goDetail"
        @toggle-fav="onRemoveFav"
      />
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useFavoriteStore } from '@/stores/favorite'
import { useSettingsStore } from '@/stores/settings'
import { useQuestionStore } from '@/stores/question'
import QuestionCard from '@/components/QuestionCard.vue'
import EmptyState from '@/components/EmptyState.vue'

const favoriteStore = useFavoriteStore()
const settingsStore = useSettingsStore()
const questionStore = useQuestionStore()

const list = computed(() => favoriteStore.list)
const total = computed(() => favoriteStore.total)
const loading = computed(() => favoriteStore.loading)

function goDetail(id: number) {
  const index = favoriteStore.list.findIndex(q => q.id === id)
  questionStore.setSearchResults(favoriteStore.list, favoriteStore.total)
  questionStore.setCurrentIndex(index)
  uni.navigateTo({ url: `/pages/detail/index?id=${id}&index=${index}&total=${favoriteStore.total}` })
}

async function onRemoveFav(id: number) {
  await favoriteStore.toggle(id, settingsStore.deviceId)
}

onMounted(() => {
  settingsStore.initDeviceId()
  favoriteStore.fetchList(settingsStore.deviceId, true)
})
</script>

<style scoped>
.favorites-page {
  min-height: 100vh;
  background: var(--bg-page, #f7f9fc);
  padding: 12px;
}
.loading-text {
  text-align: center;
  padding: 20px;
  color: var(--text-secondary, #999);
}
.count-bar {
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
  margin-bottom: 10px;
}
</style>
