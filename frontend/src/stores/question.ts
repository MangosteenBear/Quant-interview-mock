/**
 * 题目 Store
 * 列表 / 筛选 / 详情 / 作答状态
 */
import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import { listQuestions, getQuestionDetail, submitAttempt } from '@/api/question'
import type { QuestionListItem, SafeQuestionDetail, QuestionFilter, AttemptResponse } from '@/types/api'

export const useQuestionStore = defineStore('question', () => {
  // ---------- State ----------
  const list = ref<QuestionListItem[]>([])
  const total = ref(0)
  const currentPage = ref(1)
  const totalPages = ref(0)
  const loading = ref(false)
  const hasMore = ref(true)

  const filters = reactive<QuestionFilter>({
    source_id: undefined,
    book_chapter: undefined,
    question_type: undefined,
    difficulty: undefined,
    tag_name: undefined,
  })

  const detail = ref<SafeQuestionDetail | null>(null)
  const detailLoading = ref(false)
  const attemptResult = ref<AttemptResponse | null>(null)
  const submitted = ref(false)
  const currentIndex = ref(-1)

  // ---------- Actions ----------
  async function fetchList(reset = false) {
    if (loading.value) return
    if (reset) {
      currentPage.value = 1
      list.value = []
      hasMore.value = true
    }
    if (!hasMore.value) return

    loading.value = true
    try {
      const res = await listQuestions({
        ...filters,
        page: currentPage.value,
        page_size: 20,
      })
      if (currentPage.value === 1) {
        list.value = res.items
      } else {
        list.value.push(...res.items)
      }
      total.value = res.total
      totalPages.value = res.total_pages
      hasMore.value = currentPage.value < res.total_pages
    } finally {
      loading.value = false
    }
  }

  async function loadMore() {
    if (!hasMore.value || loading.value) return
    currentPage.value++
    await fetchList()
  }

  async function fetchDetail(id: number) {
    detailLoading.value = true
    submitted.value = false
    attemptResult.value = null
    try {
      detail.value = await getQuestionDetail(id)
    } finally {
      detailLoading.value = false
    }
  }

  async function submitAnswer(answer: string, durationMs: number, deviceId: string) {
    if (!detail.value) return
    const res = await submitAttempt(detail.value.id, {
      device_id: deviceId,
      answer,
      duration_ms: durationMs,
    })
    attemptResult.value = res
    submitted.value = true
    return res
  }

  function resetFilters() {
    filters.source_id = undefined
    filters.book_chapter = undefined
    filters.question_type = undefined
    filters.difficulty = undefined
    filters.tag_name = undefined
  }

  function setCurrentIndex(index: number) {
    currentIndex.value = index
  }

  function peekAnswer() {
    if (!detail.value) return
    const sol = detail.value.solutions?.find((s: any) => s.version === 2) ?? detail.value.solutions?.[0]
    attemptResult.value = {
      is_correct: null,
      correct_answer: null,
      explanation: sol?.content_markdown ?? null,
    }
    submitted.value = true
  }

  function setSearchResults(items: QuestionListItem[], totalCount: number) {
    list.value = items
    total.value = totalCount
    hasMore.value = false
    currentPage.value = 1
    totalPages.value = 1
  }

  function clearDetail() {
    detail.value = null
    attemptResult.value = null
    submitted.value = false
  }

  return {
    list,
    total,
    currentPage,
    totalPages,
    loading,
    hasMore,
    filters,
    detail,
    detailLoading,
    attemptResult,
    submitted,
    fetchList,
    loadMore,
    fetchDetail,
    submitAnswer,
    resetFilters,
    clearDetail,
    currentIndex,
    setCurrentIndex,
    setSearchResults,
    peekAnswer,
  }
})
