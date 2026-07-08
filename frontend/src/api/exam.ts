/**
 * 模考 API
 */
import { request } from './request'

export interface ExamStartResponse {
  id: number
  question_ids: number[]
  time_limit_sec: number | null
}

export interface ExamDetail {
  question_id: number
  stem: string
  user_answer: string | null
  is_correct: boolean
  correct_answer: string | null
}

export interface ExamReport {
  id: number
  correct: number
  total: number
  accuracy: number
  duration_sec: number | null
  details: ExamDetail[]
}

export function startExam(data: {
  device_id: string
  count: number
  question_type: string
  time_limit_sec?: number
}) {
  return request<ExamStartResponse>({ url: '/exam/start', method: 'POST', data })
}

export function submitExam(
  examId: number,
  data: {
    device_id: string
    answers: { question_id: number; answer: string }[]
    duration_sec?: number
  },
) {
  return request<ExamReport>({ url: `/exam/${examId}/submit`, method: 'POST', data })
}
