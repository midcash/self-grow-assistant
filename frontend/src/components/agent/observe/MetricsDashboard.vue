<script setup lang="ts">
/** MetricsDashboard — Agent 指标面板

 *  纯 CSS 实现: 成功率柱状图 + 延迟对比 + 汇总数字
 */
import { computed } from 'vue'
import type { AgentMetricsItem } from '@/api/agent'

const props = defineProps<{
  metrics: AgentMetricsItem[]
  days?: number
}>()

// 按 agent 聚合
const agentAgg = computed(() => {
  const map = new Map<string, { calls: number; ok: number; err: number; msAvg: number; msP50: number; msP95: number }>()
  for (const m of props.metrics) {
    const cur = map.get(m.agent_name) || { calls: 0, ok: 0, err: 0, msAvg: 0, msP50: 0, msP95: 0 }
    cur.calls += m.total_calls
    cur.ok += m.success_count
    cur.err += m.error_count
    cur.msAvg = Math.max(cur.msAvg, m.avg_latency_ms)
    cur.msP50 = Math.max(cur.msP50, m.p50_latency_ms)
    cur.msP95 = Math.max(cur.msP95, m.p95_latency_ms)
    map.set(m.agent_name, cur)
  }
  return Array.from(map.entries())
    .map(([name, d]) => ({
      name,
      successRate: d.calls > 0 ? Math.round((d.ok / d.calls) * 100) : 0,
      totalCalls: d.calls,
      p50: d.msP50,
      p95: d.msP95,
    }))
    .sort((a, b) => b.totalCalls - a.totalCalls)
})

const totalCalls = computed(() => agentAgg.value.reduce((s, a) => s + a.totalCalls, 0))
const overallRate = computed(() => {
  const ok = agentAgg.value.reduce((s, a) => s + Math.round(a.successRate * a.totalCalls / 100), 0)
  return totalCalls.value > 0 ? Math.round((ok / totalCalls.value) * 100) : 0
})

const maxCalls = computed(() => Math.max(1, ...agentAgg.value.map(a => a.totalCalls)))

function pct(v: number, max: number): string { return Math.round((v / max) * 100) + '%' }
function formatMs(ms: number): string { return ms < 1000 ? `${ms}ms` : `${(ms/1000).toFixed(1)}s` }
</script>

<template>
  <div class="metrics-dash">
    <!-- 空态 -->
    <div v-if="metrics.length === 0" class="md-empty">
      <p>暂无指标数据，编排后将自动生成</p>
    </div>

    <template v-else>
      <!-- 汇总行 -->
      <div class="md-summary">
        <div class="sum-item"><span class="sum-val">{{ totalCalls }}</span><span class="sum-label">总调用</span></div>
        <div class="sum-item"><span class="sum-val" :class="overallRate >= 90 ? 'green' : overallRate >= 75 ? 'amber' : 'red'">{{ overallRate }}%</span><span class="sum-label">成功率</span></div>
      </div>

      <!-- 成功率柱状图 -->
      <div class="md-section">
        <h4>成功率</h4>
        <div v-for="a in agentAgg" :key="'r'+a.name" class="md-bar-row">
          <span class="bar-label">{{ a.name }}</span>
          <div class="bar-track">
            <div class="bar-fill"
              :style="{ width: a.successRate + '%', background: a.successRate >= 90 ? '#66bb6a' : a.successRate >= 75 ? '#ffa726' : '#ef5350' }"
            />
          </div>
          <span class="bar-val">{{ a.successRate }}%</span>
        </div>
      </div>

      <!-- 调用量柱状图 -->
      <div class="md-section">
        <h4>调用量 (次)</h4>
        <div v-for="a in agentAgg" :key="'c'+a.name" class="md-bar-row">
          <span class="bar-label">{{ a.name }}</span>
          <div class="bar-track">
            <div class="bar-fill calls-bar" :style="{ width: pct(a.totalCalls, maxCalls) }" />
          </div>
          <span class="bar-val">{{ a.totalCalls }}</span>
        </div>
      </div>

      <!-- 延迟 -->
      <div class="md-section">
        <h4>延迟 (P50 / P95)</h4>
        <div v-for="a in agentAgg" :key="'l'+a.name" class="md-latency-row">
          <span class="bar-label">{{ a.name }}</span>
          <span class="lat-val p50">P50: {{ formatMs(a.p50) }}</span>
          <span class="lat-val p95">P95: {{ formatMs(a.p95) }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.metrics-dash { flex: 1; overflow-y: auto; padding: 12px 16px; min-height: 0; }
.md-empty { display: flex; align-items: center; justify-content: center; height: 100%; color: var(--color-text-muted, #999); font-size: 13px; }
.md-summary { display: flex; gap: 16px; margin-bottom: 16px; }
.sum-item { display: flex; flex-direction: column; align-items: center; padding: 10px 16px; border-radius: 8px; background: var(--color-bg, #fafafa); border: 1px solid var(--color-border, #e0e0e0); flex: 1; }
.sum-val { font-size: 20px; font-weight: 700; color: var(--color-text, #333); }
.sum-val.green { color: #2e7d32; }
.sum-val.amber { color: #f57c00; }
.sum-val.red { color: #c62828; }
.sum-label { font-size: 10px; color: var(--color-text-muted, #999); margin-top: 2px; }
.md-section { margin-bottom: 16px; }
.md-section h4 { font-size: 11px; color: var(--color-text-muted, #999); margin: 0 0 8px; }
.md-bar-row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.bar-label { font-size: 10px; color: var(--color-text, #333); width: 80px; flex-shrink: 0; text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bar-track { flex: 1; height: 14px; background: #eee; border-radius: 3px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 3px; min-width: 2px; transition: width 0.3s; }
.calls-bar { background: #90CAF9; }
.bar-val { font-size: 10px; color: var(--color-text-muted, #999); width: 40px; flex-shrink: 0; }
.md-latency-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.lat-val { font-size: 10px; color: var(--color-text-muted, #999); }
.lat-val.p50 { color: #90CAF9; }
.lat-val.p95 { color: #42A5F5; }
</style>
