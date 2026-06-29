<script setup lang="ts">
/** TraceWaterfall — Trace 瀑布图（核心组件）
 *
 *  横向甘特图风格展示编排的 5 种 span:
 *  plan (灰) → worker_execute (蓝) → synthesis (绿) → persist (紫)
 */
import { computed, ref } from 'vue'
import type { AgentTraceSpan } from '@/api/agent'

const props = defineProps<{
  spans: AgentTraceSpan[]
  loading: boolean
}>()

const expanded = ref(true)

// 颜色映射
const colorMap: Record<string, string> = {
  plan: '#9E9E9E',
  worker_dispatch: '#90CAF9',
  worker_execute: '#42A5F5',
  synthesis: '#66BB6A',
  safety_check: '#EF5350',
  persist: '#AB47BC',
}

const labelMap: Record<string, string> = {
  plan: '计划', worker_dispatch: '分发', worker_execute: '执行',
  synthesis: '整合', safety_check: '安全', persist: '持久化',
}

// 按顺序排列的 span
const orderedSpans = computed(() => {
  const s = [...props.spans]
  // plan → worker_execute×N → synthesis → persist
  const order: Record<string, number> = { plan: 0, worker_dispatch: 1, worker_execute: 2, synthesis: 3, safety_check: 4, persist: 5 }
  s.sort((a, b) => (order[a.span_type] ?? 9) - (order[b.span_type] ?? 9) || a.latency_ms - b.latency_ms)
  return s
})

const maxLatency = computed(() => {
  let max = 0
  for (const s of props.spans) max = Math.max(max, s.latency_ms)
  return max || 1
})

const timelineTicks = computed(() => {
  const max = maxLatency.value
  const step = max < 500 ? 100 : max < 2000 ? 500 : 1000
  const ticks: { label: string; left: number }[] = []
  for (let t = 0; t <= max; t += step) {
    ticks.push({
      label: t < 1000 ? `${t}ms` : `${(t/1000).toFixed(1)}s`,
      left: (t / max) * 100,
    })
  }
  return ticks
})

const visibleSpans = computed(() => {
  if (expanded.value) return orderedSpans.value
  return orderedSpans.value.slice(0, 20)
})

const hasMore = computed(() => orderedSpans.value.length > 20)

function barWidth(span: AgentTraceSpan): number {
  return Math.max(4, (span.latency_ms / maxLatency.value) * 100)
}

function formatMs(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

const selectedSpan = ref<AgentTraceSpan | null>(null)
</script>

<template>
  <div class="waterfall">
    <!-- 加载态 -->
    <div v-if="loading" class="wf-loading">
      <div v-for="n in 5" :key="n" class="sk-bar" :style="{ width: (30 + n * 12) + '%' }" />
    </div>

    <!-- 空态 -->
    <div v-else-if="!spans.length" class="wf-empty">
      <span>暂无 Trace 数据</span>
    </div>

    <!-- 瀑布图 -->
    <div v-else class="wf-body">
      <!-- 时间轴标尺 -->
      <div class="wf-ruler">
        <div class="ruler-label">&nbsp;</div>
        <div class="ruler-track">
          <div
            v-for="tick in timelineTicks" :key="tick.label"
            class="ruler-tick"
            :style="{ left: tick.left + '%' }"
          >{{ tick.label }}</div>
        </div>
      </div>

      <!-- Span 行 -->
      <div v-for="span in visibleSpans" :key="span.id" class="wf-row">
        <div class="wf-label">
          <span class="wf-tag" :style="{ background: colorMap[span.span_type] || '#999' }">
            {{ labelMap[span.span_type] || span.span_type }}
          </span>
          <span class="wf-agent">{{ span.agent_name }}</span>
        </div>
        <div class="wf-track">
          <div
            class="wf-bar"
            :class="{ fail: !span.success }"
            :style="{
              width: barWidth(span) + '%',
              background: colorMap[span.span_type] || '#999',
            }"
            :title="`${span.span_type}/${span.agent_name}: ${formatMs(span.latency_ms)} — ${span.objective?.slice(0, 60)}`"
            @click="selectedSpan = span"
          >
            <span class="wf-bar-label">{{ formatMs(span.latency_ms) }}</span>
          </div>
        </div>
      </div>

      <!-- 展开更多 -->
      <div v-if="hasMore" class="wf-more">
        <button @click="expanded = !expanded">
          {{ expanded ? '折叠' : `展开剩余 ${orderedSpans.length - 20} 条` }}
        </button>
      </div>
    </div>

    <!-- Span Detail Drawer -->
    <div v-if="selectedSpan" class="wf-drawer-mask" @click.self="selectedSpan = null">
      <div class="wf-drawer">
        <div class="drawer-header">
          <span>{{ labelMap[selectedSpan.span_type] || selectedSpan.span_type }}</span>
          <button class="drawer-close" @click="selectedSpan = null">✕</button>
        </div>
        <div class="drawer-body">
          <table class="drawer-table">
            <tr><td class="k">Agent</td><td>{{ selectedSpan.agent_name }}</td></tr>
            <tr><td class="k">延迟</td><td>{{ formatMs(selectedSpan.latency_ms) }}</td></tr>
            <tr><td class="k">状态</td><td :class="{ ok: selectedSpan.success, fail: !selectedSpan.success }">{{ selectedSpan.success ? '✓ 成功' : '✗ 失败' }}</td></tr>
            <tr v-if="!selectedSpan.success && selectedSpan.error_message">
              <td class="k">错误</td><td class="err">{{ selectedSpan.error_message }}</td>
            </tr>
          </table>
          <div v-if="selectedSpan.objective" class="drawer-section">
            <h4>目标</h4>
            <p>{{ selectedSpan.objective }}</p>
          </div>
          <div v-if="selectedSpan.input_summary" class="drawer-section">
            <h4>输入 (TaskBrief)</h4>
            <pre>{{ selectedSpan.input_summary }}</pre>
          </div>
          <div v-if="selectedSpan.output_summary" class="drawer-section">
            <h4>输出 (WorkerResult)</h4>
            <pre>{{ selectedSpan.output_summary }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.waterfall { flex: 1; display: flex; flex-direction: column; min-height: 0; overflow: hidden; }
.wf-loading { padding: 24px 16px; display: flex; flex-direction: column; gap: 12px; }
.sk-bar {
  height: 12px;
  border-radius: 3px;
  background: var(--color-border, #e0e0e0);
  animation: pulse 1.2s ease-in-out infinite;
}
@keyframes pulse { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }
.wf-empty { flex: 1; display: flex; align-items: center; justify-content: center; color: var(--color-text-muted, #999); font-size: 13px; }
.wf-body { flex: 1; overflow-y: auto; padding: 8px 0; }
.wf-ruler { display: flex; padding: 0 12px; margin-bottom: 4px; }
.ruler-label { width: 100px; flex-shrink: 0; }
.ruler-track { flex: 1; position: relative; height: 16px; }
.ruler-tick { position: absolute; font-size: 9px; color: var(--color-text-muted, #999); transform: translateX(-50%); white-space: nowrap; }
.wf-row { display: flex; align-items: center; padding: 2px 12px; }
.wf-label { width: 100px; flex-shrink: 0; display: flex; align-items: center; gap: 4px; overflow: hidden; }
.wf-tag { font-size: 9px; color: #fff; padding: 1px 5px; border-radius: 3px; white-space: nowrap; }
.wf-agent { font-size: 10px; color: var(--color-text, #333); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.wf-track { flex: 1; height: 20px; position: relative; }
.wf-bar {
  height: 16px;
  border-radius: 3px;
  min-width: 4px;
  display: flex;
  align-items: center;
  padding: 0 4px;
  cursor: pointer;
  transition: opacity 0.15s;
  position: absolute;
  left: 0;
  top: 2px;
}
.wf-bar:hover { opacity: 0.8; }
.wf-bar.fail { opacity: 0.5; border: 1px solid #c62828; }
.wf-bar-label { font-size: 8px; color: #fff; white-space: nowrap; overflow: hidden; }
.wf-more { text-align: center; padding: 8px; }
.wf-more button { font-size: 10px; padding: 3px 10px; border: 1px solid var(--color-border, #e0e0e0); border-radius: 4px; background: var(--color-bg, #fff); color: var(--color-text-muted, #999); cursor: pointer; }

/* Drawer */
.wf-drawer-mask {
  position: fixed; inset: 0; background: rgba(0,0,0,0.3); z-index: 1000;
  display: flex; justify-content: flex-end;
}
.wf-drawer {
  width: 85%; max-width: 520px; height: 100%;
  background: var(--color-card, #fff);
  display: flex; flex-direction: column;
  box-shadow: -2px 0 16px rgba(0,0,0,0.15);
  animation: slideIn 0.2s ease;
}
@keyframes slideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
.drawer-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; border-bottom: 1px solid var(--color-border, #e0e0e0);
  font-size: 14px; font-weight: 600;
}
.drawer-close {
  font-size: 16px; border: none; background: none; cursor: pointer;
  color: var(--color-text-muted, #999); padding: 4px;
}
.drawer-body { flex: 1; overflow-y: auto; padding: 16px; }
.drawer-table { width: 100%; font-size: 12px; border-collapse: collapse; margin-bottom: 12px; }
.drawer-table td { padding: 4px 8px; border-bottom: 1px solid var(--color-border, #e0e0e0); }
.drawer-table .k { color: var(--color-text-muted, #999); width: 60px; }
.drawer-table .ok { color: #2e7d32; }
.drawer-table .fail { color: #c62828; }
.drawer-table .err { color: #c62828; font-size: 11px; }
.drawer-section { margin-top: 12px; }
.drawer-section h4 { font-size: 11px; color: var(--color-text-muted, #999); margin: 0 0 4px; }
.drawer-section p { font-size: 12px; margin: 0; white-space: pre-wrap; }
.drawer-section pre { font-size: 11px; background: #f5f5f5; padding: 8px; border-radius: 4px; overflow-x: auto; white-space: pre-wrap; word-break: break-all; max-height: 200px; overflow-y: auto; margin: 0; }
</style>
