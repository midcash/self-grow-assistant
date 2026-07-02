<script setup lang="ts">
/** ObservePanel — Agent 数据流观测页入口
 *
 *  左右分栏布局:
 *  左侧 40%: 筛选栏 + 编排历史列表
 *  右侧 60%: Trace 瀑布图
 *  底部: 指标汇总条
 */
import { ref, onMounted, onUnmounted } from 'vue'
import { useObserve } from '@/composables/useObserve'
import ObserveFilterBar from './ObserveFilterBar.vue'
import OrchestrationList from './OrchestrationList.vue'
import TraceWaterfall from './TraceWaterfall.vue'
import AgentTopology from './AgentTopology.vue'
import MetricsDashboard from './MetricsDashboard.vue'
import SSEMonitor from './SSEMonitor.vue'
import MetricsStickyBar from './MetricsStickyBar.vue'
import EvaluationPanel from './EvaluationPanel.vue'

const {
  orchestrations, currentTraceSpans, metrics, filter, selectedOrchestrationId,
  selectedOrchestration, loading, error,
  fetchList, selectOrchestration, fetchMetrics, updateFilter, refresh,
  startAutoRefresh, stopAutoRefresh,
} = useObserve()


const detailTab = ref<string>('waterfall')

onMounted(() => {
  fetchList()
  fetchMetrics(7)
  startAutoRefresh(5000)
})

onUnmounted(() => stopAutoRefresh())
</script>

<template>
  <div class="observe-panel">
    <!-- 左侧: 列表 -->
    <aside class="list-panel">
      <ObserveFilterBar :filter="filter" @change="(f: any) => updateFilter(f)" />
      <OrchestrationList
        :items="orchestrations"
        :selectedId="selectedOrchestrationId"
        :loading="loading"
        @select="selectOrchestration"
      />
      <div class="list-footer">
        <span v-if="error" class="error-text">{{ error }}</span>
        <span v-else class="count-text">{{ orchestrations.length }} 条记录</span>
        <button class="refresh-btn" @click="refresh" :disabled="loading">刷新</button>
      </div>
    </aside>

    <!-- 右侧: 详情 -->
    <main class="detail-panel">
      <!-- Tabs: always visible -->
      <div class="detail-tabs">
        <button
          v-for="t in [{k:'waterfall',l:'瀑布图'},{k:'topology',l:'拓扑'},{k:'metrics',l:'指标'},{k:'evaluation',l:'评估'}]"
          :key="t.k"
          class="detail-tab-btn"
          :class="{ active: detailTab === t.k }"
          @click="detailTab = t.k"
        >{{ t.l }}</button>
        <span v-if="selectedOrchestrationId" class="detail-orch-id">#{{ selectedOrchestrationId?.slice(0, 8) }}</span>
      </div>

      <!-- Evaluation tab: works without orchestration selection -->
      <EvaluationPanel v-if="detailTab === 'evaluation'" />

      <!-- Other tabs: require orchestration selection -->
      <template v-else-if="selectedOrchestrationId">
        <TraceWaterfall
          v-if="detailTab === 'waterfall'"
          :spans="currentTraceSpans"
          :loading="loading"
        />
        <AgentTopology v-else-if="detailTab === 'topology'" :metrics="metrics" />
        <MetricsDashboard v-else-if="detailTab === 'metrics'" :metrics="metrics" />
      </template>

      <div v-else class="empty-detail">
        <span class="empty-icon">◷</span>
        <p>从左侧列表选择一个编排查看详情</p>
        <p class="hint">发送复杂请求后自动生成编排记录</p>
      </div>
      <SSEMonitor />
    </main>
    <MetricsStickyBar :metrics="metrics" />
  </div>
</template>

<style scoped>
.observe-panel {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.list-panel {
  width: 42%;
  min-width: 150px;
  max-width: 260px;
  border-right: 1px solid var(--color-border, #e0e0e0);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.detail-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}
.list-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  font-size: 10px;
  color: var(--color-text-muted, #999);
  border-top: 1px solid var(--color-border, #e0e0e0);
}
.error-text { color: #c62828; }
.count-text { flex: 1; }
.refresh-btn {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid var(--color-border, #e0e0e0);
  background: var(--color-bg, #fff);
  color: var(--color-text-muted, #999);
  cursor: pointer;
}
.detail-tabs {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 6px 12px;
  border-bottom: 1px solid var(--color-border, #e0e0e0);
  background: var(--color-bg, #fafafa);
}
.detail-tab-btn {
  font-size: 11px;
  padding: 3px 10px;
  border: none;
  background: transparent;
  color: var(--color-text-muted, #999);
  cursor: pointer;
  border-radius: 4px;
}
.detail-tab-btn.active {
  background: var(--color-primary-light, #e3f2fd);
  color: var(--color-primary, #1976d2);
  font-weight: 600;
}
.detail-orch-id {
  margin-left: auto;
  font-size: 10px;
  color: var(--color-text-muted, #999);
  font-family: monospace;
}
.empty-detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted, #999);
  gap: 8px;
}
.empty-icon { font-size: 32px; opacity: 0.5; }
.empty-detail p { font-size: 12px; margin: 0; }
.empty-detail .hint { font-size: 11px; opacity: 0.6; }
.placeholder-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: var(--color-text-muted, #999);
}
</style>
