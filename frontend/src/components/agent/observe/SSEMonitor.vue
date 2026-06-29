<script setup lang="ts">
/** SSEMonitor — 实时编排 SSE 事件监控

 *  展示当前编排的实时进度。
 *  SSE 连接由 useSSE composable 管理（待实现）。
 */
import { ref } from 'vue'

const connected = ref(false)
const events = ref<{ id: string; type: string; text: string; time: string; ok?: boolean }[]>([])

// Placeholder — SSE composable 将在 Phase 5 集成
function formatTime(): string {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
</script>

<template>
  <div class="sse-monitor">
    <div class="sse-header">
      <span class="sse-dot" :class="{ on: connected, off: !connected }" />
      <span class="sse-title">实时监控</span>
      <span class="sse-status">{{ connected ? '已连接' : '待连接' }}</span>
    </div>
    <div class="sse-body">
      <div v-if="events.length === 0" class="sse-empty">
        <span>等待编排事件...</span>
      </div>
      <div v-for="evt in events" :key="evt.id" class="sse-event" :class="evt.type">
        <span class="evt-time">{{ evt.time }}</span>
        <span class="evt-type">{{ evt.type }}</span>
        <span class="evt-text">{{ evt.text }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sse-monitor {
  border-top: 1px solid var(--color-border, #e0e0e0);
  max-height: 140px;
  display: flex;
  flex-direction: column;
  background: var(--color-bg, #fafafa);
}
.sse-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-bottom: 1px solid var(--color-border, #e0e0e0);
}
.sse-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.sse-dot.on { background: #4caf50; }
.sse-dot.off { background: #9e9e9e; }
.sse-title { font-size: 11px; font-weight: 600; color: var(--color-text, #333); }
.sse-status { font-size: 9px; color: var(--color-text-muted, #999); margin-left: auto; }
.sse-body { flex: 1; overflow-y: auto; padding: 4px 12px; min-height: 0; }
.sse-empty { padding: 20px; text-align: center; color: var(--color-text-muted, #999); font-size: 11px; }
.sse-event { display: flex; gap: 6px; padding: 2px 0; font-size: 10px; align-items: baseline; }
.sse-event.worker_done .evt-text { color: #2e7d32; }
.evt-time { color: var(--color-text-muted, #999); flex-shrink: 0; font-family: monospace; font-size: 9px; }
.evt-type { color: var(--color-primary, #1976d2); flex-shrink: 0; width: 50px; font-size: 9px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.evt-text { color: var(--color-text, #333); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
