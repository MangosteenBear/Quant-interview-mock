<template>
  <view class="index-page">
    <!-- 打招呼 -->
    <view class="hero">
      <text class="greeting">{{ greeting }}，今天加油</text>
      <text v-if="streak > 0" class="streak">🔥 {{ streak }} 天连续</text>
    </view>

    <!-- 进度卡 -->
    <view class="progress-card" @click="goList">
      <view class="ring-wrap">
        <svg width="64" height="64" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
          <circle cx="32" cy="32" r="26" fill="none" stroke="rgba(255,255,255,0.25)" stroke-width="6"/>
          <circle cx="32" cy="32" r="26" fill="none" stroke="#fff" stroke-width="6"
            :stroke-dasharray="`${completePct * 1.634} 163.4`"
            stroke-dashoffset="40.85" stroke-linecap="round"/>
        </svg>
        <text class="ring-pct">{{ completePct }}%</text>
      </view>
      <view class="ring-stats">
        <text class="stat-main">已做 {{ attemptedCount }} / {{ totalQuestions }} 题</text>
        <text class="stat-sub">答对 {{ correctCount }} 题</text>
        <text class="stat-action">开始刷题 →</text>
      </view>
    </view>

    <!-- 今日推荐 -->
    <text class="section-title">今日推荐</text>
    <view v-if="dailyQuestion" class="recommend-card" @click="goDailyQuestion">
      <view class="recommend-tags">
        <text v-if="dailyQuestion.difficulty" class="tag">P{{ dailyQuestion.difficulty }}</text>
        <text v-if="dailyQuestion.book_chapter" class="tag">{{ dailyQuestion.book_chapter }}</text>
        <text class="tag">{{ typeLabel(dailyQuestion.question_type) }}</text>
      </view>
      <text class="recommend-preview">{{ plainStem(dailyQuestion.stem_markdown) }}</text>
      <text class="recommend-btn">开始练习 →</text>
    </view>

    <!-- 按知识点 -->
    <text class="section-title">按知识点</text>
    <view class="cat-grid">
      <view v-for="tag in topTags" :key="tag.id" class="cat-item" @click="goListWithTag(tag.name)">
        <text class="cat-name">{{ tag.name }}</text>
        <text class="cat-arrow">→</text>
      </view>
    </view>

    <!-- 快捷操作 -->
    <view class="quick-row">
      <view class="quick-btn" @click="goSearch">
        <text class="quick-icon">🔍</text>
        <text class="quick-text">搜索</text>
      </view>
      <view class="quick-btn" @click="goFavorites">
        <text class="quick-icon">⭐</text>
        <text class="quick-text">收藏</text>
      </view>
      <view class="quick-btn" @click="goRandom">
        <text class="quick-icon">🎲</text>
        <text class="quick-text">随机题</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { listQuestions } from '@/api/question'
import { listTags } from '@/api/tag'
import { useAttemptStore } from '@/stores/attempt'
import { QUESTION_TYPE_LABELS } from '@/utils/difficulty'
import type { QuestionListItem, TagBrief } from '@/types/api'

const attemptStore = useAttemptStore()
const totalQuestions = ref(0)
const allQuestions = ref<QuestionListItem[]>([])
const topTags = ref<TagBrief[]>([])

const attemptedCount = computed(() => attemptStore.attemptedCount)
const correctCount = computed(() => attemptStore.correctCount)
const streak = computed(() => attemptStore.streak)

const completePct = computed(() =>
  totalQuestions.value > 0 ? Math.round((attemptedCount.value / totalQuestions.value) * 100) : 0
)

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return '早上好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const dailyQuestion = computed(() => {
  if (!allQuestions.value.length) return null
  const unattempted = allQuestions.value.filter(q => !attemptStore.getStatus(q.id))
  const pool = unattempted.length > 0 ? unattempted : allQuestions.value
  const seed = Math.floor(Date.now() / 86400000)
  return pool[seed % pool.length]
})

function typeLabel(type: string) {
  return QUESTION_TYPE_LABELS[type] || type
}

function plainStem(md: string) {
  return md.replace(/\$+/g, '').replace(/\\[a-zA-Z]+/g, '').replace(/[{}]/g, '').replace(/\n/g, ' ').trim().slice(0, 50) + '...'
}

function goList() {
  uni.switchTab({ url: '/pages/list/index' })
}

function goListWithTag(tagName: string) {
  uni.switchTab({ url: '/pages/list/index' })
}

function goSearch() {
  uni.navigateTo({ url: '/pages/search/index' })
}

function goFavorites() {
  uni.navigateTo({ url: '/pages/favorites/index' })
}

function goDailyQuestion() {
  if (!dailyQuestion.value) return
  const idx = allQuestions.value.findIndex(q => q.id === dailyQuestion.value!.id)
  uni.navigateTo({ url: `/pages/detail/index?id=${dailyQuestion.value.id}&index=${idx}&total=${totalQuestions.value}` })
}

function goRandom() {
  if (!allQuestions.value.length) return
  const q = allQuestions.value[Math.floor(Math.random() * allQuestions.value.length)]
  const idx = allQuestions.value.indexOf(q)
  uni.navigateTo({ url: `/pages/detail/index?id=${q.id}&index=${idx}&total=${totalQuestions.value}` })
}

onMounted(async () => {
  attemptStore.init()
  attemptStore.loadStreak()
  try {
    const [res, tags] = await Promise.all([
      listQuestions({ page: 1, page_size: 100 }),
      listTags('knowledge'),
    ])
    totalQuestions.value = res.total
    allQuestions.value = res.items
    topTags.value = tags.slice(0, 4)
  } catch {}
})
</script>

<style scoped>
.index-page {
  min-height: 100vh;
  background: var(--bg-page, #f7f9fc);
  padding: 20px 16px 32px;
}

.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.greeting {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary, #2c3338);
}
.streak {
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
  background: var(--bg-card, #fff);
  padding: 4px 10px;
  border-radius: 12px;
}

.progress-card {
  display: flex;
  align-items: center;
  gap: 16px;
  background: linear-gradient(135deg, #1e3a5f, #2d5a4f);
  padding: 20px;
  border-radius: 16px;
  margin-bottom: 24px;
  box-shadow: 0 4px 12px rgba(30, 58, 95, 0.2);
}
.ring-wrap {
  position: relative;
  width: 64px;
  height: 64px;
  flex-shrink: 0;
}
.ring-pct {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
}
.ring-stats {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.stat-main { font-size: 16px; font-weight: 600; color: #fff; }
.stat-sub { font-size: 13px; color: rgba(255,255,255,0.75); }
.stat-action { font-size: 12px; color: rgba(255,255,255,0.6); margin-top: 4px; }

.section-title {
  display: block;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary, #2c3338);
  margin-bottom: 10px;
}

.recommend-card {
  background: var(--bg-card, #fff);
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 24px;
  border-left: 3px solid var(--primary-color, #1e3a5f);
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.recommend-tags {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
}
.tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--bg-secondary, #f0f2f5);
  color: var(--text-secondary, #6b7280);
}
.recommend-preview {
  display: block;
  font-size: 14px;
  color: var(--text-primary, #2c3338);
  line-height: 1.6;
  margin-bottom: 10px;
}
.recommend-btn {
  font-size: 13px;
  font-weight: 500;
  color: var(--primary-color, #1e3a5f);
}

.cat-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 24px;
}
.cat-item {
  background: var(--bg-card, #fff);
  border-radius: 10px;
  padding: 14px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.cat-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #2c3338);
}
.cat-arrow {
  font-size: 13px;
  color: var(--text-secondary, #ccc);
}

.quick-row {
  display: flex;
  gap: 12px;
}
.quick-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 14px 0;
  background: var(--bg-card, #fff);
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.quick-icon { font-size: 22px; }
.quick-text { font-size: 12px; color: var(--text-primary, #2c3338); }
</style>
