import { request } from './request'

export interface TypeStat { total: number; correct: number }
export interface StatsResult {
  by_type: Record<string, TypeStat>
  by_diff: Record<string, TypeStat>
}

export function getStats(deviceId: string): Promise<StatsResult> {
  return request<StatsResult>(`/api/stats?device_id=${encodeURIComponent(deviceId)}`)
}
