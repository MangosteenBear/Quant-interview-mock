<!--
  题库列表页
  分页加载 + 筛选（来源/题型/难度） + 骨架屏
-->
<template>
  <view class="list-page">
    <!-- 筛选区 -->
    <view class="filter-bar">
      <view class="filter-item" @click="showSourcePicker = !showSourcePicker">
        <text>{{ currentSourceName || '来源' }}</text>
        <text class="arrow">▼</text>
      </view>
      <view class="filter-item" @click="showTypePicker = !showTypePicker">
        <text>{{ currentTypeName || '题型' }}</text>
        <text class="arrow">▼</text>
      </view>
      <view class="filter-item" @click="showDifficultyPicker = !showDifficultyPicker">
        <text>{{ currentDifficultyName || '难度' }}</text>
        <text class="arrow">▼</text>
      </view>
      <view v-if="hasFilter" class="filter-clear" @click="clearFilters">清除</view>
    </view>

    <!-- 筛选下拉 -->
    <view v-if="showSourcePicker" class="picker-dropdown">
      <view class="picker-item" :class="{ active: !filters.source_id }" @click="selectSource(undefined)">全部</view>
      <view
        v-for="s in sources"
        :key="s.id"
        class="picker-item"
        :class="{ active: filters.source_id === s.id }"
        @click="selectSource(s.id)"
      >{{ s.book_title.slice(0, 20) }}</view>
    </view>
    <view v-if="showTypePicker" class="picker-dropdown">
      <view class="picker-item" :class="{ active: !filters.question_type }" @click="selectType(undefined)">全部</view>
      <view
        v-for="(label, key) in typeOptions"
        :key="key"
        class="picker-item"
        :class="{ active: filters.question_type === key }"
        @click="selectType(key as any)"
      >{{ label }}</view>
    </view>
    <view v-if="showDifficultyPicker" class="picker-dropdown">
      <view class="picker-item" :class="{ active: !filters.difficulty }" @click="selectDifficulty(undefined)">全部</view>
      <view
        v-for="d in 5"
        :key="d"
        class="picker-item"
        :class="{ active: filters.difficulty === d }"
        @click="selectDifficulty(d)"
      >P{{ d }}</view>
    </view>

    <!-- 遮罩 -->
    <view v-if="showSourcePicker || showTypePicker || showDifficultyPicker" class="picker-mask" @click="closePickers" />

    <!-- 题目列表 -->
    <view class="list-content">
      <view v-if="loading && list.length === 0" class="loading-list">
        <view v-for="i in 5" :key="i" class="skeleton-card" />
      </view>

      <view v-else-if="list.length === 0">
        <EmptyState text="暂无题目" />
      </view>

      <view v-else>
        <QuestionCard
          v-for="q in list"
          :key="q.id"
          :question="q"
          @click="goDetail"
        />
        <view v-if="loading" class="loading-more">加载中...</view>
        <view v-else-if="!hasMore && list.length > 0" class="no-more">没有更多了</view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { onReachBottom } from '@dcloudio/uni-app'
import { useQuestionStore } from '@/stores/question'
import { listSources } from '@/api/source'
import { QUESTION_TYPE_LABELS } from '@/utils/difficulty'
import type { SourceBrief, QuestionType } from '@/types/api'
import QuestionCard from '@/components/QuestionCard.vue'
import EmptyState from '@/components/EmptyState.vue'

const questionStore = useQuestionStore()
const list = computed(() => questionStore.list)
const loading = computed(() => questionStore.loading)
const hasMore = computed(() => questionStore.hasMore)
const filters = computed(() => questionStore.filters)

const sources = ref<SourceBrief[]>([])
const showSourcePicker = ref(false)
const showTypePicker = ref(false)
const showDifficultyPicker = ref(false)
const typeOptions = QUESTION_TYPE_LABELS

const hasFilter = computed(() =>
  filters.value.source_id || filters.value.question_type || filters.value.difficulty
)

const currentSourceName = computed(() => {
  const s = sources.value.find(s => s.id === filters.value.source_id)
  return s ? s.book_title.slice(0, 10) : ''
})
const currentTypeName = computed(() =>
  filters.value.question_type ? typeOptions[filters.value.question_type] : ''
)
const currentDifficultyName = computed(() =>
  filters.value.difficulty ? `P${filters.value.difficulty}` : ''
)

function selectSource(id: number | undefined) {
  questionStore.filters.source_id = id
  showSourcePicker.value = false
  questionStore.fetchList(true)
}
function selectType(type: QuestionType | undefined) {
  questionStore.filters.question_type = type
  showTypePicker.value = false
  questionStore.fetchList(true)
}
function selectDifficulty(d: number | undefined) {
  questionStore.filters.difficulty = d
  showDifficultyPicker.value = false
  questionStore.fetchList(true)
}
function clearFilters() {
  questionStore.resetFilters()
  questionStore.fetchList(true)
}
function closePickers() {
  showSourcePicker.value = false
  showTypePicker.value = false
  showDifficultyPicker.value = false
}

function goDetail(id: number) {
  uni.navigateTo({ url: `/pages/detail/index?id=${id}` })
}

// 触底加载更多
onReachBottom(() => {
  questionStore.loadMore()
})

onMounted(async () => {
  // 读取首页传入的 type 参数（题型筛选）
  const pages = getCurrentPages()
  const currentPage = pages[pages.length - 1] as any
  const typeParam = currentPage?.options?.type as QuestionType | undefined
  if (typeParam) {
    questionStore.filters.question_type = typeParam
  }

  // 加载来源列表（容错：失败不阻塞列表加载）
  try {
    sources.value = await listSources()
  } catch (e) {
    sources.value = []
  }

  await questionStore.fetchList(true)
})
</script>

<style scoped>
.list-page {
  min-height: 100vh;
  background: var(--bg-page, #f7f9fc);
}

/* 筛选区 */
.filter-bar {
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
.filter-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: var(--bg-secondary, #f0f2f5);
  border-radius: 16px;
  font-size: 13px;
  color: var(--text-primary, #2c3338);
}
.filter-item .arrow { font-size: 10px; color: var(--text-secondary, #999); }
.filter-clear {
  margin-left: auto;
  font-size: 13px;
  color: var(--primary-color, #1e3a5f);
}

/* 下拉选择 */
.picker-dropdown {
  position: fixed;
  top: 52px;
  left: 0;
  right: 0;
  background: var(--bg-card, #fff);
  z-index: 9;
  padding: 8px 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  max-height: 300px;
  overflow-y: auto;
}
.picker-item {
  padding: 10px 12px;
  font-size: 14px;
  color: var(--text-primary, #2c3338);
  border-radius: 6px;
}
.picker-item.active {
  color: var(--primary-color, #1e3a5f);
  font-weight: 600;
  background: var(--bg-primary-light, #e8f0fe);
}
.picker-mask {
  position: fixed;
  top: 52px;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.2);
  z-index: 8;
}

/* 列表内容 */
.list-content { padding: 12px; }

.skeleton-card {
  height: 80px;
  background: var(--bg-secondary, #e8e8e8);
  border-radius: 10px;
  margin-bottom: 10px;
  animation: pulse 1.5s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.loading-more, .no-more {
  text-align: center;
  padding: 16px;
  font-size: 13px;
  color: var(--text-secondary, #999);
}
</style>
