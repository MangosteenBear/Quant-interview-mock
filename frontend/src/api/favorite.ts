/**
 * 收藏 API
 * toggle 切换 + 列表查询
 */
import { request } from './request'
import type { FavoriteRequest, FavoriteResponse, QuestionListItem, PageResponse } from '@/types/api'

/** 切换收藏（已收藏则取消，未收藏则添加） */
export function toggleFavorite(body: FavoriteRequest) {
  return request<FavoriteResponse>({
    url: '/favorites',
    method: 'POST',
    data: body,
  })
}

/** 收藏列表 */
export function listFavorites(params: { device_id: string; page?: number; page_size?: number }) {
  return request<PageResponse<QuestionListItem>>({
    url: '/favorites',
    params,
  })
}
