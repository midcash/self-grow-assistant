<script setup lang="ts">
/** ObserveFilterBar — 编排筛选栏 */
import type { ObserveFilter } from '@/composables/useObserve'

const props = defineProps<{ filter: ObserveFilter }>()
const emit = defineEmits<{ change: [partial: Partial<ObserveFilter>] }>()

const agentOptions = ['', 'orchestrator', 'searcher', 'profiler', 'executor', 'goal_decomposer', 'coach']
const statusOptions = [
  { value: '', label: '全部' },
  { value: 'true', label: 'OK' },
  { value: 'false', label: 'FAIL' },
]
</script>

<template>
  <div class="filter-bar">
    <select
      class="filter-select"
      :value="filter.agent_name || ''"
      @change="emit('change', { agent_name: ($event.target as HTMLSelectElement).value || undefined })"
    >
      <option v-for="a in agentOptions" :key="a" :value="a">
        {{ a || '全部 Agent' }}
      </option>
    </select>
    <div class="status-btns">
      <button
        v-for="s in statusOptions" :key="s.value"
        class="status-btn"
        :class="{ active: (filter.success || '') === s.value }"
        @click="emit('change', { success: s.value || undefined })"
      >{{ s.label }}</button>
    </div>
  </div>
</template>

<style scoped>
.filter-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--color-border, #e0e0e0);
}
.filter-select {
  flex: 1;
  font-size: 11px;
  padding: 3px 6px;
  border: 1px solid var(--color-border, #e0e0e0);
  border-radius: 4px;
  background: var(--color-bg, #fff);
  color: var(--color-text, #333);
  min-width: 0;
}
.status-btns { display: flex; gap: 2px; }
.status-btn {
  font-size: 10px;
  padding: 2px 8px;
  border: 1px solid var(--color-border, #e0e0e0);
  border-radius: 4px;
  background: var(--color-bg, #fff);
  color: var(--color-text-muted, #999);
  cursor: pointer;
  white-space: nowrap;
}
.status-btn.active {
  background: var(--color-primary, #1976d2);
  color: #fff;
  border-color: var(--color-primary, #1976d2);
}
</style>
