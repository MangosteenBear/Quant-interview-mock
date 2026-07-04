/**
 * 标签 API
 */
import { request } from './request'
import type { TagBrief } from '@/types/api'

export function listTags(type?: 'knowledge' | 'position' | 'topic') {
  return request<TagBrief[]>({ url: '/tags', params: { type } })
}

export interface TagWithCount { id: number; name: string; count: number }

export function listTopicStats(): Promise<TagWithCount[]> {
  return request<TagWithCount[]>({ url: '/tags/topic-stats' })
}
