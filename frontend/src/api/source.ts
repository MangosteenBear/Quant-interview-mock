/**
 * 来源书目 API
 */
import { request } from './request'
import type { SourceBrief } from '@/types/api'

export function listSources() {
  return request<SourceBrief[]>({ url: '/sources' })
}
