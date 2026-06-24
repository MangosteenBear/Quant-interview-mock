/**
 * 难度标签 P1-P5 色阶映射
 * 按 PRD：低饱和商务简约，浅色系区分难度
 */

export interface DifficultyStyle {
  bg: string
  color: string
  label: string
}

const DIFFICULTY_MAP: Record<number, DifficultyStyle> = {
  1: { bg: '#d4edda', color: '#155724', label: 'P1' },
  2: { bg: '#fff3cd', color: '#856404', label: 'P2' },
  3: { bg: '#ffe0b2', color: '#e65100', label: 'P3' },
  4: { bg: '#f8d7da', color: '#721c24', label: 'P4' },
  5: { bg: '#c0392b', color: '#ffffff', label: 'P5' },
}

export function getDifficultyStyle(level: number | null): DifficultyStyle | null {
  if (!level || level < 1 || level > 5) return null
  return DIFFICULTY_MAP[level]
}

/** 题型中文标签 */
export const QUESTION_TYPE_LABELS: Record<string, string> = {
  choice: '选择题',
  fill: '填空题',
  short: '简答题',
  proof: '证明题',
}
