import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export type AttemptStatus = 'correct' | 'wrong'

export const useAttemptStore = defineStore('attempt', () => {
  const records = ref<Record<number, AttemptStatus>>({})

  function init() {
    try {
      const raw = uni.getStorageSync('attempt_records')
      if (raw) records.value = JSON.parse(raw)
    } catch {}
  }

  function record(questionId: number, isCorrect: boolean) {
    records.value[questionId] = isCorrect ? 'correct' : 'wrong'
    try {
      uni.setStorageSync('attempt_records', JSON.stringify(records.value))
    } catch {}
    updateStreak()
  }

  function getStatus(questionId: number): AttemptStatus | null {
    return records.value[questionId] ?? null
  }

  const attemptedCount = computed(() => Object.keys(records.value).length)
  const correctCount = computed(() => Object.values(records.value).filter(v => v === 'correct').length)

  // streak: consecutive days with at least one attempt
  const streak = ref(0)

  function updateStreak() {
    try {
      const today = new Date().toDateString()
      const lastDay = uni.getStorageSync('streak_last_day')
      const streakVal = parseInt(uni.getStorageSync('streak_count') || '0', 10)
      if (lastDay === today) return
      const yesterday = new Date(Date.now() - 86400000).toDateString()
      const newStreak = lastDay === yesterday ? streakVal + 1 : 1
      uni.setStorageSync('streak_last_day', today)
      uni.setStorageSync('streak_count', String(newStreak))
      streak.value = newStreak
    } catch {}
  }

  function loadStreak() {
    try {
      streak.value = parseInt(uni.getStorageSync('streak_count') || '0', 10)
    } catch {}
  }

  return { records, init, record, getStatus, attemptedCount, correctCount, streak, loadStreak }
})
