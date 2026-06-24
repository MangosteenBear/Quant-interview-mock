<!--
  题目详情与作答页（核心页面）
  布局：题干置顶 → 选项/作答区 → 判定结果 → 解析折叠
  功能：LaTeX 渲染、计时、作答提交、判对错、解析展开、收藏星标
-->
<template>
  <view class="detail-page">
    <!-- 骨架屏 -->
    <view v-if="detailLoading && !detail" class="skeleton">
      <view class="skeleton-line long"></view>
      <view class="skeleton-line mid"></view>
      <view class="skeleton-line short"></view>
    </view>

    <template v-if="detail">
      <!-- 题干区 -->
      <view class="stem-section">
        <view class="stem-header">
          <DifficultyTag :level="detail.difficulty" />
          <text class="type-label">{{ typeLabel }}</text>
          <text v-if="detail.book_chapter" class="chapter">{{ detail.book_chapter }}</text>
          <view class="fav-star" @click="onToggleFav">
            <text :class="{ active: isFav }">{{ isFav ? '★' : '☆' }}</text>
          </view>
        </view>
        <FormulaText :content="detail.stem_markdown" />
      </view>

      <!-- 作答区 -->
      <view v-if="!submitted" class="answer-section">
        <!-- 选择题 -->
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

        <!-- 填空题 -->
        <view v-else-if="detail.question_type === 'fill'" class="fill-input">
          <input
            v-model="fillAnswer"
            class="input-box"
            placeholder="输入答案"
            confirm-type="done"
          />
        </view>

        <!-- 简答/证明题 -->
        <view v-else class="short-input">
          <textarea
            v-model="shortAnswer"
            class="textarea-box"
            placeholder="输入你的解答（提交后展示参考答案）"
            :maxlength="-1"
            auto-height
          />
        </view>

        <button class="submit-btn" :disabled="!canSubmit" @click="onSubmit">
          提交作答
        </button>
      </view>

      <!-- 判定结果 -->
      <view v-if="submitted && attemptResult" class="result-section">
        <view class="result-banner" :class="resultClass">
          <text class="result-icon">{{ resultIcon }}</text>
          <text class="result-text">{{ resultText }}</text>
        </view>
        <view v-if="attemptResult.correct_answer" class="correct-answer">
          <text class="label">正确答案：</text>
          <FormulaText :content="attemptResult.correct_answer" />
        </view>
      </view>

      <!-- 解析区（折叠） -->
      <view v-if="submitted && attemptResult?.explanation" class="explanation-section">
        <view class="explanation-toggle" @click="showExplanation = !showExplanation">
          <text>查看解析</text>
          <text class="arrow">{{ showExplanation ? '▼' : '▶' }}</text>
        </view>
        <view v-if="showExplanation" class="explanation-content">
          <FormulaText :content="attemptResult.explanation" />
        </view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQuestionStore } from '@/stores/question'
import { useFavoriteStore } from '@/stores/favorite'
import { useSettingsStore } from '@/stores/settings'
import { QUESTION_TYPE_LABELS } from '@/utils/difficulty'
import FormulaText from '@/components/FormulaText.vue'
import DifficultyTag from '@/components/DifficultyTag.vue'

const questionStore = useQuestionStore()
const favoriteStore = useFavoriteStore()
const settingsStore = useSettingsStore()

// 作答状态
const selectedOptions = ref<Set<string>>(new Set())
const fillAnswer = ref('')
const shortAnswer = ref('')
const startTime = ref(0)
const showExplanation = ref(false)

// 收藏状态（本地乐观更新）
const isFav = ref(false)

const detail = computed(() => questionStore.detail)
const detailLoading = computed(() => questionStore.detailLoading)
const submitted = computed(() => questionStore.submitted)
const attemptResult = computed(() => questionStore.attemptResult)

const typeLabel = computed(() => {
  return detail.value ? QUESTION_TYPE_LABELS[detail.value.question_type] : ''
})

const canSubmit = computed(() => {
  if (!detail.value) return false
  switch (detail.value.question_type) {
    case 'choice': return selectedOptions.value.size > 0
    case 'fill': return fillAnswer.value.trim().length > 0
    case 'short':
    case 'proof': return shortAnswer.value.trim().length > 0
    default: return false
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
  if (selectedOptions.value.has(label)) {
    selectedOptions.value.delete(label)
  } else {
    selectedOptions.value.add(label)
  }
  // 触发响应式更新
  selectedOptions.value = new Set(selectedOptions.value)
}

async function onSubmit() {
  if (!detail.value) return
  let answer = ''
  switch (detail.value.question_type) {
    case 'choice':
      answer = Array.from(selectedOptions.value).sort().join(',')
      break
    case 'fill':
      answer = fillAnswer.value.trim()
      break
    case 'short':
    case 'proof':
      answer = shortAnswer.value.trim()
      break
  }
  const durationMs = Date.now() - startTime.value
  await questionStore.submitAnswer(answer, durationMs, settingsStore.deviceId)
}

async function onToggleFav() {
  if (!detail.value) return
  isFav.value = await favoriteStore.toggle(detail.value.id, settingsStore.deviceId)
}

onMounted(async () => {
  settingsStore.initDeviceId()
  // 从页面参数获取题目 ID
  const pages = getCurrentPages()
  const currentPage = pages[pages.length - 1] as any
  const questionId = parseInt(currentPage?.options?.id || '1', 10)

  startTime.value = Date.now()
  await questionStore.fetchDetail(questionId)

  // 初始化收藏状态（先预热收藏列表，确保 favoritedIds 已加载）
  if (favoriteStore.favoritedIds.size === 0) {
    await favoriteStore.fetchList(settingsStore.deviceId, true)
  }
  isFav.value = favoriteStore.isFavorited(questionId)
})
</script>

<style scoped>
.detail-page {
  min-height: 100vh;
  background: var(--bg-page, #f7f9fc);
  padding-bottom: 40px;
}

/* 骨架屏 */
.skeleton { padding: 20px; }
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

/* 题干区 */
.stem-section {
  background: var(--bg-card, #fff);
  padding: 16px;
  margin-bottom: 8px;
}
.stem-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.type-label, .chapter {
  font-size: 12px;
  color: var(--text-secondary, #6b7280);
  background: var(--bg-secondary, #f0f2f5);
  padding: 2px 8px;
  border-radius: 4px;
}
.fav-star {
  margin-left: auto;
  font-size: 22px;
  cursor: pointer;
}
.fav-star text { color: var(--text-secondary, #ccc); }
.fav-star text.active { color: #f5a623; }

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
  transition: all 0.2s;
}
.option-item.selected {
  border-color: var(--primary-color, #1e3a5f);
  background: var(--bg-primary-light, #e8f0fe);
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
.short-input .textarea-box {
  min-height: 120px;
  line-height: 1.6;
}

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
.submit-btn[disabled] {
  opacity: 0.5;
}

/* 判定结果 */
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

.correct-answer {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  padding: 8px 0;
}
.correct-answer .label {
  font-weight: 600;
  color: var(--text-primary, #2c3338);
  white-space: nowrap;
}

/* 解析区 */
.explanation-section {
  background: var(--bg-card, #fff);
  padding: 16px;
}
.explanation-toggle {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 15px;
  font-weight: 500;
  color: var(--primary-color, #1e3a5f);
  cursor: pointer;
}
.explanation-toggle .arrow { font-size: 12px; }
.explanation-content {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color, #e0e0e0);
}
</style>
