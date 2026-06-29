<script setup lang="ts">
/** AgentTopology — Agent 拓扑图 (CSS Flex 纯布局)

 *  central orchestrator node → worker nodes with edge lines
 */
import { computed } from 'vue'
import type { AgentMetricsItem } from '@/api/agent'

const props = defineProps<{
  metrics: AgentMetricsItem[]
}>()

interface WorkerNode {
  name: string
  total_calls: number
  success_rate: number
  avg_latency_ms: number
  status: 'active' | 'idle'
}

const workers = computed<WorkerNode[]>(() => {
  const map = new Map<string, { calls: number; ok: number; ms: number }>()
  for (const m of props.metrics) {
    if (m.agent_name === 'orchestrator') continue
    const cur = map.get(m.agent_name) || { calls: 0, ok: 0, ms: 0 }
    cur.calls += m.total_calls
    cur.ok += m.success_count
    cur.ms += m.avg_latency_ms
    map.set(m.agent_name, cur)
  }
  return Array.from(map.entries()).map(([name, d]) => ({
    name,
    total_calls: d.calls,
    success_rate: d.calls > 0 ? Math.round((d.ok / d.calls) * 100) : 0,
    avg_latency_ms: d.calls > 0 ? Math.round(d.ms / d.calls) : 0,
    status: d.calls > 0 ? 'active' as const : 'idle' as const,
  }))
})

// Color palette
const nodeColors: Record<string, string> = {
  searcher: '#42A5F5', profiler: '#AB47BC', executor: '#66BB6A',
  goal_decomposer: '#FFA726', coach: '#EF5350',
  reflection: '#26C6DA', replanner: '#7E57C2',
}

const selectedWorker = ref<string | null>(null)

function selectWorker(name: string) {
  selectedWorker.value = selectedWorker.value === name ? null : name
}

const selectedStats = computed(() =>
  workers.value.find(w => w.name === selectedWorker.value)
)

function formatMs(ms: number): string {
  return ms < 1000 ? `${ms}ms` : `${(ms/1000).toFixed(1)}s`
}

import { ref } from 'vue'
</script>

<template>
  <div class="topology">
    <!-- 空态 -->
    <div v-if="workers.length === 0" class="topo-empty">
      <p>Worker 尚未注册或暂无统计数据</p>
    </div>

    <template v-else>
      <!-- 编排器中心节点 -->
      <div class="topo-orch">
        <div class="topo-node orch">
          <span class="node-name">Orchestrator</span>
        </div>
      </div>

      <!-- 连线层 (CSS borders simulate edges) -->
      <div class="topo-edges">
        <div class="edge-line" />
      </div>

      <!-- Worker 节点 -->
      <div class="topo-workers">
        <div
          v-for="w in workers" :key="w.name"
          class="topo-node worker"
          :class="{ active: w.status === 'active', idle: w.status === 'idle', selected: selectedWorker === w.name }"
          :style="{ borderColor: nodeColors[w.name] || '#999' }"
          @click="selectWorker(w.name)"
        >
          <span class="node-name">{{ w.name }}</span>
          <span class="node-calls">{{ w.total_calls }}次</span>
          <span class="node-rate" :style="{ color: w.success_rate >= 90 ? '#2e7d32' : w.success_rate >= 75 ? '#f57c00' : '#c62828' }">
            {{ w.success_rate }}%
          </span>
        </div>
      </div>

      <!-- 选中 Worker 详情 -->
      <div v-if="selectedStats" class="topo-detail">
        <h4>{{ selectedStats.name }} 统计</h4>
        <div class="detail-grid">
          <span>总调用: <b>{{ selectedStats.total_calls }}</b></span>
          <span>成功率: <b>{{ selectedStats.success_rate }}%</b></span>
          <span>均延迟: <b>{{ formatMs(selectedStats.avg_latency_ms) }}</b></span>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.topology {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px;
  overflow-y: auto;
  min-height: 0;
}
.topo-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted, #999);
  font-size: 13px;
}
.topo-orch { margin-bottom: 24px; }
.topo-workers {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: center;
}
.topo-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 16px;
  border-radius: 8px;
  border: 2px solid var(--color-border, #e0e0e0);
  background: var(--color-bg, #fff);
  cursor: pointer;
  transition: transform 0.15s, opacity 0.15s;
  min-width: 80px;
}
.topo-node:hover { transform: scale(1.05); }
.topo-node.orch { border-color: #9E9E9E; background: #f5f5f5; cursor: default; min-width: 120px; }
.topo-node.idle { opacity: 0.5; }
.topo-node.selected { transform: scale(1.08); box-shadow: 0 2px 12px rgba(0,0,0,0.15); }
.node-name { font-size: 11px; font-weight: 600; color: var(--color-text, #333); }
.node-calls { font-size: 9px; color: var(--color-text-muted, #999); margin-top: 2px; }
.node-rate { font-size: 10px; font-weight: 700; margin-top: 1px; }
.topo-detail {
  margin-top: 16px;
  padding: 12px 20px;
  border-radius: 8px;
  border: 1px solid var(--color-border, #e0e0e0);
  background: var(--color-bg, #fafafa);
  width: 100%;
  max-width: 320px;
}
.topo-detail h4 {
  font-size: 12px;
  margin: 0 0 8px;
  color: var(--color-text, #333);
}
.detail-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  font-size: 11px;
  color: var(--color-text-muted, #999);
}
.detail-grid b { color: var(--color-text, #333); }
</style>
