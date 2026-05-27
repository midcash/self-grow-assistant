<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getActivity, type ActivityEntry } from '@/api/agent'

const logs = ref<ActivityEntry[]>([])
const loading = ref(true)

async function refresh() {
  loading.value = true
  try { logs.value = await getActivity(12) } catch { logs.value = [] }
  loading.value = false
}

onMounted(refresh)
defineExpose({ refresh })
</script>

<template>
  <div class="activity-log">
    <div class="log-header">
      <span class="log-title">Agent 活动日志</span>
      <button class="refresh-btn" @click="refresh" :disabled="loading">刷新</button>
    </div>
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="logs.length === 0" class="empty">暂无活动记录</div>
    <div v-else class="log-list">
      <div v-for="log in logs" :key="log.file" class="log-item">
        <div class="log-head">
          <span class="log-time">{{ log.time?.slice(0,16) || log.file?.slice(0,16) }}</span>
          <span v-if="log.elapsed" class="log-elapsed">{{ log.elapsed }}</span>
        </div>
        <div class="log-msg">{{ log.message || '—' }}</div>
        <!-- Worker 调用链 -->
        <div v-if="log.workers?.length" class="worker-chain">
          <span v-for="(w, i) in log.workers" :key="i" class="worker-tag" :class="w.result === 'OK' ? 'ok' : 'fail'">
            {{ w.name }}
            <span v-if="w.elapsed" class="worker-time">({{ w.elapsed }})</span>
            <span v-if="i < log.workers.length - 1" class="arrow">→</span>
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.activity-log { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.log-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px 8px; border-bottom: 1px solid var(--color-border); }
.log-title { font-size: 13px; font-weight: 600; color: var(--color-text); }
.refresh-btn { font-size: 11px; padding: 3px 10px; border-radius: 6px; border: 1px solid var(--color-border); background: var(--color-bg); color: var(--color-text-muted); cursor: pointer; }
.loading, .empty { padding: 24px; text-align: center; font-size: 12px; color: var(--color-text-muted); }
.log-list { flex: 1; overflow-y: auto; padding: 0 16px; }
.log-item { padding: 10px 0; border-bottom: 1px solid var(--color-border); }
.log-head { display: flex; justify-content: space-between; align-items: center; }
.log-time { font-size: 11px; color: var(--color-text-muted); }
.log-elapsed { font-size: 10px; color: var(--color-accent); }
.log-msg { font-size: 12px; color: var(--color-text); margin-top: 2px; }
.worker-chain { display: flex; align-items: center; gap: 2px; margin-top: 6px; flex-wrap: wrap; }
.worker-tag { font-size: 10px; padding: 1px 6px; border-radius: 4px; display: flex; align-items: center; gap: 2px; }
.worker-tag.ok { background: #E8F5E9; color: #2E7D32; }
.worker-tag.fail { background: #FFEBEE; color: #C62828; }
.worker-time { opacity: 0.6; font-size: 9px; }
.arrow { color: var(--color-text-muted); margin: 0 2px; font-size: 11px; }
</style>
