<script setup lang="ts">
/** OrchestrationItem — 单条编排记录 */
import { computed } from 'vue'
import type { OrchestrationSummary } from '@/api/agent'

const props = defineProps<{
  item: OrchestrationSummary
  selected: boolean
}>()

defineEmits<{ click: [] }>()

const timeLabel = computed(() => {
  if (!props.item.created_at) return ''
  try {
    const d = new Date(props.item.created_at)
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } catch { return '' }
})

const msLabel = computed(() => {
  const ms = props.item.total_latency_ms
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
})

const workerPills = computed(() =>
  (props.item.workers_used || []).slice(0, 4)
)
</script>

<template>
  <div class="orch-item" :class="{ selected, failed: !item.success }" @click="$emit('click')">
    <div class="item-left">
      <span class="item-time">{{ timeLabel }}</span>
    </div>
    <div class="item-body">
      <div class="item-intent">{{ item.intent || 'general' }}</div>
      <div class="item-workers">
        <span v-for="w in workerPills" :key="w" class="worker-pill" :class="'w-' + w">{{ w }}</span>
      </div>
    </div>
    <div class="item-right">
      <span class="item-ms">{{ msLabel }}</span>
      <span class="item-status" :class="{ ok: item.success, fail: !item.success }">
        {{ item.success ? '✓' : '✗' }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.orch-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  border-bottom: 1px solid var(--color-border, #e0e0e0);
  transition: background 0.15s;
}
.orch-item:hover { background: var(--color-bg-hover, rgba(0,0,0,0.03)); }
.orch-item.selected { background: var(--color-primary-light, #e3f2fd); }
.orch-item.failed { border-left: 2px solid #c62828; }
.item-left { flex-shrink: 0; padding-top: 1px; }
.item-time { font-size: 11px; color: var(--color-text-muted, #999); white-space: nowrap; }
.item-body { flex: 1; min-width: 0; }
.item-intent { font-size: 12px; color: var(--color-text, #333); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.item-workers { display: flex; gap: 3px; margin-top: 3px; flex-wrap: wrap; }
.worker-pill {
  font-size: 9px;
  padding: 1px 5px;
  border-radius: 3px;
  background: #e8eaf6;
  color: #3949ab;
  white-space: nowrap;
}
.w-synthesis { background: #e8f5e9; color: #2e7d32; }
.w-persist { background: #f3e5f5; color: #7b1fa2; }
.item-right {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}
.item-ms { font-size: 10px; color: var(--color-accent, #1976d2); white-space: nowrap; }
.item-status { font-size: 12px; font-weight: 700; }
.item-status.ok { color: #2e7d32; }
.item-status.fail { color: #c62828; }
</style>
