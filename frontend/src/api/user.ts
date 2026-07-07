/**
 * 用户数据 API：进度统计 / 错题本 / 资料更新 / 随机题
 * 统计与错题本支持匿名（device_id）与登录（自动带 token）两种身份
 */
import { request } from './request'
import type { UserOut } from './auth'
import type { QuestionListItem } from '@/types/api'

export interface StatsResponse {
  total_attempts: number
  attempted_questions: number
  correct_rate: number | null
  today_count: number
  streak_days: number
  by_type: Record<string, number>
}

export interface WrongQuestionItem {
  question: QuestionListItem
  last_wrong_at: string
  wrong_count: number
}

export function getStats(deviceId?: string) {
  return request<StatsResponse>({
    url: '/users/me/stats',
    params: { device_id: deviceId },
  })
}

export function getWrongQuestions(deviceId?: string, limit = 50) {
  return request<{ items: WrongQuestionItem[]; total: number }>({
    url: '/users/me/wrong-questions',
    params: { device_id: deviceId, limit },
  })
}

export function updateMe(data: { nickname?: string; avatar_url?: string }) {
  return request<UserOut>({ url: '/users/me', method: 'PATCH', data })
}

export function getRandomQuestion(params?: {
  question_type?: string
  difficulty?: number
  tag_name?: string
  source_id?: number
  exclude_id?: number
}) {
  return request<{ id: number }>({ url: '/questions/random', params })
}
