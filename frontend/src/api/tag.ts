/**
 * 标签 API
 */
import { request } from './request'
import type { TagBrief } from '@/types/api'

export function listTags(type?: 'knowledge' | 'position' | 'topic') {
  return request<TagBrief[]>({ url: '/tags', params: { type } })
}
