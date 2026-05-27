import { get, post, put, del } from './request'
import type { Quality, QualityDetail, Mapping } from '@/types'

export function listQualities(isActive = true) {
  return get<Quality[]>(`/qualities?is_active=${isActive}`)
}

export function getQuality(id: number) {
  return get<QualityDetail>(`/qualities/${id}`)
}

export function createQuality(data: { name: string; description?: string; icon?: string; target_level?: number }) {
  return post<Quality>('/qualities', data)
}

export function updateQuality(id: number, data: Record<string, unknown>) {
  return put<Quality>(`/qualities/${id}`, data)
}

export function deleteQuality(id: number) {
  return del(`/qualities/${id}`)
}

export function updateMappings(id: number, mappings: { category: string; score_per_duration: number; score_per_completion: number }[]) {
  return put<Mapping[]>(`/qualities/${id}/mappings`, { mappings })
}
