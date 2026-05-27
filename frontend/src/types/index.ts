// ── Quality ──
export interface Quality {
  id: number
  name: string
  description: string
  icon: string
  target_level: number
  created_at: string
  is_active: boolean
}

export interface QualityLevel {
  level: number
  name: string
  description: string
  threshold_score: number
}

export interface QualityDetail extends Quality {
  current_level: number
  total_score: number
  levels: QualityLevel[]
  progress: ProgressRecord[]
}

export interface MappingItem {
  category: string
  score_per_duration: number
  score_per_completion: number
}

export interface Mapping extends MappingItem {
  id: number
  quality_id: number
}

// ── Todo ──
export interface TodoItem {
  id: number
  date: string
  content: string
  category: string
  duration_minutes: number
  actual_duration: number
  status: 'pending' | 'done' | 'skipped'
  completed_at: string | null
  created_at: string
}

export interface ParsedTodo {
  content: string
  category: string
  duration_minutes: number
}

// ── Progress ──
export interface ProgressRecord {
  date: string
  score: number
  total_score: number
}

export interface DashboardQuality {
  id: number
  name: string
  icon: string
  current_score: number
  current_level: number
  level_name: string
  next_level_name: string
  next_level_score: number
  progress_pct: number
}

export interface Dashboard {
  date: string
  completion_rate: number
  total_duration: number
  total_score_today: number
  streak_days: number
  qualities: DashboardQuality[]
  todos: TodoItem[]
  background_url?: string
}

export interface HeatmapData {
  categories: string[]
  data: Record<string, number>[]
}

export interface TrendPoint {
  date: string
  cumulative_score: number
}

export interface Trend {
  quality_name: string
  points: TrendPoint[]
  level_thresholds: number[]
}

// ── Report ──
export interface Summary {
  period: string
  total_duration: number
  total_score: number
  streak_days: number
  top_quality: { name: string; score_gained: number }
  insight: string
}

// ── RoleModel ──
export interface SuggestedActivity {
  content: string
  category: string
  duration_minutes: number
  frequency: string
  reason: string
}

export interface RoleModelQuality {
  id: number
  role_model_id: number
  quality_name: string
  description: string
  suggested_activities: SuggestedActivity[]
}

export interface RoleModel {
  id: number
  name: string
  field: string
  avatar: string
  image_url: string
  description: string
  qualities: RoleModelQuality[]
}

export interface AdoptResult {
  quality_id: number
  quality_name: string
  role_model_name: string
  message: string
}

// ── API ──
export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}
