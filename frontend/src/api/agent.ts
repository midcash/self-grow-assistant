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
  monitoring?: {
    safety?: { safety_score: number; flags: any[]; jailbreak_attempt: boolean; pii_detected: boolean; harmful_content: boolean } | null
    quality?: { quality_score: number; dimensions: Record<string, number>; reasoning: string } | null
    tokens_estimated: number
    cost_estimated: number
  }
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

// === Agent 可观测性 (Trace + Metrics) ===

export interface OrchestrationSummary {
  orchestration_id: string
  intent: string
  workers_used: string[]
  total_latency_ms: number
  success: boolean
  created_at: string
  reply_preview: string
}

export interface AgentTraceSpan {
  id: string
  orchestration_id: string
  span_type: string
  agent_name: string
  parent_span_id: string | null
  objective: string
  input_summary: string
  output_summary: string
  latency_ms: number
  success: boolean
  error_message: string
  metadata_json: string
  created_at: string
}

export interface AgentMetricsItem {
  date: string
  agent_name: string
  total_calls: number
  success_count: number
  error_count: number
  avg_latency_ms: number
  p50_latency_ms: number
  p95_latency_ms: number
  total_token_estimate: number
}

export function getTraces(params: {
  limit?: number
  agent_name?: string
  date?: string
  success?: string
} = {}): Promise<OrchestrationSummary[]> {
  const q = new URLSearchParams()
  if (params.limit) q.set('limit', String(params.limit))
  if (params.agent_name) q.set('agent_name', params.agent_name)
  if (params.date) q.set('date', params.date)
  if (params.success) q.set('success', params.success)
  const qs = q.toString()
  return get(`/agent/traces${qs ? '?' + qs : ''}`)
}

export function getTraceDetail(orchestrationId: string): Promise<AgentTraceSpan[]> {
  return get(`/agent/traces/${orchestrationId}`)
}

export function getMetrics(params: {
  days?: number
  agent_name?: string
} = {}): Promise<AgentMetricsItem[]> {
  const q = new URLSearchParams()
  if (params.days) q.set('days', String(params.days))
  if (params.agent_name) q.set('agent_name', params.agent_name)
  const qs = q.toString()
  return get(`/agent/metrics${qs ? '?' + qs : ''}`)
}

// === Agent Evaluation API ===

export interface EvalRunRequest {
  name?: string
  components?: string[]
  workers?: string[]
  tags?: string[]
  gates?: string[]
}

export interface EvalRunSummary {
  id: number
  eval_name: string
  passed: boolean
  score: number
  duration_ms: number
  created_at: string
}

export interface EvalRunDetail {
  run: {
    id: number
    eval_name: string
    passed: boolean
    score: number
    metrics: Record<string, number>
    summary: Record<string, { total: number; passed: number; failed: number; avg_score: number }>
    failure_reason: string
    duration_ms: number
    created_at: string
  }
  results: EvalResultItem[]
}

export interface EvalResultItem {
  id: number
  example_id: string
  worker: string
  eval_type: string
  score: number
  passed: boolean
  dimension_scores: Record<string, number>
  reasoning: string
}

export interface EvalDatasetInfo {
  name: string
  description: string
  example_count: number
  workers: string[]
}

export interface EvalSummary {
  last_run: EvalRunSummary | null
  recent: { date: string; score: number; passed: boolean }[]
}

export function runEvaluation(params: EvalRunRequest = {}): Promise<EvalReportData> {
  return post('/agent/evaluation/run', params)
}

export interface EvalReportData {
  run_id: string
  config: any
  summary: Record<string, { total: number; passed: number; failed: number; avg_score: number; min_score: number; max_score: number }>
  dimension_scores: Record<string, number>
  passed: boolean
  total_duration_ms: number
  results: any[]
}

export function getEvaluationRuns(params: {
  limit?: number
  passed?: string
  name?: string
} = {}): Promise<EvalRunSummary[]> {
  const q = new URLSearchParams()
  if (params.limit) q.set('limit', String(params.limit))
  if (params.passed) q.set('passed', params.passed)
  if (params.name) q.set('name', params.name)
  const qs = q.toString()
  return get(`/agent/evaluation/runs${qs ? '?' + qs : ''}`)
}

export function getEvaluationRunDetail(runId: number): Promise<EvalRunDetail> {
  return get(`/agent/evaluation/runs/${runId}`)
}

export function getEvaluationDatasets(worker?: string): Promise<EvalDatasetInfo[]> {
  const q = worker ? `?worker=${encodeURIComponent(worker)}` : ''
  return get(`/agent/evaluation/datasets${q}`)
}

export function getEvaluationSummary(): Promise<EvalSummary> {
  return get('/agent/evaluation/summary')
}
