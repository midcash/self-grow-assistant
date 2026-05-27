import { get } from './request'
import type { Dashboard, HeatmapData, Trend, Summary } from '@/types'

export function getDashboard(date: string) {
  return get<Dashboard>(`/progress/dashboard?date=${date}`)
}

export function getQualityHistory(qualityId: number, days = 30) {
  return get<{ quality: Record<string, unknown>; history: Record<string, unknown>[] }>(`/progress/qualities/${qualityId}/history?days=${days}`)
}

export function getHeatmap(startDate: string, endDate: string) {
  return get<HeatmapData>(`/progress/heatmap?start_date=${startDate}&end_date=${endDate}`)
}

export function getTrend(qualityId: number, days = 30) {
  return get<Trend>(`/progress/trend?quality_id=${qualityId}&days=${days}`)
}

export function getSummary(type: 'weekly' | 'monthly', date?: string) {
  const dateParam = date ? `&date=${date}` : ''
  return get<Summary>(`/reports/summary?type=${type}${dateParam}`)
}
