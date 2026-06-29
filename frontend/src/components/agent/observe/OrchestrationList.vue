<script setup lang="ts">
/** OrchestrationList — 编排历史列表 */
import type { OrchestrationSummary } from '@/api/agent'
import OrchestrationItem from './OrchestrationItem.vue'

defineProps<{
  items: OrchestrationSummary[]
  selectedId: string | null
  loading: boolean
}>()

const emit = defineEmits<{ select: [id: string] }>()
</script>

<template>
  <div class="orchestration-list">
    <!-- Loading -->
    <div v-if="loading && items.length === 0" class="loading-area">
      <div v-for="n in 5" :key="n" class="skeleton-item">
        <div class="sk-line w-16" />
        <div class="sk-line w-32" />
      </div>
    </div>

    <!-- Empty -->
    <div v-else-if="!loading && items.length === 0" class="empty-area">
      <span class="empty-mark">◷</span>
      <p>暂无编排记录</p>
      <p class="hint">发送复杂请求后将自动生成</p>
    </div>

    <!-- List -->
    <div v-else class="list-body">
      <OrchestrationItem
        v-for="item in items"
        :key="item.orchestration_id"
        :item="item"
        :selected="item.orchestration_id === selectedId"
        @click="emit('select', item.orchestration_id)"
      />
    </div>
    <div v-if="loading && items.length > 0" class="loading-inline">加载中...</div>
  </div>
</template>

<style scoped>
.orchestration-list {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}
.loading-area { padding: 16px 12px; }
.skeleton-item {
  display: flex;
  gap: 8px;
  padding: 8px 0;
}
.sk-line {
  height: 10px;
  border-radius: 3px;
  background: var(--color-border, #e0e0e0);
  animation: pulse 1.2s ease-in-out infinite;
}
.w-16 { width: 40px; }
.w-32 { width: 80px; flex: 1; }
@keyframes pulse { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }
.empty-area {
  padding: 32px 16px;
  text-align: center;
  color: var(--color-text-muted, #999);
}
.empty-mark { font-size: 28px; opacity: 0.4; }
.empty-area p { font-size: 12px; margin: 4px 0; }
.empty-area .hint { font-size: 10px; opacity: 0.6; }
.list-body { }
.loading-inline {
  text-align: center;
  font-size: 10px;
  color: var(--color-text-muted, #999);
  padding: 8px;
}
</style>
