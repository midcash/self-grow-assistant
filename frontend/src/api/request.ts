import type { ApiResponse } from '@/types'

const BASE = '/api/v1'

function handleError(res: ApiResponse) {
  if (res.code !== 0) {
    throw new Error(res.message || 'Unknown error')
  }
}

export async function get<T>(path: string): Promise<T> {
  const r = await fetch(BASE + path)
  const json: ApiResponse<T> = await r.json()
  handleError(json)
  return json.data
}

export async function post<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(BASE + path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  const json: ApiResponse<T> = await r.json()
  handleError(json)
  return json.data
}

export async function put<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(BASE + path, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  const json: ApiResponse<T> = await r.json()
  handleError(json)
  return json.data
}

export async function patch<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(BASE + path, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  const json: ApiResponse<T> = await r.json()
  handleError(json)
  return json.data
}

export async function del(path: string): Promise<void> {
  const r = await fetch(BASE + path, { method: 'DELETE' })
  const json: ApiResponse = await r.json()
  handleError(json)
}

export async function upload<T>(path: string, formData: FormData): Promise<T> {
  const r = await fetch(BASE + path, {
    method: 'POST',
    body: formData,
  })
  const json: ApiResponse<T> = await r.json()
  handleError(json)
  return json.data
}
