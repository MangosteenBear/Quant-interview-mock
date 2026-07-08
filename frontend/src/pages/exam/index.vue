<!--
  模考模式（轻量版）：配置 → 顺序作答 → 成绩报告
  仅 choice/fill（可自动判分），作答同步计入做题记录
-->
<template>
  <view class="exam-page">
    <!-- 阶段一：配置 -->
    <view v-if="phase === 'config'" class="config-card">
      <text class="config-title">模拟考试</text>
      <text class="config-sub">随机抽题 · 顺序作答 · 自动判分</text>

      <text class="config-label">题目数量</text>
      <view class="opt-row">
        <view v-for="n in [10, 20, 30]" :key="n" class="opt" :class="{ active: cfg.count === n }" @click="cfg.count = n">{{ n }} 题</view>
      </view>

      <text class="config-label">题型</text>
      <view class="opt-row">
        <view v-for="t in typeOpts" :key="t.value" class="opt" :class="{ active: cfg.type === t.value }" @click="cfg.type = t.value">{{ t.label }}</view>
      </view>

      <text class="config-label">限时</text>
      <view class="opt-row">
        <view v-for="l in limitOpts" :key="l.label" class="opt" :class="{ active: cfg.limit === l.value }" @click="cfg.limit = l.value">{{ l.label }}</view>
      </view>

      <button class="start-btn" :disabled="starting" @click="onStart">{{ starting ? '抽题中…' : '开始模考' }}</button>
    </view>

    <!-- 阶段二：作答 -->
    <view v-else-if="phase === 'taking'" class="taking">
      <view class="taking-header">
        <text class="progress-text">{{ currentIdx + 1 }} / {{ questionIds.length }}</text>
        <text v-if="remainSec !== null" class="timer" :class="{ urgent: remainSec < 60 }">⏱ {{ fmtTime(remainSec) }}</text>
      </view>
      <view class="progress-track">
        <view class="progress-fill" :style="{ width: ((currentIdx + 1) / questionIds.length * 100) + '%' }" />
      </view>

      <view v-if="current" class="q-card">
        <FormulaText :content="current.stem_markdown" />

        <!-- 选择题 -->
        <view v-if="current.question_type === 'choice'" class="options">
          <view
            v-for="opt in current.options"
            :key="opt.id"
            class="option"
            :class="{ selected: answers[current.id] === opt.label }"
            @click="answers[current.id] = opt.label"
          >
            <text class="opt-label">{{ opt.label }}</text>
            <FormulaText :content="opt.content_markdown" class="opt-content" />
          </view>
        </view>

        <!-- 填空题 -->
        <view v-else class="fill-area">
          <input
            :value="answers[current.id] || ''"
            class="fill-input"
            placeholder="输入答案"
            @input="(e: any) => (answers[current.id] = e.detail.value)"
          />
        </view>
      </view>
      <view v-else class="q-loading">加载中…</view>

      <view class="taking-footer">
        <button v-if="currentIdx > 0" class="nav-btn ghost" @click="currentIdx--">上一题</button>
        <button v-if="currentIdx < questionIds.length - 1" class="nav-btn" @click="currentIdx++">下一题</button>
        <button v-else class="nav-btn submit" :disabled="submitting" @click="onSubmit">{{ submitting ? '判分中…' : '交卷' }}</button>
      </view>
    </view>

    <!-- 阶段三：报告 -->
    <view v-else-if="phase === 'report' && report" class="report">
      <view class="score-card">
        <text class="score-big">{{ report.correct }} / {{ report.total }}</text>
        <text class="score-label">正确率 {{ Math.round(report.accuracy * 100) }}%{{ report.duration_sec ? ` · 用时 ${fmtTime(report.duration_sec)}` : '' }}</text>
      </view>

      <text class="report-section-title">答题明细</text>
      <view
        v-for="(d, i) in report.details"
        :key="d.question_id"
        class="detail-row"
        @click="uni.navigateTo({ url: `/pages/detail/index?id=${d.question_id}` })"
      >
        <text class="detail-icon">{{ d.is_correct ? '✅' : '❌' }}</text>
        <view class="detail-body">
          <text class="detail-stem">{{ i + 1 }}. {{ plain(d.stem) }}</text>
          <text v-if="!d.is_correct && d.correct_answer" class="detail-answer">正确答案：{{ d.correct_answer }}</text>
        </view>
      </view>

      <button class="start-btn" @click="reset">再来一次</button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onUnmounted } from 'vue'
import { startExam, submitExam, type ExamReport } from '@/api/exam'
import { getQuestionDetail } from '@/api/question'
import { useSettingsStore } from '@/stores/settings'
import FormulaText from '@/components/FormulaText.vue'
import type { QuestionDetail } from '@/types/api'

const settings = useSettingsStore()

const phase = ref<'config' | 'taking' | 'report'>('config')
const cfg = reactive({ count: 10, type: 'mixed', limit: null as number | null })
const typeOpts = [
  { value: 'mixed', label: '混合' },
  { value: 'choice', label: '选择题' },
  { value: 'fill', label: '填空题' },
]
const limitOpts = [
  { value: null, label: '不限时' },
  { value: 600, label: '10 分钟' },
  { value: 1200, label: '20 分钟' },
  { value: 1800, label: '30 分钟' },
]

const starting = ref(false)
const submitting = ref(false)
const examId = ref(0)
const questionIds = ref<number[]>([])
const currentIdx = ref(0)
const answers = reactive<Record<number, string>>({})
const detailCache = reactive<Record<number, QuestionDetail>>({})
const report = ref<ExamReport | null>(null)
const remainSec = ref<number | null>(null)
const startedAt = ref(0)
let timer: ReturnType<typeof setInterval> | null = null

const current = computed(() => detailCache[questionIds.value[currentIdx.value]] || null)

watch(currentIdx, (idx) => {
  const qid = questionIds.value[idx]
  if (qid && !detailCache[qid]) loadDetail(qid)
  // 预取下一题
  const next = questionIds.value[idx + 1]
  if (next && !detailCache[next]) loadDetail(next)
})

async function loadDetail(qid: number) {
  try {
    detailCache[qid] = (await getQuestionDetail(qid)) as QuestionDetail
  } catch { /* toast 已弹 */ }
}

async function onStart() {
  starting.value = true
  settings.initDeviceId()
  try {
    const res = await startExam({
      device_id: settings.deviceId,
      count: cfg.count,
      question_type: cfg.type,
      time_limit_sec: cfg.limit || undefined,
    })
    examId.value = res.id
    questionIds.value = res.question_ids
    currentIdx.value = 0
    startedAt.value = Date.now()
    phase.value = 'taking'
    loadDetail(res.question_ids[0])
    if (res.question_ids[1]) loadDetail(res.question_ids[1])
    if (cfg.limit) {
      remainSec.value = cfg.limit
      timer = setInterval(() => {
        remainSec.value!--
        if (remainSec.value! <= 0) {
          uni.showToast({ title: '时间到，自动交卷', icon: 'none' })
          onSubmit()
        }
      }, 1000)
    }
  } catch { /* toast 已弹 */ } finally {
    starting.value = false
  }
}

async function onSubmit() {
  if (submitting.value) return
  submitting.value = true
  if (timer) { clearInterval(timer); timer = null }
  try {
    report.value = await submitExam(examId.value, {
      device_id: settings.deviceId,
      answers: questionIds.value
        .filter(qid => answers[qid])
        .map(qid => ({ question_id: qid, answer: answers[qid] })),
      duration_sec: Math.round((Date.now() - startedAt.value) / 1000),
    })
    phase.value = 'report'
  } catch { /* toast 已弹 */ } finally {
    submitting.value = false
  }
}

function reset() {
  phase.value = 'config'
  report.value = null
  questionIds.value = []
  remainSec.value = null
  Object.keys(answers).forEach(k => delete answers[Number(k)])
}

function fmtTime(sec: number) {
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

function plain(md: string) {
  return md.replace(/\$+/g, '').replace(/\\[a-zA-Z]+/g, '').replace(/[{}]/g, '').slice(0, 60)
}

onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.exam-page {
  min-height: 100vh;
  background: var(--bg-page, #f7f9fc);
  padding: 24rpx;
}

/* 配置 */
.config-card {
  display: flex;
  flex-direction: column;
  gap: 20rpx;
  background: var(--bg-card, #fff);
  border-radius: 24rpx;
  padding: 48rpx 40rpx;
}

.config-title {
  font-size: 40rpx;
  font-weight: 600;
  color: var(--text-primary, #2c3338);
}

.config-sub {
  font-size: 26rpx;
  color: var(--text-secondary, #6b7280);
  margin-bottom: 16rpx;
}

.config-label {
  font-size: 28rpx;
  color: var(--text-primary, #2c3338);
  margin-top: 12rpx;
}

.opt-row {
  display: flex;
  gap: 16rpx;
  flex-wrap: wrap;
}

.opt {
  padding: 14rpx 32rpx;
  font-size: 27rpx;
  border-radius: 40rpx;
  background: var(--bg-page, #f3f4f6);
  color: var(--text-secondary, #6b7280);
}

.opt.active {
  background: #1e3a5f;
  color: #fff;
}

.start-btn {
  margin-top: 32rpx;
  height: 92rpx;
  line-height: 92rpx;
  font-size: 32rpx;
  color: #fff;
  background: #1e3a5f;
  border-radius: 16rpx;
}

/* 作答 */
.taking-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8rpx 8rpx 16rpx;
}

.progress-text {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--text-primary, #2c3338);
}

.timer {
  font-size: 28rpx;
  color: var(--text-secondary, #6b7280);
}

.timer.urgent {
  color: #e24b4a;
  font-weight: 600;
}

.progress-track {
  height: 8rpx;
  background: var(--bg-secondary, #e5e7eb);
  border-radius: 4rpx;
  margin-bottom: 24rpx;
}

.progress-fill {
  height: 100%;
  background: #1e3a5f;
  border-radius: 4rpx;
  transition: width 0.2s;
}

.q-card {
  background: var(--bg-card, #fff);
  border-radius: 24rpx;
  padding: 32rpx;
  font-size: 30rpx;
  color: var(--text-primary, #2c3338);
}

.q-loading {
  text-align: center;
  padding: 80rpx 0;
  color: var(--text-secondary, #9ca3af);
}

.options {
  margin-top: 28rpx;
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.option {
  display: flex;
  gap: 16rpx;
  padding: 24rpx;
  border: 2rpx solid var(--border-color, #e0e0e0);
  border-radius: 16rpx;
}

.option.selected {
  border-color: #1e3a5f;
  background: var(--bg-primary-light, #e8f0fe);
}

.opt-label {
  font-weight: 600;
  color: #1e3a5f;
}

.fill-area {
  margin-top: 28rpx;
}

.fill-input {
  height: 88rpx;
  padding: 0 24rpx;
  background: var(--bg-page, #f3f4f6);
  border-radius: 12rpx;
  font-size: 28rpx;
  color: var(--text-primary, #2c3338);
}

.taking-footer {
  display: flex;
  gap: 20rpx;
  margin-top: 32rpx;
}

.nav-btn {
  flex: 1;
  height: 88rpx;
  line-height: 88rpx;
  font-size: 30rpx;
  border-radius: 16rpx;
  background: #1e3a5f;
  color: #fff;
}

.nav-btn.ghost {
  background: transparent;
  border: 2rpx solid #1e3a5f;
  color: #1e3a5f;
}

.nav-btn.submit {
  background: #2d8a4f;
}

/* 报告 */
.score-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12rpx;
  background: var(--bg-card, #fff);
  border-radius: 24rpx;
  padding: 56rpx;
  margin-bottom: 24rpx;
}

.score-big {
  font-size: 72rpx;
  font-weight: 700;
  color: #1e3a5f;
}

.score-label {
  font-size: 28rpx;
  color: var(--text-secondary, #6b7280);
}

.report-section-title {
  font-size: 28rpx;
  font-weight: 600;
  color: var(--text-primary, #2c3338);
  display: block;
  padding: 8rpx;
}

.detail-row {
  display: flex;
  gap: 16rpx;
  background: var(--bg-card, #fff);
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 12rpx;
}

.detail-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8rpx;
}

.detail-stem {
  font-size: 27rpx;
  color: var(--text-primary, #2c3338);
}

.detail-answer {
  font-size: 24rpx;
  color: #2d8a4f;
}
</style>
