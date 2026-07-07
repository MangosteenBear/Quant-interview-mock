/**
 * 后端 API Schema 对应的 TypeScript 类型定义
 * 严格对齐 /workspace/backend/app/schemas/
 */

// ---------- 基础类型 ----------

export type QuestionType = 'choice' | 'fill' | 'short' | 'proof'

export interface SourceBrief {
  id: number
  book_title: string
  author: string | null
}

export interface TagBrief {
  id: number
  name: string
  type: 'knowledge' | 'position' | 'topic'
}

export interface OptionOut {
  id: number
  label: string
  content_markdown: string
  // is_correct 已在服务端剥离，不再下发
}

export interface SolutionOut {
  id: number
  content_markdown: string
  version: number
}

// ---------- 题目类型 ----------

export interface QuestionListItem {
  id: number
  stem_markdown: string
  question_type: QuestionType
  difficulty: number | null
  status: string
  book_chapter: string | null
  source: SourceBrief | null
  tags: TagBrief[]
  parent_question_id: number | null
}

/** 后端返回的完整详情（is_correct 已服务端剥离，含前后题 ID） */
export interface QuestionDetail extends QuestionListItem {
  book_page: number | null
  options: OptionOut[]
  solutions: SolutionOut[]
  updated_at: string | null
  adj_prev_id: number | null
  adj_next_id: number | null
}

/** 前端安全类型（OptionOut 已无 is_correct，SafeOption = OptionOut） */
export type SafeOption = OptionOut

export interface SafeQuestionDetail extends QuestionListItem {
  book_page: number | null
  options: SafeOption[]
  solutions: SolutionOut[]
  updated_at: string | null
  parent_question_id: number | null
  adj_prev_id: number | null
  adj_next_id: number | null
}

// ---------- 通用响应 ----------

export interface PageResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// ---------- 请求/响应模型 ----------

export interface AttemptRequest {
  device_id: string
  answer: string
  duration_ms: number | null
}

export interface AttemptResponse {
  is_correct: boolean | null
  correct_answer: string | null
  explanation: string | null
}

export interface FavoriteRequest {
  device_id: string
  question_id: number
}

export interface FavoriteResponse {
  favorited: boolean
  question_id: number
}

// ---------- 筛选参数 ----------

export interface QuestionFilter {
  source_id?: number
  book_chapter?: string
  question_type?: QuestionType
  difficulty?: number
  tag_name?: string
  status?: string
  page?: number
  page_size?: number
}
