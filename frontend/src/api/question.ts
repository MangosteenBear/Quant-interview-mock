/**
 * 题目相关 API
 * 列表 / 详情 / 搜索 / 作答
 *
 * is_correct 已在服务端剥离，adj_prev_id/adj_next_id 随详情一起返回
 */
import { request } from './request'
import type {
  QuestionListItem,
  SafeQuestionDetail,
  PageResponse,
  QuestionFilter,
  AttemptRequest,
  AttemptResponse,
} from '@/types/api'

/** 题目列表（分页+筛选） */
export function listQuestions(params: QuestionFilter = {}) {
  return request<PageResponse<QuestionListItem>>({
    url: '/questions',
    params: { status: 'published', ...params },
  })
}

/** 题目详情（含 adj_prev_id / adj_next_id，is_correct 已服务端剥离） */
export function getQuestionDetail(id: number): Promise<SafeQuestionDetail> {
  return request<SafeQuestionDetail>({ url: `/questions/${id}` })
}

/** 关键词搜索 */
export function searchQuestions(params: { q: string; page?: number; page_size?: number }) {
  return request<PageResponse<QuestionListItem>>({
    url: '/questions/search/all',
    params,
  })
}

/** 提交作答 */
export function submitAttempt(id: number, body: AttemptRequest) {
  return request<AttemptResponse>({
    url: `/questions/${id}/attempt`,
    method: 'POST',
    data: body,
  })
}
