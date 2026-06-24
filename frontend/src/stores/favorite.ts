/**
 * 收藏 Store
 * 收藏列表 + 收藏 ID 集合缓存
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { toggleFavorite, listFavorites } from '@/api/favorite'
import type { QuestionListItem, PageResponse } from '@/types/api'

export const useFavoriteStore = defineStore('favorite', () => {
  // ---------- State ----------
  const list = ref<QuestionListItem[]>([])
  const total = ref(0)
  const loading = ref(false)
  /** 已收藏题目 ID 集合（用于详情页星标状态） */
  const favoritedIds = ref<Set<number>>(new Set())

  // ---------- Actions ----------
  async function fetchList(deviceId: string, reset = false) {
    if (loading.value) return
    if (reset) list.value = []
    loading.value = true
    try {
      const res: PageResponse<QuestionListItem> = await listFavorites({
        device_id: deviceId,
        page: 1,
        page_size: 100,
      })
      list.value = res.items
      total.value = res.total
      // 更新缓存
      favoritedIds.value = new Set(res.items.map(q => q.id))
    } finally {
      loading.value = false
    }
  }

  async function toggle(questionId: number, deviceId: string) {
    const res = await toggleFavorite({
      device_id: deviceId,
      question_id: questionId,
    })
    if (res.favorited) {
      favoritedIds.value.add(questionId)
    } else {
      favoritedIds.value.delete(questionId)
      // 从收藏列表移除
      list.value = list.value.filter(q => q.id !== questionId)
      total.value--
    }
    return res.favorited
  }

  function isFavorited(id: number): boolean {
    return favoritedIds.value.has(id)
  }

  return {
    list,
    total,
    loading,
    favoritedIds,
    fetchList,
    toggle,
    isFavorited,
  }
})
