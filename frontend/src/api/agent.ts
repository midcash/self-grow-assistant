import { post, get, put } from './request'

export interface AgentStatus {
  initialized: boolean
  harness?: string
  plugins?: Record<string, { name: string; version: string; loaded: boolean; healthy: boolean }>
  token_zone?: string
  config?: {
    llm_provider: string
    tts_provider: string
    cron: string
    live2d_enabled: boolean
    mcp_active: boolean
  }
}

export interface ChatResponse {
  reply: string
  emotion_tag: string
}

export interface PriorityTask {
  id: number
  content: string
  category: string
  priority_score: number
  urgency: number
  importance: number
  reasoning: string
  suggested_action: string
  needs_alert: boolean
  evaluated_at?: string
}

export interface EvaluateResult {
  evaluated: boolean
  tasks: PriorityTask[]
  alerts: { task_id: number; content: string; score: number; suggested_action: string; is_deadline_near: boolean }[]
  message?: string
}

export interface ScheduleStatus {
  running: boolean
  cron: string
  next_run: string | null
}

// Agent status
export function getAgentStatus(): Promise<AgentStatus> {
  return get('/agent/status')
}

// Chat
export function agentChat(message: string, history: { role: string; content: string }[] = []): Promise<ChatResponse> {
  return post('/agent/chat', { message, history })
}

// Multi-Agent orchestration
export interface OrchestrateResult {
  reply: string
  workers_used: string[]
  results: { role: string; success: boolean; summary: string }[]
  plan: { intent: string; subtasks: any[] }
}

export function orchestrate(message: string, history: { role: string; content: string }[] = []): Promise<OrchestrateResult> {
  return post('/agent/orchestrate', { message, history })
}

// Trigger priority evaluation
export function triggerEvaluation(): Promise<EvaluateResult> {
  return post('/agent/evaluate')
}

// Get priority tasks
export function getPriorityTasks(): Promise<{ tasks: PriorityTask[] }> {
  return get('/agent/tasks/priority')
}

// TTS
export function textToSpeech(text: string, voice?: string, speed?: number): Promise<Blob> {
  return fetch('/api/v1/agent/tts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, voice, speed }),
  }).then(r => r.blob())
}

// Schedule control
export function getScheduleStatus(): Promise<ScheduleStatus> {
  return get('/agent/schedule/status')
}

export function toggleSchedule(): Promise<{ running: boolean; message: string }> {
  return post('/agent/schedule/toggle')
}

export function updateCron(cron: string): Promise<{ success: boolean; cron: string }> {
  return put('/agent/schedule/cron', { cron })
}

// Activity log
export interface ActivityEntry {
  file: string; time: string; elapsed: string
  workers: { name: string; objective: string; elapsed: string; result: string }[]
  message: string
}

export function getActivity(limit?: number): Promise<ActivityEntry[]> {
  return get(`/agent/activity?limit=${limit || 10}`)
}

// MCP tools + knowledge status
export interface McpTool {
  name: string; description: string
}

export interface KnowledgeStatus {
  connected: boolean; server?: string
  tools?: McpTool[]; collections?: string; message?: string
}

export function getKnowledge(): Promise<KnowledgeStatus> {
  return get('/agent/knowledge')
}
