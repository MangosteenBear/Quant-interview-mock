<template>
  <view class="detail-page">
    <!-- 顶部导航 -->
    <view class="top-nav">
      <view class="nav-back" @click="goBack">
        <text class="nav-back-icon">←</text>
        <text class="nav-back-text">返回</text>
      </view>
      <text class="nav-progress">{{ indexLabel }}</text>
      <view class="fav-star" @click="onToggleFav">
        <text :class="{ active: isFav }">{{ isFav ? '★' : '☆' }}</text>
      </view>
    </view>

    <!-- 骨架屏 -->
    <view v-if="detailLoading && !detail" class="skeleton-wrap">
      <view class="skeleton-line long" />
      <view class="skeleton-line mid" />
      <view class="skeleton-line short" />
    </view>

    <template v-if="detail">
      <!-- 题干 -->
      <view class="stem-section">
        <view class="stem-tags">
          <DifficultyTag :level="detail.difficulty" />
          <text class="tag">{{ typeLabel }}</text>
          <text v-if="detail.book_chapter" class="tag">{{ detail.book_chapter }}</text>
        </view>
        <FormulaText :content="detail.stem_markdown" />
      </view>

      <!-- 作答区 -->
      <view v-if="!submitted" class="answer-section">
        <view v-if="detail.question_type === 'choice'" class="options">
          <view
            v-for="opt in detail.options"
            :key="opt.id"
            class="option-item"
            :class="{ selected: selectedOptions.has(opt.label) }"
            @click="toggleOption(opt.label)"
          >
            <text class="option-label">{{ opt.label }}</text>
            <FormulaText class="option-content" :content="opt.content_markdown" />
          </view>
        </view>
        <view v-else-if="detail.question_type === 'fill'" class="fill-input">
          <input v-model="fillAnswer" class="input-box" placeholder="输入答案" confirm-type="done" />
        </view>
        <view v-else class="short-input">
          <textarea v-model="shortAnswer" class="textarea-box" placeholder="输入你的解答（提交后展示参考答案）" :maxlength="-1" auto-height />
        </view>
        <button class="submit-btn" :disabled="!canSubmit" @click="onSubmit">提交作答</button>
      </view>

      <!-- 判定结果 -->
      <view v-if="submitted && attemptResult" class="result-section">
        <view class="result-banner" :class="resultClass">
          <text class="result-icon">{{ resultIcon }}</text>
          <text class="result-text">{{ resultText }}</text>
          <text v-if="durationSec" class="result-time">用时 {{ durationSec }} 秒</text>
        </view>
        <view v-if="attemptResult.correct_answer" class="correct-answer">
          <text class="label">正确答案：</text>
          <FormulaText :content="attemptResult.correct_answer" />
        </view>
      </view>

      <!-- 解析 -->
      <view v-if="submitted && attemptResult?.explanation" class="explanation-section">
        <view class="explanation-toggle" @click="showExplanation = !showExplanation">
          <text>查看解析</text>
          <text class="arrow">{{ showExplanation ? '▼' : '▶' }}</text>
        </view>
        <view v-if="showExplanation" class="explanation-content">
          <FormulaText :content="attemptResult.explanation" />
        </view>
      </view>

      <!-- 知识点标签 -->
      <view v-if="detail.tags && detail.tags.length" class="tags-section">
        <text v-for="tag in detail.tags.filter(t => t.type === 'knowledge')" :key="tag.id" class="kp-tag">{{ tag.name }}</text>
      </view>
    </template>

    <!-- 底部翻题导航 -->
    <view class="bottom-nav">
      <view class="nav-btn" :class="{ disabled: !hasPrev }" @click="goPrev">
        <text>← 上一题</text>
      </view>
      <text class="nav-center">{{ indexLabel }}</text>
      <view class="nav-btn right" :class="{ disabled: !hasNext }" @click="goNext">
        <text>下一题 →</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuestionStore } from '@/stores/question'
import { useFavoriteStore } from '@/stores/favorite'
import { useSettingsStore } from '@/stores/settings'
import { useAttemptStore } from '@/stores/attempt'
import { QUESTION_TYPE_LABELS } from '@/utils/difficulty'
import FormulaText from '@/components/FormulaText.vue'
import DifficultyTag from '@/components/DifficultyTag.vue'

const questionStore = useQuestionStore()
const favoriteStore = useFavoriteStore()
const settingsStore = useSettingsStore()
const attemptStore = useAttemptStore()

const selectedOptions = ref<Set<string>>(new Set())
const fillAnswer = ref('')
const shortAnswer = ref('')
const startTime = ref(0)
const showExplanation = ref(false)
const isFav = ref(false)
const durationSec = ref(0)

// 页面参数
const currentId = ref(0)
const currentIndex = ref(-1)
const total = ref(0)

const detail = computed(() => questionStore.detail)
const detailLoading = computed(() => questionStore.detailLoading)
const submitted = computed(() => questionStore.submitted)
const attemptResult = computed(() => questionStore.attemptResult)

const indexLabel = computed(() => total.value > 0 && currentIndex.value >= 0 ? `${currentIndex.value + 1} / ${total.value}` : '')
const hasPrev = computed(() => currentIndex.value > 0 && questionStore.list.length > 0)
const hasNext = computed(() => currentIndex.value >= 0 && currentIndex.value < questionStore.list.length - 1)

const typeLabel = computed(() => detail.value ? QUESTION_TYPE_LABELS[detail.value.question_type] : '')

const canSubmit = computed(() => {
  if (!detail.value) return false
  switch (detail.value.question_type) {
    case 'choice': return selectedOptions.value.size > 0
    case 'fill': return fillAnswer.value.trim().length > 0
    default: return shortAnswer.value.trim().length > 0
  }
})

const resultClass = computed(() => {
  if (!attemptResult.value) return ''
  if (attemptResult.value.is_correct === true) return 'correct'
  if (attemptResult.value.is_correct === false) return 'wrong'
  return 'neutral'
})
const resultIcon = computed(() => {
  if (!attemptResult.value) return ''
  if (attemptResult.value.is_correct === true) return '✓'
  if (attemptResult.value.is_correct === false) return '✗'
  return '○'
})
const resultText = computed(() => {
  if (!attemptResult.value) return ''
  if (attemptResult.value.is_correct === true) return '回答正确'
  if (attemptResult.value.is_correct === false) return '回答错误'
  return '参考答案'
})

function toggleOption(label: string) {
  if (selectedOptions.value.has(label)) selectedOptions.value.delete(label)
  else selectedOptions.value.add(label)
  selectedOptions.value = new Set(selectedOptions.value)
}

async function onSubmit() {
  if (!detail.value) return
  let answer = ''
  switch (detail.value.question_type) {
    case 'choice': answer = Array.from(selectedOptions.value).sort().join(','); break
    case 'fill': answer = fillAnswer.value.trim(); break
    default: answer = shortAnswer.value.trim()
  }
  const dur = Date.now() - startTime.value
  durationSec.value = Math.round(dur / 1000)
  const res = await questionStore.submitAnswer(answer, dur, settingsStore.deviceId)
  if (res && res.is_correct !== null) {
    attemptStore.record(detail.value.id, res.is_correct === true)
  }
}

async function onToggleFav() {
  if (!detail.value) return
  isFav.value = await favoriteStore.toggle(detail.value.id, settingsStore.deviceId)
}

function goBack() {
  uni.navigateBack()
}

async function navigateTo(index: number) {
  const q = questionStore.list[index]
  if (!q) return
  currentIndex.value = index
  currentId.value = q.id
  selectedOptions.value = new Set()
  fillAnswer.value = ''
  shortAnswer.value = ''
  showExplanation.value = false
  durationSec.value = 0
  startTime.value = Date.now()
  await questionStore.fetchDetail(q.id)
  isFav.value = favoriteStore.isFavorited(q.id)
}

function goPrev() {
  if (hasPrev.value) navigateTo(currentIndex.value - 1)
}
function goNext() {
  if (hasNext.value) navigateTo(currentIndex.value + 1)
}

onMounted(async () => {
  settingsStore.initDeviceId()
  attemptStore.init()
  const pages = getCurrentPages()
  const currentPage = pages[pages.length - 1] as any
  const opts = currentPage?.options || {}
  currentId.value = parseInt(opts.id || '1', 10)
  currentIndex.value = parseInt(opts.index ?? '-1', 10)
  total.value = parseInt(opts.total ?? '0', 10)

  startTime.value = Date.now()
  await questionStore.fetchDetail(currentId.value)

  if (favoriteStore.favoritedIds.size === 0) {
    await favoriteStore.fetchList(settingsStore.deviceId, true)
  }
  isFav.value = favoriteStore.isFavorited(currentId.value)
})
</script>

<style scoped>
.detail-page {
  min-height: 100vh;
  background: var(--bg-page, #f7f9fc);
  padding-bottom: 72px;
}

/* 顶部导航 */
.top-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-card, #fff);
  padding: 10px 16px;
  border-bottom: 1px solid var(--border-color, #f0f0f0);
  position: sticky;
  top: 0;
  z-index: 10;
}
.nav-back {
  display: flex;
  align-items: center;
  gap: 4px;
}
.nav-back-icon { font-size: 16px; color: var(--text-secondary, #888); }
.nav-back-text { font-size: 14px; color: var(--text-secondary, #888); }
.nav-progress { font-size: 14px; font-weight: 500; color: var(--primary-color, #1e3a5f); }
.fav-star { font-size: 22px; cursor: pointer; }
.fav-star text { color: var(--text-secondary, #ccc); }
.fav-star text.active { color: #f5a623; }

/* 骨架屏 */
.skeleton-wrap { padding: 20px; }
.skeleton-line {
  height: 16px;
  background: var(--bg-secondary, #e8e8e8);
  border-radius: 4px;
  margin-bottom: 12px;
  animation: pulse 1.5s infinite;
}
.skeleton-line.long { width: 100%; }
.skeleton-line.mid { width: 70%; }
.skeleton-line.short { width: 40%; }
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 题干 */
.stem-section {
  background: var(--bg-card, #fff);
  padding: 16px;
  margin-bottom: 8px;
}
.stem-tags {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.tag {
  font-size: 12px;
  color: var(--text-secondary, #6b7280);
  background: var(--bg-secondary, #f0f2f5);
  padding: 2px 8px;
  border-radius: 4px;
}

/* 作答区 */
.answer-section {
  background: var(--bg-card, #fff);
  padding: 16px;
  margin-bottom: 8px;
}
.options { display: flex; flex-direction: column; gap: 10px; }
.option-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px;
  border: 2px solid var(--border-color, #e0e0e0);
  border-radius: 8px;
}
.option-item.selected {
  border-color: var(--primary-color, #1e3a5f);
  background: #e8f0fe;
}
.option-label {
  font-weight: 600;
  font-size: 16px;
  color: var(--primary-color, #1e3a5f);
  min-width: 24px;
}
.option-content { flex: 1; }
.fill-input .input-box,
.short-input .textarea-box {
  width: 100%;
  padding: 12px;
  border: 2px solid var(--border-color, #e0e0e0);
  border-radius: 8px;
  font-size: 16px;
  background: var(--bg-input, #fff);
  color: var(--text-primary, #2c3338);
  box-sizing: border-box;
}
.short-input .textarea-box { min-height: 120px; line-height: 1.6; }
.submit-btn {
  margin-top: 16px;
  width: 100%;
  height: 44px;
  line-height: 44px;
  background: var(--primary-color, #1e3a5f);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
}
.submit-btn[disabled] { opacity: 0.5; }

/* 结果 */
.result-section {
  background: var(--bg-card, #fff);
  padding: 16px;
  margin-bottom: 8px;
}
.result-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 12px;
}
.result-banner.correct { background: #d4edda; color: #155724; }
.result-banner.wrong { background: #f8d7da; color: #721c24; }
.result-banner.neutral { background: #e2e3e5; color: #6c757d; }
.result-icon { font-size: 20px; font-weight: bold; }
.result-text { font-size: 16px; font-weight: 500; }
.result-time { margin-left: auto; font-size: 12px; opacity: .8; }
.correct-answer {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  padding: 8px 0;
}
.correct-answer .label { font-weight: 600; white-space: nowrap; }

/* 解析 */
.explanation-section {
  background: var(--bg-card, #fff);
  padding: 16px;
  margin-bottom: 8px;
}
.explanation-toggle {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 15px;
  font-weight: 500;
  color: var(--primary-color, #1e3a5f);
}
.explanation-content {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color, #e0e0e0);
}

/* 知识点标签 */
.tags-section {
  padding: 12px 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.kp-tag {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 12px;
  background: #e8f0fe;
  color: var(--primary-color, #1e3a5f);
  border: 1px solid #c5d6f5;
}

/* 底部导航 */
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-card, #fff);
  border-top: 1px solid var(--border-color, #f0f0f0);
  padding: 12px 20px;
  z-index: 10;
}
.nav-btn {
  font-size: 14px;
  color: var(--primary-color, #1e3a5f);
  font-weight: 500;
  padding: 6px 0;
}
.nav-btn.disabled { color: var(--text-secondary, #ccc); pointer-events: none; }
.nav-center { font-size: 13px; color: var(--text-secondary, #888); }
</style>
