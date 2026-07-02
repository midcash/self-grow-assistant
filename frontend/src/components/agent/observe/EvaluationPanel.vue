<script setup lang="ts">
/** EvaluationPanel — Agent评估面板

  状态: Empty / Loading / Running / Error / HasRuns
  左侧: 运行历史列表 + 运行按钮
  右侧: 选中运行的详情 (Score / Dimensions / Results / Gates)
*/
import { ref, computed, onMounted } from 'vue'
import { useEvaluation } from '@/composables/useEvaluation'

const {
  runs, selectedRunDetail, lastReport,
  loading, running, error,
  fetchRuns, selectRun, triggerRun,
} = useEvaluation()

const selectedRunId = ref<number | null>(null)
const detailTab = ref<'overview' | 'results'>('overview')
const runConfig = ref({
  name: 'manual',
  components: ['prompt', 'tool_call', 'reasoning', 'rag', 'trajectory'],
  workers: [] as string[],
  tags: [] as string[],
  gates: ['smoke'],
})

const latestScore = computed(() => lastReport.value?.dimension_scores ?? {})

onMounted(() => fetchRuns())

async function handleRun() {
  await triggerRun(runConfig.value)
}

async function handleSelectRun(id: number) {
  selectedRunId.value = id
  await selectRun(id)
}

function formatTime(iso: string): string {
  if (!iso) return ''
  return iso.replace('T', ' ').slice(0, 19)
}

function scoreClass(score: number): string {
  if (score >= 4) return 'score-good'
  if (score >= 3) return 'score-ok'
  return 'score-bad'
}
</script>

<template>
  <div class="eval-panel">
    <!-- Header -->
    <div class="eval-header">
      <div class="eval-header-left">
        <h3>Agent Evaluation</h3>
        <span v-if="lastReport" class="last-run-info">
          Latest: <span :class="lastReport.passed ? 'pass' : 'fail'">{{ lastReport.passed ? 'PASS' : 'FAIL' }}</span>
        </span>
      </div>
      <button class="run-btn" :disabled="running" @click="handleRun">
        {{ running ? 'Running...' : 'Run Evaluation' }}
      </button>
    </div>

    <!-- Running overlay -->
    <div v-if="running" class="eval-running">
      <div class="running-spinner" />
      <span>Evaluation in progress...</span>
    </div>

    <!-- Error -->
    <div v-if="error && !loading" class="eval-error">
      <span>{{ error }}</span>
      <button @click="fetchRuns()">Retry</button>
    </div>

    <!-- Loading -->
    <div v-if="loading && runs.length === 0" class="eval-loading">
      <div class="skeleton" v-for="i in 3" :key="i">
        <div class="skeleton-line w-60" />
        <div class="skeleton-line w-40" />
      </div>
    </div>

    <!-- Empty -->
    <div v-if="!loading && !error && !running && runs.length === 0" class="eval-empty">
      <p>No evaluation runs yet.</p>
      <p class="hint">Run an evaluation to measure Agent quality across prompt, tool calling, reasoning, RAG, and trajectory dimensions.</p>
      <button class="run-btn primary" @click="handleRun">Run First Evaluation</button>
    </div>

    <!-- Has runs: list + detail -->
    <template v-if="runs.length > 0">
      <div class="eval-layout">
        <!-- Left: runs list -->
        <aside class="eval-list">
          <div
            v-for="r in runs"
            :key="r.id"
            class="eval-run-item"
            :class="{ selected: selectedRunId === r.id }"
            @click="handleSelectRun(r.id)"
          >
            <div class="eval-run-top">
              <span class="eval-run-name">{{ r.eval_name }}</span>
              <span class="eval-badge" :class="r.passed ? 'pass' : 'fail'">
                {{ r.passed ? 'PASS' : 'FAIL' }}
              </span>
            </div>
            <div class="eval-run-meta">
              <span class="eval-score" :class="scoreClass(r.score)">{{ r.score.toFixed(1) }}</span>
              <span class="eval-time">{{ formatTime(r.created_at) }}</span>
            </div>
          </div>
          <div class="eval-list-count">{{ runs.length }} runs</div>
        </aside>

        <!-- Right: detail -->
        <main class="eval-detail" v-if="selectedRunDetail">
          <!-- Detail tabs -->
          <div class="detail-tabs">
            <button
              v-for="t in [{k:'overview',l:'Overview'},{k:'results',l:'Results'}]"
              :key="t.k"
              class="detail-tab-btn"
              :class="{ active: detailTab === t.k }"
              @click="detailTab = t.k as any"
            >{{ t.l }}</button>
          </div>

          <!-- Overview tab -->
          <div v-if="detailTab === 'overview'" class="eval-overview">
            <div class="pass-fail-banner" :class="selectedRunDetail.run.passed ? 'banner-pass' : 'banner-fail'">
              <span class="banner-icon">{{ selectedRunDetail.run.passed ? 'PASS' : 'FAIL' }}</span>
              <span class="banner-score">Score: {{ selectedRunDetail.run.score.toFixed(1) }}</span>
              <span class="banner-time">{{ selectedRunDetail.run.duration_ms }}ms</span>
            </div>

            <!-- Dimension scores -->
            <div class="dim-scores" v-if="Object.keys(selectedRunDetail.run.metrics).length">
              <h4>Dimension Scores</h4>
              <div class="dim-bar" v-for="(score, dim) in selectedRunDetail.run.metrics" :key="dim">
                <span class="dim-label">{{ dim }}</span>
                <div class="dim-track">
                  <div class="dim-fill" :class="scoreClass(score)" :style="{ width: (score / 5 * 100) + '%' }" />
                </div>
                <span class="dim-value">{{ score.toFixed(1) }}</span>
              </div>
            </div>

            <!-- Component summaries -->
            <div class="comp-summaries" v-if="Object.keys(selectedRunDetail.run.summary).length">
              <h4>Components</h4>
              <div class="comp-row" v-for="(s, comp) in selectedRunDetail.run.summary" :key="comp">
                <span class="comp-name">{{ comp }}</span>
                <span class="comp-stat">{{ s.passed }}/{{ s.total }} passed</span>
                <span class="comp-avg" :class="scoreClass(s.avg_score)">{{ s.avg_score.toFixed(1) }}</span>
              </div>
            </div>
          </div>

          <!-- Results tab -->
          <div v-if="detailTab === 'results'" class="eval-results">
            <div class="result-item" v-for="r in selectedRunDetail.results" :key="r.id">
              <div class="result-header">
                <span class="result-id">{{ r.example_id }}</span>
                <span class="result-worker">{{ r.worker }}</span>
                <span class="result-score" :class="r.passed ? 'pass' : 'fail'">{{ r.score.toFixed(1) }}</span>
              </div>
              <div class="result-dims" v-if="Object.keys(r.dimension_scores).length">
                <span class="dim-chip" v-for="(s, d) in r.dimension_scores" :key="d">{{ d }}: {{ s }}</span>
              </div>
              <div class="result-reasoning" v-if="r.reasoning">{{ r.reasoning }}</div>
            </div>
          </div>
        </main>

        <main v-else class="eval-detail-empty">
          Select a run to see details
        </main>
      </div>
    </template>
  </div>
</template>

<style scoped>
.eval-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}
.eval-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--color-border, #e0e0e0);
}
.eval-header-left { display: flex; align-items: center; gap: 12px; }
.eval-header-left h3 { margin: 0; font-size: 13px; }
.last-run-info { font-size: 11px; color: var(--color-text-muted, #999); }
.run-btn {
  font-size: 11px;
  padding: 4px 12px;
  border-radius: 4px;
  border: 1px solid var(--color-border, #e0e0e0);
  background: var(--color-bg, #fff);
  color: var(--color-text, #333);
  cursor: pointer;
}
.run-btn.primary { background: var(--color-primary, #1976d2); color: #fff; border: none; padding: 6px 16px; }
.run-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.eval-running {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: var(--color-primary-light, #e3f2fd);
  font-size: 12px;
}
.running-spinner {
  width: 16px; height: 16px;
  border: 2px solid var(--color-primary, #1976d2);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.eval-error { padding: 12px; color: #c62828; font-size: 12px; display: flex; gap: 8px; align-items: center; }
.eval-loading { padding: 12px; }
.skeleton { padding: 8px 0; }
.skeleton-line { height: 12px; background: #e0e0e0; border-radius: 4px; margin: 4px 0; }
.skeleton-line.w-60 { width: 60%; }
.skeleton-line.w-40 { width: 40%; }
.eval-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--color-text-muted, #999);
  font-size: 13px;
}
.eval-empty .hint { font-size: 11px; max-width: 300px; text-align: center; }
.eval-layout { flex: 1; display: flex; overflow: hidden; min-height: 0; }
.eval-list {
  width: 35%;
  min-width: 120px;
  max-width: 220px;
  border-right: 1px solid var(--color-border, #e0e0e0);
  overflow-y: auto;
}
.eval-run-item {
  padding: 8px 10px;
  border-bottom: 1px solid var(--color-border, #f0f0f0);
  cursor: pointer;
  font-size: 11px;
}
.eval-run-item:hover { background: var(--color-bg-hover, #f5f5f5); }
.eval-run-item.selected { background: var(--color-primary-light, #e3f2fd); }
.eval-run-top { display: flex; justify-content: space-between; align-items: center; }
.eval-run-name { font-weight: 500; }
.eval-run-meta { display: flex; gap: 8px; margin-top: 4px; color: var(--color-text-muted, #999); }
.eval-score { font-weight: 600; }
.eval-time { font-size: 10px; }
.eval-badge { font-size: 10px; padding: 1px 6px; border-radius: 3px; font-weight: 600; }
.eval-badge.pass { background: #e8f5e9; color: #2e7d32; }
.eval-badge.fail { background: #ffebee; color: #c62828; }
.eval-list-count { padding: 6px 10px; font-size: 10px; color: var(--color-text-muted, #999); border-top: 1px solid var(--color-border, #f0f0f0); }
.eval-detail { flex: 1; overflow-y: auto; min-width: 0; }
.eval-detail-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--color-text-muted, #999);
}
.detail-tabs {
  display: flex;
  gap: 2px;
  padding: 6px 10px;
  border-bottom: 1px solid var(--color-border, #e0e0e0);
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
.pass-fail-banner {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  margin: 8px;
  border-radius: 6px;
}
.banner-pass { background: #e8f5e9; }
.banner-fail { background: #ffebee; }
.banner-icon { font-size: 24px; font-weight: 700; }
.banner-pass .banner-icon { color: #2e7d32; }
.banner-fail .banner-icon { color: #c62828; }
.banner-score { font-size: 18px; font-weight: 600; }
.banner-time { font-size: 11px; color: var(--color-text-muted, #999); margin-left: auto; }
.dim-scores, .comp-summaries { padding: 8px 16px; }
.dim-scores h4, .comp-summaries h4 { font-size: 12px; margin: 0 0 8px; }
.dim-bar { display: flex; align-items: center; gap: 8px; margin: 4px 0; }
.dim-label { width: 90px; font-size: 11px; text-align: right; }
.dim-track { flex: 1; height: 8px; background: #e0e0e0; border-radius: 4px; overflow: hidden; }
.dim-fill { height: 100%; border-radius: 4px; transition: width 0.3s; }
.dim-fill.score-good { background: #4caf50; }
.dim-fill.score-ok { background: #ff9800; }
.dim-fill.score-bad { background: #f44336; }
.dim-value { width: 30px; font-size: 11px; font-weight: 600; }
.comp-row { display: flex; align-items: center; gap: 12px; padding: 3px 0; font-size: 11px; }
.comp-name { width: 80px; }
.comp-stat { color: var(--color-text-muted, #999); }
.comp-avg { font-weight: 600; margin-left: auto; }
.eval-results { padding: 8px; }
.result-item {
  padding: 8px;
  margin: 4px 0;
  border: 1px solid var(--color-border, #e0e0e0);
  border-radius: 4px;
  font-size: 11px;
}
.result-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.result-id { font-weight: 500; }
.result-worker { color: var(--color-text-muted, #999); font-size: 10px; }
.result-score { margin-left: auto; font-weight: 600; }
.result-score.pass { color: #2e7d32; }
.result-score.fail { color: #c62828; }
.result-dims { display: flex; gap: 6px; flex-wrap: wrap; margin: 4px 0; }
.dim-chip {
  font-size: 10px;
  padding: 1px 5px;
  background: #f5f5f5;
  border-radius: 3px;
}
.result-reasoning {
  font-size: 10px;
  color: var(--color-text-muted, #999);
  margin-top: 4px;
  line-height: 1.4;
}
.score-good { color: #2e7d32; }
.score-ok { color: #e65100; }
.score-bad { color: #c62828; }
</style>
