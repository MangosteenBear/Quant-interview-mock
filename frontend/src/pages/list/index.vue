<template>
  <view class="list-page">
    <!-- 题型筛选 chips（水平滚动） -->
    <scroll-view class="chips-bar" scroll-x>
      <view class="chips-inner">
        <view
          class="chip"
          :class="{ active: !filters.question_type }"
          @click="selectType(undefined)"
        >全部</view>
        <view
          v-for="(label, key) in typeOptions"
          :key="key"
          class="chip"
          :class="{ active: filters.question_type === key }"
          @click="selectType(key as any)"
        >{{ label }}</view>
      </view>
    </scroll-view>

    <!-- 统计行 + 筛选 pills -->
    <view class="meta-row">
      <text class="meta-count">{{ total }} 题 · 已做 {{ attemptedCount }}</text>
      <view class="filter-pills">
        <view class="pill" :class="{ active: !!filters.tag_name }" @click="showTagPicker = !showTagPicker">
          {{ filters.tag_name ? filters.tag_name.slice(0, 4) : '知识点' }} ▾
        </view>
        <view class="pill" :class="{ active: !!filters.difficulty }" @click="showDiffPicker = !showDiffPicker">
          {{ filters.difficulty ? `P${filters.difficulty}` : '难度' }} ▾
        </view>
        <view class="pill" :class="{ active: !!filters.source_id }" @click="showSourcePicker = !showSourcePicker">
          {{ currentSourceName || '来源' }} ▾
        </view>
        <view v-if="hasFilter" class="pill clear" @click="clearFilters">清除</view>
      </view>
    </view>

    <!-- 知识点下拉 -->
    <view v-if="showTagPicker" class="dropdown dropdown-left">
      <view class="drop-item" :class="{ active: !filters.tag_name }" @click="selectTag(undefined)">全部</view>
      <view v-for="t in availableTags" :key="t.id" class="drop-item" :class="{ active: filters.tag_name === t.name }" @click="selectTag(t.name)">{{ t.name }}</view>
    </view>

    <!-- 难度下拉 -->
    <view v-if="showDiffPicker" class="dropdown">
      <view class="drop-item" :class="{ active: !filters.difficulty }" @click="selectDifficulty(undefined)">全部</view>
      <view v-for="d in 5" :key="d" class="drop-item" :class="{ active: filters.difficulty === d }" @click="selectDifficulty(d)">P{{ d }}</view>
    </view>

    <!-- 来源下拉 -->
    <view v-if="showSourcePicker" class="dropdown">
      <view class="drop-item" :class="{ active: !filters.source_id }" @click="selectSource(undefined)">全部</view>
      <view v-for="s in sources" :key="s.id" class="drop-item" :class="{ active: filters.source_id === s.id }" @click="selectSource(s.id)">
        {{ s.book_title.slice(0, 22) }}
      </view>
    </view>

    <!-- 遮罩 -->
    <view v-if="showDiffPicker || showSourcePicker || showTagPicker" class="mask" @click="closePickers" />

    <!-- 列表 -->
    <view class="list-content">
      <view v-if="loading && list.length === 0">
        <view v-for="i in 5" :key="i" class="skeleton" />
      </view>
      <view v-else-if="list.length === 0">
        <EmptyState text="暂无题目" />
      </view>
      <view v-else>
        <QuestionCard
          v-for="(q, index) in list"
          :key="q.id"
          :question="q"
          @click="goDetail(q.id, index)"
        />
        <view v-if="loading" class="tip">加载中...</view>
        <view v-else-if="!hasMore && list.length > 0" class="tip">没有更多了</view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { onReachBottom, onShow } from '@dcloudio/uni-app'
import { useQuestionStore } from '@/stores/question'
import { useAttemptStore } from '@/stores/attempt'
import { listSources } from '@/api/source'
import { listTags } from '@/api/tag'
import { QUESTION_TYPE_LABELS } from '@/utils/difficulty'
import type { SourceBrief, TagBrief, QuestionType } from '@/types/api'
import QuestionCard from '@/components/QuestionCard.vue'
import EmptyState from '@/components/EmptyState.vue'

const questionStore = useQuestionStore()
const attemptStore = useAttemptStore()

const list = computed(() => questionStore.list)
const total = computed(() => questionStore.total)
const loading = computed(() => questionStore.loading)
const hasMore = computed(() => questionStore.hasMore)
const filters = computed(() => questionStore.filters)

const sources = ref<SourceBrief[]>([])
const availableTags = ref<TagBrief[]>([])
const showDiffPicker = ref(false)
const showSourcePicker = ref(false)
const showTagPicker = ref(false)
const typeOptions = QUESTION_TYPE_LABELS

const attemptedCount = computed(() => attemptStore.attemptedCount)

const hasFilter = computed(() => filters.value.source_id || filters.value.question_type || filters.value.difficulty || filters.value.tag_name)

const currentSourceName = computed(() => {
  const s = sources.value.find(s => s.id === filters.value.source_id)
  return s ? s.book_title.slice(0, 8) : ''
})

function selectType(type: QuestionType | undefined) {
  questionStore.filters.question_type = type
  questionStore.fetchList(true)
}
function selectSource(id: number | undefined) {
  questionStore.filters.source_id = id
  showSourcePicker.value = false
  questionStore.fetchList(true)
}
function selectDifficulty(d: number | undefined) {
  questionStore.filters.difficulty = d
  showDiffPicker.value = false
  questionStore.fetchList(true)
}
function selectTag(name: string | undefined) {
  questionStore.filters.tag_name = name
  showTagPicker.value = false
  questionStore.fetchList(true)
}
function clearFilters() {
  questionStore.resetFilters()
  questionStore.fetchList(true)
}
function closePickers() {
  showDiffPicker.value = false
  showSourcePicker.value = false
  showTagPicker.value = false
}

function goDetail(id: number, index: number) {
  questionStore.setCurrentIndex(index)
  uni.navigateTo({ url: `/pages/detail/index?id=${id}&index=${index}&total=${total.value}` })
}

onReachBottom(() => questionStore.loadMore())

onShow(async () => {
  // 首页点知识点标签后 switchTab 到此，需要重新拉取
  await questionStore.fetchList(true)
})

onMounted(async () => {
  attemptStore.init()
  const pages = getCurrentPages()
  const currentPage = pages[pages.length - 1] as any
  const typeParam = currentPage?.options?.type as QuestionType | undefined
  if (typeParam) questionStore.filters.question_type = typeParam

  try {
    const [srcs, tags] = await Promise.all([listSources(), listTags('topic')])
    sources.value = srcs
    availableTags.value = tags
  } catch {}
  await questionStore.fetchList(true)
})
</script>

<style scoped>
.list-page {
  min-height: 100vh;
  background: var(--bg-page, #f7f9fc);
}

/* chips 筛选栏 */
.chips-bar {
  background: var(--bg-card, #fff);
  border-bottom: 1px solid var(--border-color, #f0f0f0);
  white-space: nowrap;
}
.chips-inner {
  display: flex;
  gap: 8px;
  padding: 10px 12px;
}
.chip {
  display: inline-flex;
  align-items: center;
  padding: 5px 14px;
  border-radius: 16px;
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
  background: var(--bg-secondary, #f0f2f5);
  white-space: nowrap;
  flex-shrink: 0;
}
.chip.active {
  background: var(--primary-color, #1e3a5f);
  color: #fff;
}

/* 统计行 */
.meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--bg-card, #fff);
  border-bottom: 1px solid var(--border-color, #f0f0f0);
  position: sticky;
  top: 44px;
  z-index: 9;
}
.meta-count {
  font-size: 12px;
  color: var(--text-secondary, #888);
}
.filter-pills {
  display: flex;
  gap: 6px;
}
.pill {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 12px;
  border: 1px solid var(--border-color, #e0e0e0);
  color: var(--text-secondary, #6b7280);
  background: var(--bg-card, #fff);
}
.pill.active {
  color: var(--primary-color, #1e3a5f);
  border-color: var(--primary-color, #1e3a5f);
}
.pill.clear {
  color: #e24b4a;
  border-color: #e24b4a;
}

/* 下拉 */
.dropdown {
  position: fixed;
  top: 100px;
  right: 12px;
  background: var(--bg-card, #fff);
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
  z-index: 20;
  min-width: 120px;
  overflow: hidden;
}
.dropdown-left {
  right: auto;
  left: 12px;
  min-width: 100px;
  max-height: 280px;
  overflow-y: auto;
}
.drop-item {
  padding: 10px 16px;
  font-size: 14px;
  color: var(--text-primary, #2c3338);
  border-bottom: 1px solid var(--border-color, #f0f0f0);
}
.drop-item:last-child { border-bottom: none; }
.drop-item.active {
  color: var(--primary-color, #1e3a5f);
  font-weight: 600;
  background: var(--bg-secondary, #f0f2f5);
}

.mask {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.1);
  z-index: 19;
}

/* 列表 */
.list-content { padding: 10px 12px; }
.skeleton {
  height: 76px;
  background: var(--bg-secondary, #e8e8e8);
  border-radius: 10px;
  margin-bottom: 8px;
  animation: pulse 1.5s infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
.tip {
  text-align: center;
  padding: 16px;
  font-size: 13px;
  color: var(--text-secondary, #999);
}
</style>
