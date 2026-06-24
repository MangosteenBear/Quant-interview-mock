<!--
  搜索页
  关键词搜索题目，防抖 300ms
-->
<template>
  <view class="search-page">
    <!-- 搜索框 -->
    <view class="search-bar">
      <input
        v-model="keyword"
        class="search-input"
        placeholder="搜索题目关键词..."
        confirm-type="search"
        @input="onInput"
        @confirm="onSearch"
      />
      <text v-if="keyword" class="clear-btn" @click="clearSearch">✕</text>
    </view>

    <!-- 搜索结果 -->
    <view class="search-results">
      <view v-if="loading" class="loading-text">搜索中...</view>

      <view v-else-if="results.length === 0 && searched" >
        <EmptyState text="未找到相关题目" icon="🔍" />
      </view>

      <view v-else>
        <view v-if="searched" class="result-count">共 {{ total }} 道题</view>
        <QuestionCard
          v-for="q in results"
          :key="q.id"
          :question="q"
          @click="goDetail"
        />
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { searchQuestions } from '@/api/question'
import type { QuestionListItem } from '@/types/api'
import QuestionCard from '@/components/QuestionCard.vue'
import EmptyState from '@/components/EmptyState.vue'

const keyword = ref('')
const results = ref<QuestionListItem[]>([])
const total = ref(0)
const loading = ref(false)
const searched = ref(false)
let debounceTimer: ReturnType<typeof setTimeout> | null = null

function onInput() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    if (keyword.value.trim()) {
      onSearch()
    } else {
      results.value = []
      searched.value = false
    }
  }, 300)
}

async function onSearch() {
  const q = keyword.value.trim()
  if (!q) return
  loading.value = true
  searched.value = true
  try {
    const res = await searchQuestions({ q, page: 1, page_size: 50 })
    results.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function clearSearch() {
  keyword.value = ''
  results.value = []
  searched.value = false
}

function goDetail(id: number) {
  uni.navigateTo({ url: `/pages/detail/index?id=${id}` })
}
</script>

<style scoped>
.search-page {
  min-height: 100vh;
  background: var(--bg-page, #f7f9fc);
}

.search-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: var(--bg-card, #fff);
  position: sticky;
  top: 0;
  z-index: 10;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}
.search-input {
  flex: 1;
  height: 36px;
  padding: 0 12px;
  background: var(--bg-secondary, #f0f2f5);
  border-radius: 18px;
  font-size: 14px;
  color: var(--text-primary, #2c3338);
}
.clear-btn {
  font-size: 16px;
  color: var(--text-secondary, #999);
  padding: 4px;
}

.search-results { padding: 12px; }
.loading-text {
  text-align: center;
  padding: 20px;
  color: var(--text-secondary, #999);
  font-size: 14px;
}
.result-count {
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
  margin-bottom: 10px;
}
</style>
