<script setup lang="ts">
/** MetricsStickyBar — 底部固定指标汇总条 */
import { computed } from 'vue'
import type { AgentMetricsItem } from '@/api/agent'

const props = defineProps<{ metrics: AgentMetricsItem[] }>()

const summary = computed(() => {
  let calls = 0; let ok = 0
  for (const m of props.metrics) {
    calls += m.total_calls
    ok += m.success_count
  }
  return { calls, rate: calls > 0 ? Math.round((ok / calls) * 100) : 0 }
})
</script>

<template>
  <div class="sticky-bar" v-if="summary.calls > 0">
    <span>总编排: <b>{{ summary.calls }}</b></span>
    <span class="sep">|</span>
    <span>成功率: <b :class="summary.rate >= 90 ? 'green' : summary.rate >= 75 ? 'amber' : 'red'">{{ summary.rate }}%</b></span>
  </div>
</template>

<style scoped>
.sticky-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  font-size: 11px;
  color: var(--color-text-muted, #999);
  border-top: 1px solid var(--color-border, #e0e0e0);
  background: var(--color-bg, #fafafa);
}
.sep { color: var(--color-border, #e0e0e0); }
b.green { color: #2e7d32; }
b.amber { color: #f57c00; }
b.red { color: #c62828; }
</style>
