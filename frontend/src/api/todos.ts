import { get, post, put, patch, del } from './request'
import type { TodoItem, ParsedTodo } from '@/types'

export function parseTodos(text: string, date: string) {
  return post<{ parsed: ParsedTodo[] }>('/todos/parse', { text, date })
}

export function batchCreate(date: string, todos: { content: string; category: string; duration_minutes: number }[]) {
  return post<{ items: TodoItem[] }>('/todos/batch', { date, todos })
}

export function getTodosByDate(date: string) {
  return get<{ items: TodoItem[] }>(`/todos?date=${date}`)
}

export function updateTodo(id: number, data: Record<string, unknown>) {
  return put<TodoItem>(`/todos/${id}`, data)
}

export function deleteTodo(id: number) {
  return del(`/todos/${id}`)
}

export function checkIn(id: number, actual_duration = 0) {
  return patch<{ todo: TodoItem; score_earned: number }>(`/todos/${id}/checkin`, { actual_duration })
}

export function skipTodo(id: number) {
  return patch<TodoItem>(`/todos/${id}/skip`)
}
