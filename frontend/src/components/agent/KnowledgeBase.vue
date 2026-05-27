<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getKnowledge, type KnowledgeStatus, type McpTool } from '@/api/agent'

const status = ref<KnowledgeStatus>({ connected: false })
const loading = ref(true)

async function refresh() {
  loading.value = true
  try { status.value = await getKnowledge() } catch { status.value = { connected: false, message: '查询失败' } }
  loading.value = false
}

onMounted(refresh)
defineExpose({ refresh })
</script>

<template>
  <div class="knowledge-base">
    <div class="kb-header">
      <span class="kb-title">MCP 工具</span>
      <div class="kb-status">
        <span class="kb-dot" :class="{ on: status.connected }"></span>
        {{ status.connected ? status.server || '已连接' : '未连接' }}
      </div>
    </div>
    <div v-if="loading" class="loading">连接中...</div>
    <div v-else-if="!status.connected" class="empty">
      <p>MCP 服务未连接</p>
      <p class="hint">配置 agent-config.yaml 中的 mcp_servers</p>
    </div>
    <div v-else class="kb-content">
      <!-- MCP 工具列表 -->
      <div v-if="status.tools?.length" class="tools-section">
        <div class="section-title">可用工具 ({{ status.tools.length }})</div>
        <div v-for="tool in status.tools" :key="tool.name" class="tool-item">
          <div class="tool-name">{{ tool.name }}</div>
          <div class="tool-desc">{{ tool.description || '—' }}</div>
        </div>
      </div>
      <!-- 知识库文集 -->
      <div v-if="status.collections" class="collections-section">
        <div class="section-title">知识库文档</div>
        <pre class="collections-text">{{ status.collections }}</pre>
      </div>
    </div>
  </div>
</template>

<style scoped>
.knowledge-base { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.kb-header { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px 8px; border-bottom: 1px solid var(--color-border); }
.kb-title { font-size: 13px; font-weight: 600; color: var(--color-text); }
.kb-status { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--color-text-muted); }
.kb-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--color-border); }
.kb-dot.on { background: var(--color-success); }
.loading, .empty { padding: 24px; text-align: center; font-size: 12px; color: var(--color-text-muted); }
.hint { font-size: 10px; margin-top: 4px; color: var(--color-text-muted); }
.kb-content { flex: 1; overflow-y: auto; padding: 0 16px; }
.section-title { font-size: 11px; font-weight: 600; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.5px; padding: 12px 0 6px; }
.tools-section, .collections-section { border-bottom: 1px solid var(--color-border); padding-bottom: 8px; }
.tool-item { padding: 6px 0; }
.tool-name { font-size: 12px; color: var(--color-text); font-weight: 500; }
.tool-desc { font-size: 11px; color: var(--color-text-muted); margin-top: 1px; }
.collections-text { font-size: 11px; color: var(--color-text-light); white-space: pre-wrap; margin: 4px 0; font-family: var(--font-sans); }
</style>
