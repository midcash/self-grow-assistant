/** useEvaluation — Agent评估状态管理

  遵循 useObserve.ts 的 singleton 模式。
  管理评估运行、详情、数据集、摘要的查询和触发。
*/
import { ref, computed } from 'vue'
import {
  runEvaluation, getEvaluationRuns, getEvaluationRunDetail,
  getEvaluationDatasets, getEvaluationSummary,
  type EvalRunSummary, type EvalRunDetail, type EvalDatasetInfo,
  type EvalSummary, type EvalReportData,
} from '@/api/agent'

// ----- Singleton State -----
const runs = ref<EvalRunSummary[]>([])
const selectedRunDetail = ref<EvalRunDetail | null>(null)
const lastReport = ref<EvalReportData | null>(null)
const datasets = ref<EvalDatasetInfo[]>([])
const summary = ref<EvalSummary | null>(null)
const loading = ref(false)
const running = ref(false)
const error = ref<string | null>(null)

export function useEvaluation() {
  const selectedRun = computed(() =>
    selectedRunDetail.value?.run ?? null
  )

  async function fetchRuns(params?: { limit?: number; passed?: string }) {
    loading.value = true
    error.value = null
    try {
      runs.value = await getEvaluationRuns(params || { limit: 20 })
    } catch (e) {
      error.value = e instanceof Error ? e.message : '获取评估列表失败'
      runs.value = []
    }
    loading.value = false
  }

  async function selectRun(runId: number) {
    loading.value = true
    error.value = null
    try {
      selectedRunDetail.value = await getEvaluationRunDetail(runId)
    } catch (e) {
      error.value = e instanceof Error ? e.message : '获取评估详情失败'
      selectedRunDetail.value = null
    }
    loading.value = false
  }

  async function fetchDatasets(worker?: string) {
    try {
      datasets.value = await getEvaluationDatasets(worker)
    } catch {
      datasets.value = []
    }
  }

  async function fetchSummary() {
    try {
      summary.value = await getEvaluationSummary()
    } catch {
      summary.value = null
    }
  }

  async function triggerRun(config: {
    name?: string
    components?: string[]
    workers?: string[]
    tags?: string[]
    gates?: string[]
  } = {}): Promise<boolean> {
    running.value = true
    error.value = null
    try {
      const result = await runEvaluation({
        name: config.name || 'manual',
        components: config.components || ['prompt', 'tool_call', 'reasoning', 'rag', 'trajectory'],
        workers: config.workers || [],
        tags: config.tags || [],
        gates: config.gates || ['smoke'],
      })
      lastReport.value = result
      await fetchRuns()
      return lastReport.value?.passed ?? false
    } catch (e) {
      error.value = e instanceof Error ? e.message : '评估运行失败'
      return false
    } finally {
      running.value = false
    }
  }

  function refresh() {
    fetchRuns()
    fetchSummary()
  }

  return {
    runs, selectedRunDetail, selectedRun, lastReport,
    datasets, summary,
    loading, running, error,
    fetchRuns, selectRun, fetchDatasets, fetchSummary, triggerRun, refresh,
  }
}
