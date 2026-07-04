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
      <view class="answer-section">
        <!-- 选择题：提交前可点击，提交后只读+对错高亮 -->
        <view v-if="detail.question_type === 'choice'" class="options">
          <view
            v-for="opt in detail.options"
            :key="opt.id"
            class="option-item"
            :class="optionClass(opt.label)"
            @click="submitted ? undefined : toggleOption(opt.label)"
          >
            <text class="option-label">{{ opt.label }}</text>
            <FormulaText class="option-content" :content="opt.content_markdown" />
            <text v-if="submitted && isCorrectOption(opt.label)" class="opt-badge opt-correct">✓</text>
            <text v-else-if="submitted && selectedOptions.has(opt.label) && !isCorrectOption(opt.label)" class="opt-badge opt-wrong">✗</text>
          </view>
        </view>
        <!-- 填空题 -->
        <view v-else-if="detail.question_type === 'fill'" class="fill-input">
          <view v-if="fillBlanks.length > 1" class="multi-blank">
            <view v-for="(_, i) in fillBlanks" :key="i" class="blank-row">
              <text class="blank-label">第 {{ i + 1 }} 空</text>
              <input v-model="fillBlanks[i]" class="input-box" :disabled="submitted" :placeholder="`填写第 ${i + 1} 空`" confirm-type="done" />
            </view>
          </view>
          <input v-else v-model="fillBlanks[0]" class="input-box" :disabled="submitted" placeholder="输入答案" confirm-type="done" />
        </view>
        <!-- 简答/证明 -->
        <view v-else class="short-input">
          <textarea v-if="!submitted" v-model="shortAnswer" class="textarea-box" placeholder="输入解答思路（选填）" :maxlength="-1" auto-height />
        </view>
        <!-- 提交按钮 -->
        <view v-if="!submitted" class="submit-row">
          <button class="submit-btn" :disabled="!canSubmit" @click="onSubmit">提交作答</button>
          <button v-if="detail.question_type === 'short'" class="peek-btn" @click="onPeek">直接看答案</button>
        </view>
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
        <text v-for="tag in detail.tags.filter(t => t.type === 'topic')" :key="tag.id" class="kp-tag">{{ tag.name }}</text>
      </view>

      <!-- 举报入口 -->
      <view class="report-section">
        <text class="report-btn" @click="showReportSheet = true">⚑ 题目有问题</text>
      </view>
    </template>

    <!-- 举报弹窗 -->
    <view v-if="showReportSheet" class="report-mask" @click.self="showReportSheet = false">
      <view class="report-sheet">
        <text class="report-sheet-title">反馈问题类型</text>
        <view class="report-options">
          <view v-for="opt in reportOptions" :key="opt.value"
            class="report-option"
            :class="{ selected: reportReason === opt.value }"
            @click="reportReason = opt.value">
            {{ opt.label }}
          </view>
        </view>
        <button class="report-submit-btn" :disabled="!reportReason || reportSent" @click="submitReport">
          {{ reportSent ? '✅ 已提交，感谢反馈' : '提交反馈' }}
        </button>
        <text class="report-cancel" @click="showReportSheet = false">取消</text>
      </view>
    </view>

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
import { getAdjacentQuestions } from '@/api/question'

const questionStore = useQuestionStore()
const favoriteStore = useFavoriteStore()
const settingsStore = useSettingsStore()
const attemptStore = useAttemptStore()

const selectedOptions = ref<Set<string>>(new Set())
const fillBlanks = ref<string[]>([''])
const shortAnswer = ref('')
const startTime = ref(0)
const showExplanation = ref(false)
const isFav = ref(false)
const durationSec = ref(0)
const showReportSheet = ref(false)
const reportReason = ref('')
const reportSent = ref(false)
const reportOptions = [
  { value: 'wrong_answer', label: '答案有误' },
  { value: 'bad_options', label: '选项有问题' },
  { value: 'garbled', label: '题目乱码/排版错误' },
  { value: 'other', label: '其他问题' },
]

// 页面参数
const currentId = ref(0)
const currentIndex = ref(-1)
const total = ref(0)
const prevId = ref<number | null>(null)
const nextId = ref<number | null>(null)

const detail = computed(() => questionStore.detail)
const detailLoading = computed(() => questionStore.detailLoading)
const submitted = computed(() => questionStore.submitted)
const attemptResult = computed(() => questionStore.attemptResult)

const indexLabel = computed(() => total.value > 0 && currentIndex.value >= 0 ? `${currentIndex.value + 1} / ${total.value}` : '')
const hasPrev = computed(() => {
  if (questionStore.list.length > 0) return currentIndex.value > 0
  return prevId.value !== null
})
const hasNext = computed(() => {
  if (questionStore.list.length > 0) return currentIndex.value >= 0 && currentIndex.value < questionStore.list.length - 1
  return nextId.value !== null
})

const typeLabel = computed(() => detail.value ? QUESTION_TYPE_LABELS[detail.value.question_type] : '')

const canSubmit = computed(() => {
  if (!detail.value) return false
  switch (detail.value.question_type) {
    case 'choice': return selectedOptions.value.size > 0
    case 'fill': return fillBlanks.value.some(b => b.trim().length > 0)
    default: return shortAnswer.value.trim().length > 0
  }
})

// 获取选择题正确答案集合（提交后从 attemptResult 中的 correct_answer 字段反推，
// 但更可靠的是在提交时记录）
const correctOptionLabels = ref<Set<string>>(new Set())

function isCorrectOption(label: string) {
  return correctOptionLabels.value.has(label)
}

function optionClass(label: string) {
  if (!submitted.value) {
    return { selected: selectedOptions.value.has(label) }
  }
  const isSelected = selectedOptions.value.has(label)
  const isCorrect = correctOptionLabels.value.has(label)
  return {
    'opt-revealed-correct': isCorrect,
    'opt-revealed-wrong': isSelected && !isCorrect,
    'selected': isSelected,
  }
}

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
    case 'fill': answer = fillBlanks.value.map(b => b.trim()).join('|'); break
    default: answer = shortAnswer.value.trim()
  }
  const dur = Date.now() - startTime.value
  durationSec.value = Math.round(dur / 1000)
  const res = await questionStore.submitAnswer(answer, dur, settingsStore.deviceId)
  if (res && res.is_correct !== null) {
    attemptStore.record(detail.value.id, res.is_correct === true)
  }
  // 从 correct_answer 中解析正确选项标签 (格式: "正确答案 A：xxx  /  正确答案 B：xxx")
  if (detail.value.question_type === 'choice' && res?.correct_answer) {
    const matches = res.correct_answer.matchAll(/正确答案\s+([A-D])：/g)
    correctOptionLabels.value = new Set([...matches].map(m => m[1]))
  }
}

async function onPeek() {
  if (!detail.value) return
  // 以空字符串提交，仅触发"查看答案"流程（is_correct 为 null）
  const dur = Date.now() - startTime.value
  durationSec.value = 0
  const res = await questionStore.submitAnswer('', dur, settingsStore.deviceId)
  // 简答题 peek 不记录对错
}

async function onToggleFav() {
  if (!detail.value) return
  isFav.value = await favoriteStore.toggle(detail.value.id, settingsStore.deviceId)
}

async function submitReport() {
  if (!detail.value || !reportReason.value) return
  try {
    await fetch(`/api/questions/${detail.value.id}/report`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ device_id: settingsStore.deviceId, reason: reportReason.value }),
    })
    reportSent.value = true
    setTimeout(() => { showReportSheet.value = false; reportSent.value = false; reportReason.value = '' }, 1500)
  } catch (e) { /* silent */ }
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
  correctOptionLabels.value = new Set()
  fillBlanks.value = ['']
  shortAnswer.value = ''
  showExplanation.value = false
  durationSec.value = 0
  showReportSheet.value = false
  reportReason.value = ''
  reportSent.value = false
  startTime.value = Date.now()
  await questionStore.fetchDetail(q.id)
  // 根据 stem 中 ___N___ 数量初始化输入框
  if (questionStore.detail?.question_type === 'fill') {
    const matches = (questionStore.detail.stem_markdown || '').match(/___[①-⑨\d]+___/g)
    const count = matches ? matches.length : 1
    fillBlanks.value = Array(count).fill('')
  }
  isFav.value = favoriteStore.isFavorited(q.id)
}

async function navigateById(id: number) {
  currentId.value = id
  currentIndex.value = -1
  selectedOptions.value = new Set()
  correctOptionLabels.value = new Set()
  fillBlanks.value = ['']
  shortAnswer.value = ''
  showExplanation.value = false
  durationSec.value = 0
  showReportSheet.value = false
  reportReason.value = ''
  reportSent.value = false
  startTime.value = Date.now()
  await questionStore.fetchDetail(id)
  if (questionStore.detail?.question_type === 'fill') {
    const matches = (questionStore.detail.stem_markdown || '').match(/___[①-⑨\d]+___/g)
    fillBlanks.value = Array(matches ? matches.length : 1).fill('')
  }
  isFav.value = favoriteStore.isFavorited(id)
  const adj = await getAdjacentQuestions(id)
  prevId.value = adj.prev_id
  nextId.value = adj.next_id
}

function goPrev() {
  if (!hasPrev.value) return
  if (questionStore.list.length > 0) navigateTo(currentIndex.value - 1)
  else if (prevId.value) navigateById(prevId.value)
}
function goNext() {
  if (!hasNext.value) return
  if (questionStore.list.length > 0) navigateTo(currentIndex.value + 1)
  else if (nextId.value) navigateById(nextId.value)
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
  if (questionStore.detail?.question_type === 'fill') {
    const matches = (questionStore.detail.stem_markdown || '').match(/___[①-⑨\d]+___/g)
    fillBlanks.value = Array(matches ? matches.length : 1).fill('')
  }

  if (favoriteStore.favoritedIds.size === 0) {
    await favoriteStore.fetchList(settingsStore.deviceId, true)
  }
  isFav.value = favoriteStore.isFavorited(currentId.value)

  // 当无列表上下文时（随机/每日/收藏入口），用 adjacent API 激活前后题按钮
  if (questionStore.list.length === 0) {
    const adj = await getAdjacentQuestions(currentId.value)
    prevId.value = adj.prev_id
    nextId.value = adj.next_id
  }
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
.option-item.opt-revealed-correct {
  border-color: #1d9e75;
  background: #e8f9f3;
}
.option-item.opt-revealed-wrong {
  border-color: #e24b4a;
  background: #fdf0f0;
}
.opt-badge {
  font-size: 16px;
  font-weight: 700;
  margin-left: auto;
  flex-shrink: 0;
}
.opt-badge.opt-correct { color: #1d9e75; }
.opt-badge.opt-wrong { color: #e24b4a; }
.submit-row {
  margin-top: 16px;
  display: flex;
  gap: 10px;
}
.submit-row .submit-btn { flex: 2; margin-top: 0; }
.peek-btn {
  flex: 1;
  height: 44px;
  line-height: 44px;
  background: var(--bg-secondary, #f0f2f5);
  color: var(--text-primary, #2c3338);
  border: none;
  border-radius: 8px;
  font-size: 14px;
}
.option-label {
  font-weight: 600;
  font-size: 16px;
  color: var(--primary-color, #1e3a5f);
  min-width: 24px;
}
.option-content { flex: 1; }
.multi-blank { display: flex; flex-direction: column; gap: 10px; }
.blank-row { display: flex; align-items: center; gap: 8px; }
.blank-label { font-size: 13px; color: var(--text-secondary, #888); white-space: nowrap; min-width: 44px; }
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

/* 举报入口 */
.report-section {
  padding: 8px 16px 16px;
  text-align: right;
}
.report-btn {
  font-size: 12px;
  color: var(--text-secondary, #aaa);
  cursor: pointer;
}
.report-btn:hover { color: #e24b4a; }

/* 举报弹窗 */
.report-mask {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  z-index: 100;
  display: flex;
  align-items: flex-end;
}
.report-sheet {
  background: var(--bg-card, #fff);
  border-radius: 16px 16px 0 0;
  padding: 20px 16px 32px;
  width: 100%;
}
.report-sheet-title {
  font-size: 16px;
  font-weight: 600;
  display: block;
  text-align: center;
  margin-bottom: 16px;
  color: var(--text-primary, #2c3338);
}
.report-options { display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px; }
.report-option {
  padding: 12px 16px;
  border: 1.5px solid var(--border-color, #e0e0e0);
  border-radius: 10px;
  font-size: 14px;
  cursor: pointer;
  color: var(--text-primary, #2c3338);
}
.report-option.selected {
  border-color: var(--primary-color, #1e3a5f);
  background: #e8f0fe;
  color: var(--primary-color, #1e3a5f);
  font-weight: 500;
}
.report-submit-btn {
  width: 100%;
  height: 44px;
  background: var(--primary-color, #1e3a5f);
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 500;
  margin-bottom: 12px;
}
.report-submit-btn[disabled] { opacity: 0.5; }
.report-cancel {
  display: block;
  text-align: center;
  font-size: 14px;
  color: var(--text-secondary, #888);
  cursor: pointer;
  padding: 4px;
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
