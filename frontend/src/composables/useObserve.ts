/** useObserve — Agent 数据流观测状态管理

  遵循 useAgent.ts 的 singleton 模式，管理观测页面的所有查询状态。
  纯查询型，不包含写入操作。
*/
import { ref, computed } from 'vue'
import {
  getTraces, getTraceDetail, getMetrics,
  type OrchestrationSummary, type AgentTraceSpan, type AgentMetricsItem,
} from '@/api/agent'

export interface ObserveFilter {
  agent_name?: string
  date?: string
  success?: string
  limit: number
}

// ----- Singleton State -----
const orchestrations = ref<OrchestrationSummary[]>([])
const currentTraceSpans = ref<AgentTraceSpan[]>([])
const metrics = ref<AgentMetricsItem[]>([])
const filter = ref<ObserveFilter>({ limit: 20 })
const selectedOrchestrationId = ref<string | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
let refreshTimer: ReturnType<typeof setInterval> | null = null

export function useObserve() {
  // ----- Computed -----
  const selectedOrchestration = computed(() =>
    orchestrations.value.find(o => o.orchestration_id === selectedOrchestrationId.value) ?? null
  )

  // ----- Methods -----
  async function fetchList() {
    loading.value = true
    error.value = null
    try {
      orchestrations.value = await getTraces({
        limit: filter.value.limit,
        agent_name: filter.value.agent_name,
        date: filter.value.date,
        success: filter.value.success,
      })
    } catch (e) {
      error.value = e instanceof Error ? e.message : '获取编排列表失败'
      orchestrations.value = []
    }
    loading.value = false
  }

  async function selectOrchestration(id: string) {
    selectedOrchestrationId.value = id
    loading.value = true
    error.value = null
    try {
      currentTraceSpans.value = await getTraceDetail(id)
    } catch (e) {
      error.value = e instanceof Error ? e.message : '获取 Trace 详情失败'
      currentTraceSpans.value = []
    }
    loading.value = false
  }

  async function fetchMetrics(days = 7, agentName?: string) {
    try {
      metrics.value = await getMetrics({ days, agent_name: agentName })
    } catch {
      metrics.value = []
    }
  }

  function updateFilter(partial: Partial<ObserveFilter>) {
    filter.value = { ...filter.value, ...partial }
    fetchList()
  }

  function refresh() {
    fetchList()
    if (selectedOrchestrationId.value) {
      selectOrchestration(selectedOrchestrationId.value)
    }
    fetchMetrics()
  }

  function startAutoRefresh(intervalMs = 3000) {
    stopAutoRefresh()
    refreshTimer = setInterval(() => fetchList(), intervalMs)
  }

  function stopAutoRefresh() {
    if (refreshTimer) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }

  return {
    orchestrations,
    currentTraceSpans,
    metrics,
    filter,
    selectedOrchestrationId,
    selectedOrchestration,
    loading,
    error,
    fetchList,
    selectOrchestration,
    fetchMetrics,
    updateFilter,
    refresh,
    startAutoRefresh,
    stopAutoRefresh,
  }
}
