/**
 * 题目相关 API
 * 列表 / 详情 / 搜索 / 作答
 *
 * ⚠️ 安全关键：getQuestionDetail 会剥离 options 的 is_correct 字段，
 * 返回 SafeQuestionDetail，防止作答前答案泄露
 */
import { request } from './request'
import type {
  QuestionListItem,
  QuestionDetail,
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

/**
 * 题目详情
 * ⚠️ 剥离 is_correct 字段，UI 层拿不到正确答案
 */
export async function getQuestionDetail(id: number): Promise<SafeQuestionDetail> {
  const raw = await request<QuestionDetail>({ url: `/questions/${id}` })
  // 安全关键：剥离 is_correct，防止作答前答案泄露
  return {
    ...raw,
    options: raw.options.map(o => ({
      id: o.id,
      label: o.label,
      content_markdown: o.content_markdown,
    })),
  }
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
