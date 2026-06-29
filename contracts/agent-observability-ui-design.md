# Agent 数据流观测页面设计文档 (Observe Tab)

> 版本: v0.1
> 目标读者: 前端开发、全栈开发
> 对应规格: `contracts/goal-achievement-level3-spec.md` — Phase 0: Observability + Safety Foundation
> 成熟度: 🔴 草稿

---

## 目录

1. 页面概述与定位
2. 页面布局线框图 (ASCII)
3. 组件树 (Vue 组件层级)
4. 各组件规格 (Props / State / Computed / Methods)
5. 数据流图 (SSE + REST → UI)
6. 状态管理设计 (useAgent 扩展 vs 局部状态)
7. 边界状态处理
8. 交互设计
9. 实施步骤

---

## 1. 页面概述与定位

### 1.1 背景

当前 `AgentPanel.vue` 有 4 个 tab: 对话 / 任务 / 日志 / 知识库。"日志" tab 中的 `ActivityLog.vue` 通过正则解析 Markdown 文件来展示 Worker 调用记录，存在以下问题:

- 无结构化数据，正则解析脆弱
- 无时序可视化，无法直观看出编排流程
- 无指标聚合，无法回答"哪个 Worker 最慢"
- 无实时推送，需手动刷新
- 无拓扑关系展示

### 1.2 本次设计目标

在 Agent 面板中新增第 5 个 tab "观察" (Observe)，提供 5 个功能区块:

| 区块 | 用途 | 数据源 |
|------|------|--------|
| A. 编排历史列表 | 左侧展示最近 orchestration 记录 | `GET /traces?limit=` |
| B. Trace 瀑布图 | 主视图，展示单次编排的 span 时序 | `GET /traces/{id}` |
| C. Agent 拓扑图 | Worker 注册关系与路由频率 | `GET /metrics` |
| D. 指标面板 | 成功率、延迟趋势、错误分布 | `GET /metrics?days=` |
| E. 实时 SSE 监控 | 当前编排的实时进度 | SSE `/chat/stream` |

### 1.3 与现有架构的关系

```
AgentPanel.vue (380px sidebar)
  ├── Tab: 对话 (chat)       ← 不变
  ├── Tab: 任务 (tasks)      ← 不变
  ├── Tab: 日志 (log)        ← 不变 (向后兼容)
  ├── Tab: 知识库 (kb)       ← 不变
  └── Tab: 观察 (observe)    ← 新增，本文档主体
        ├── OrchestrationList   ← A
        ├── TraceWaterfall      ← B
        ├── AgentTopology       ← C
        ├── MetricsDashboard    ← D
        └── SSEMonitor          ← E
```

---

## 2. 页面布局线框图 (ASCII)

整个 tab 区域是一个**左右分栏布局**，左侧 40% 为编排列表，右侧 60% 为详情视图 + 下方指标。

```
┌─────────────────────────────────────────────────┐
│ 观察 (Observe)  Tab                              │
├──────────────────────┬──────────────────────────┤
│ [左侧 40%]            │ [右侧 60%]                │
│                      │                          │
│ ┌─── 筛选栏 ──────┐  │ ┌─── TabBar ──────────┐  │
│ │ Agent: [▼]      │  │ │ 瀑布图 │ 拓扑 │ 指标  │  │
│ │ 日期: [input]   │  │ └────────────────────┘  │
│ │ 状态: [全部][OK] │  │                          │
│ │ [FAIL]          │  │   [上下文切换区]          │
│ └────────────────┘  │                          │
│                      │  ┌ 默认: TraceWaterfall  │
│ ┌─── 列表 ────────┐  │  │                      │
│ │ 09:15 搜索攻略    │  │  ┌──────────────────┐  │
│ │ searcher+profile │  │  │ plan   ████ 450ms│  │
│ │ 1.2s ✓          │  │  │ worker ██████ 800ms│  │
│ ├─────────────────┤  │  │ synth  ██   200ms│  │
│ │ 09:10 辅导焦虑    │  │  │ safety █     30ms│  │
│ │ coach           │  │  │ persist ██   100ms│  │
│ │ 3.5s ✓          │  │  └──────────────────┘  │
│ ├─────────────────┤  │                          │
│ │ ...             │  │  ┌─── SSE Monitor ────┐  │
│ │                 │  │  │ ◉ plan: 分析意图... │  │
│ └────────────────┘  │  │ ◎ worker: searcher  │  │
│                      │  │ ◉ synthesis: 生成.. │  │
│  [自动刷新 3s]       │  └────────────────────┘  │
│                      │                          │
├──────────────────────┴──────────────────────────┤
│ Metrics Bar (底部)                               │
│ 总编排: 42  │  成功率: 95%  │  平均延迟: 1.2s    │
└─────────────────────────────────────────────────┘
```

### 2.1 移动端 / 窄屏适配 (< 640px)

当 sidebar 宽度不足以展示左右分栏时，切换为上下结构:

```
┌──────────────────────┐
│ TabBar: 列表｜瀑布｜拓扑│指标│监控 │
├──────────────────────┤
│ [当前选中面板全宽]    │
│                      │
│ 例如「列表」被选中:    │
│ ┌─── 筛选栏 ──────┐  │
│ │ ...              │  │
│ └──────────────────┘  │
│ ┌─── 列表 ────────┐  │
│ │ ...              │  │
│ └──────────────────┘  │
└──────────────────────┘
```

---

## 3. 组件树 (Vue 组件层级)

```
AgentPanel.vue
  └── ObservePanel.vue                          ← 新入口组件，管理观察 Tab
        ├── ObserveFilterBar.vue                ← 筛选栏 (agent_name, date, status)
        ├── OrchestrationList.vue               ← A: 编排历史列表
        │     └── OrchestrationItem.vue          ← 单条编排条目
        ├── ObserveDetailArea.vue               ← 右侧详情容器 (含子 tab)
        │     ├── TraceWaterfall.vue             ← B: 瀑布图 (主视图)
        │     │     └── SpanBar.vue              ← 单个 span 条
        │     │           └── SpanTooltip.vue    ← hover 浮层
        │     │           └── SpanDetailDrawer.vue ← click 展开详情抽屉
        │     ├── AgentTopology.vue              ← C: 拓扑图
        │     │     └── TopologyNode.vue         ← 单个 worker 节点
        │     ├── MetricsDashboard.vue           ← D: 指标面板
        │     │     ├── MetricsSummaryBar.vue    ← 顶部汇总数字
        │     │     ├── WorkerSuccessChart.vue   ← 成功率柱状图 (纯CSS)
        │     │     ├── LatencyTrendChart.vue    ← 延迟趋势折线图 (纯CSS)
        │     │     └── ErrorPieChart.vue        ← 错误分布饼图 (纯CSS)
        │     └── SSEMonitor.vue                 ← E: 实时监控面板
        │           └── SSEEventItem.vue          ← 单个 SSE 事件条目
        └── MetricsStickyBar.vue                 ← 底部全局指标条
```

### 3.1 组件依赖关系

```
ObservePanel
  ├── 依赖: useObserve (新 composable)
  ├── 依赖: useSSE (新 composable)
  └── 子组件通过 Provide/Inject 共享 selectedOrchestrationId
```

---

## 4. 各组件规格

### 4.1 ObservePanel.vue — 观察面板入口

**职责**: 管理左右分栏布局、子 tab 切换、筛选状态同步

**Props**: 无

**State**:

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `selectedOrchestrationId` | `string \| null` | `null` | 当前选中的编排 ID |
| `detailTab` | `'waterfall' \| 'topology' \| 'metrics'` | `'waterfall'` | 详情区子 tab |
| `filter` | `ObserveFilter` | `{ limit: 20 }` | 当前筛选条件 |
| `orchestrations` | `OrchestrationSummary[]` | `[]` | 编排列表数据 |
| `loading` | `boolean` | `false` | 是否正在加载 |
| `error` | `string \| null` | `null` | 错误信息 |
| `autoRefresh` | `boolean` | `true` | 是否自动刷新 |

**Computed**:

| 属性 | 类型 | 说明 |
|------|------|------|
| `selectedOrchestration` | `OrchestrationSummary \| null` | 从 `orchestrations` 中查找 ID 匹配项 |
| `hasSelection` | `boolean` | 是否有选中编排 |
| `isNarrowMode` | `boolean` | 根据容器宽度判断是否启用窄屏模式 |

**Methods**:

| 方法 | 说明 |
|------|------|
| `fetchList()` | 调用 API 获取编排列表 |
| `selectOrchestration(id)` | 选中一个编排，触发详情加载 |
| `onFilterChange(newFilter)` | 筛选条件变化时重新加载 |
| `toggleAutoRefresh()` | 切换自动刷新 |

**Key Template 结构**:

```html
<div class="observe-panel" :class="{ narrow: isNarrowMode }">
  <!-- 左栏: 列表 -->
  <aside class="list-panel">
    <ObserveFilterBar :filter="filter" @change="onFilterChange" />
    <OrchestrationList
      :items="orchestrations"
      :selectedId="selectedOrchestrationId"
      :loading="loading"
      @select="selectOrchestration"
    />
  </aside>

  <!-- 右栏: 详情 -->
  <main class="detail-panel">
    <template v-if="hasSelection">
      <div class="detail-tabs">
        <button v-for="tab in detailTabs" ...>...</button>
      </div>
      <TraceWaterfall v-if="detailTab === 'waterfall'" :orchestrationId />
      <AgentTopology v-else-if="detailTab === 'topology'" />
      <MetricsDashboard v-else-if="detailTab === 'metrics'" />
      <SSEMonitor class="sse-panel" />
    </template>
    <EmptyState v-else message="请从左侧选择一个编排" />
  </main>

  <!-- 底部指标条 -->
  <MetricsStickyBar />
</div>
```

**样式要点**:

```css
.observe-panel {
  display: flex;
  flex: 1;
  min-height: 0; /* 关键: 让 flex 子项可滚动 */
  position: relative;
}
.list-panel {
  width: 40%;
  min-width: 160px;
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
}
.detail-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow-y: auto;
}
.narrow .list-panel {
  width: 100%;
  border-right: none;
  max-height: 50%;
}
```

---

### 4.2 ObserveFilterBar.vue — 筛选栏

**Props**:

| 属性 | 类型 | 说明 |
|------|------|------|
| `filter` | `ObserveFilter` | 当前筛选条件 |
| `agentOptions` | `string[]` | 可选的 agent 列表 |

**Emits**: `change(newFilter: ObserveFilter)`

**State**: 内部编辑状态，确认后 emit

**UI 元素**:
- Agent 名称下拉: `全部 / searcher / profiler / executor / coach / goal_decomposer`
- 日期选择器 (input type="date")
- 状态按钮组: `全部 | 成功 | 失败` (pill 按钮)
- 时间范围: `今天 | 最近7天 | 最近30天` (预设快捷按钮)

**边界处理**:
- 当 filter 全部为空时，显示轻提示 "显示全部编排"
- 日期选择器默认聚焦当日，可通过快捷按钮切换

---

### 4.3 OrchestrationList.vue — 编排历史列表

**Props**:

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `items` | `OrchestrationSummary[]` | `[]` | 编排列表 |
| `selectedId` | `string \| null` | `null` | 当前选中 ID |
| `loading` | `boolean` | `false` | 加载状态 |

**Emits**: `select(id: string)`

**OrchestrationSummary 数据类型**:

```typescript
interface OrchestrationSummary {
  orchestration_id: string       // UUID
  intent: string                 // 意图，如 "travel_planning"
  workers_used: string[]         // ["searcher", "profiler"]
  total_latency_ms: number
  success: boolean               // 所有 span 都成功 = true
  created_at: string             // ISO datetime
  reply_preview: string          // 回复前 80 字
}
```

**渲染**:

每条条目展示:
- 左侧: 时间 (`09:15`，格式化为 `HH:mm`)
- 中间: intent 文本 + workers_used 标签列表 (彩色 pill)
- 右侧: 延迟 (彩色文字) + 成功/失败图标

**Empty State**:

```html
<div class="empty">
  <p>暂无编排记录</p>
  <p class="hint">发送复杂请求（如"帮我安排明天"）后会自动生成</p>
</div>
```

**Loading State**: 5 行骨架屏 (skeleton)，每行 3 个不同宽度的灰色块脉冲动画

**Error State**: 显示重试按钮和错误消息

---

### 4.4 OrchestrationItem.vue — 单条编排条目

**Props**:

| 属性 | 类型 | 说明 |
|------|------|------|
| `item` | `OrchestrationSummary` | 编排数据 |
| `selected` | `boolean` | 是否被选中 |

**Emits**: `click`

**渲染细节**:

```html
<div class="orchestration-item" :class="{ selected, failed: !item.success }" @click="$emit('click')">
  <div class="item-left">
    <span class="item-time">{{ formatTime(item.created_at) }}</span>
  </div>
  <div class="item-body">
    <div class="item-intent">{{ item.intent }}</div>
    <div class="item-workers">
      <span v-for="w in item.workers_used" class="worker-pill" :class="w">
        {{ w }}
      </span>
    </div>
  </div>
  <div class="item-right">
    <span class="item-latency">{{ formatMs(item.total_latency_ms) }}</span>
    <span class="item-status" :class="{ ok: item.success, fail: !item.success }">
      {{ item.success ? '✓' : '✗' }}
    </span>
  </div>
</div>
```

**样式要点**: `selected` 状态用高亮背景色，`failed` 在左侧加红色边框。

---

### 4.5 TraceWaterfall.vue — Trace 瀑布图 (核心组件)

**Props**:

| 属性 | 类型 | 说明 |
|------|------|------|
| `orchestrationId` | `string` | 编排 ID |
| `spans` | `AgentTraceSpan[]` | span 数据 (从父级或内部加载) |

**AgentTraceSpan 数据类型**:

```typescript
interface AgentTraceSpan {
  id: string
  orchestration_id: string
  span_type: 'plan' | 'worker_dispatch' | 'worker_execute' | 'synthesis' | 'safety_check' | 'persist'
  agent_name: string        // orchestrator / searcher / profiler / ...
  parent_span_id: string | null
  objective: string
  input_summary: string
  output_summary: string
  latency_ms: number
  token_estimate?: number
  success: boolean
  error_message?: string
  metadata_json?: string     // JSON string
  created_at: string
}
```

**State**:

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `spans` | `AgentTraceSpan[]` | `[]` | span 列表 |
| `loading` | `boolean` | `false` | 是否加载中 |
| `error` | `string \| null` | `null` | 错误信息 |
| `selectedSpan` | `AgentTraceSpan \| null` | `null` | 当前展开的 span |
| `hoveredSpan` | `AgentTraceSpan \| null` | `null` | 当前 hover 的 span |

**Computed**:

| 属性 | 类型 | 说明 |
|------|------|------|
| `totalDuration` | `number` | 所有 span 中最大 `latency_ms`，作为时间轴基准 |
| `orderedSpans` | `AgentTraceSpan[]` | 按 `created_at` + `parent_span_id` 排序的展平列表 |
| `planSpan` | `AgentTraceSpan \| null` | 找到类型为 `plan` 的根 span |
| `workerGroups` | `WorkerSpanGroup[]` | 并行执行的 worker_execute 分组 |
| `spanColorMap` | `Record<string, string>` | span 类型到颜色的映射 |

**CSS 纯色方案** (通过 CSS 变量定义):

```
plan:             #9E9E9E  (--waterfall-plan)        灰色
worker_dispatch:  #90CAF9  (--waterfall-dispatch)    浅蓝
worker_execute:   #42A5F5  (--waterfall-execute)     蓝色
synthesis:        #66BB6A  (--waterfall-synthesis)   绿色
safety_check:     #EF5350 / #66BB6A                  红/绿 (取决于success)
persist:          #AB47BC  (--waterfall-persist)     紫色
```

**瀑布图渲染逻辑**:

时间轴定位算法:
- 每个 span 的 `left` = (该 span 的开始时间 / totalDuration) × 100%
- 每个 span 的 `width` = (该 span 的 latency_ms / totalDuration) × 100%

并行 worker 检测: worker_execute spans 中，时间范围重叠的归为同一组并可视化分组。

**模板结构**:

```html
<div class="trace-waterfall">
  <div class="trace-header">
    <span class="trace-intent">{{ planSpan?.objective }}</span>
    <span class="trace-id">ID: {{ orchestrationId?.slice(0, 8) }}...</span>
  </div>

  <div class="timeline-ruler">
    <div v-for="tick in ticks" class="ruler-tick" :style="{ left: tick.percent + '%' }">
      {{ tick.label }}
    </div>
  </div>

  <div v-if="loading" class="waterfall-loading">
    <div v-for="n in 6" class="skeleton-bar" />
  </div>

  <div v-else-if="!orderedSpans.length" class="waterfall-empty">
    无法加载 Trace 数据
  </div>

  <div v-else class="waterfall-body">
    <div v-for="span in orderedSpans" :key="span.id" class="span-row">
      <div class="span-label">
        <span class="span-type-badge" :style="{ background: spanColorMap[span.span_type] }">
          {{ span.span_type }}
        </span>
        <span class="span-agent">{{ span.agent_name }}</span>
      </div>
      <div class="span-track">
        <div class="span-bar"
          :style="{
            left: barLeft(span) + '%',
            width: barWidth(span) + '%',
            background: spanColorMap[span.span_type],
            opacity: span.success ? 1 : 0.6,
          }"
          @mouseenter="hoveredSpan = span"
          @mouseleave="hoveredSpan = null"
          @click="selectedSpan = span"
        />
      </div>
    </div>
  </div>

  <SpanTooltip v-if="hoveredSpan" :span="hoveredSpan" :pos="mousePos" />
  <SpanDetailDrawer v-if="selectedSpan" :span="selectedSpan" @close="selectedSpan = null" />
</div>
```

**边界处理**:

| 场景 | 处理方式 |
|------|----------|
| 100+ spans (长编排) | 瀑布图可滚动，默认折叠超 20 条，显示 "显示全部 N 条" 按钮 |
| span 延迟为 0 | 显示最小宽度 4px 的细条，保证可见 |
| 失败 span | 半透明 + 红色边框 + 左侧 ! 图标 |
| 无 plan span | 显示 "非编排模式" 提示 |
| totalDuration 为 0 | 特殊处理，均分时间轴 |

---

### 4.6 SpanTooltip.vue — Hover 浮层

**Props**:

| 属性 | 类型 | 说明 |
|------|------|------|
| `span` | `AgentTraceSpan` | span 数据 |
| `pos` | `{ x: number, y: number }` | 鼠标位置 |

**渲染**: 绝对定位的浮层，显示 span_type + agent_name、objective[:60]、latency_ms、success/fail 状态 + error_message(如有)。

---

### 4.7 SpanDetailDrawer.vue — 点击展开抽屉

**Props**:

| 属性 | 类型 | 说明 |
|------|------|------|
| `span` | `AgentTraceSpan` | 被选中的 span |

**Emits**: `close`

**渲染内容**:

```
┌──────────────────────────────────────┐
│ ✕ Span 详情                           │
├──────────────────────────────────────┤
│ span_type: worker_execute             │
│ agent_name: searcher                  │
│ latency: 345ms   success: ✓           │
├──────────────────────────────────────┤
│ Objective                             │
│ ┌──────────────────────────────────┐ │
│ │ 搜索西安热门景点和美食推荐       │ │
│ └──────────────────────────────────┘ │
│                                      │
│ Input (TaskBrief)                     │
│ ┌──────────────────────────────────┐ │
│ │ task_id: searcher                │ │
│ │ objective: 搜索西安...           │ │
│ │ constraints: []                  │ │
│ └──────────────────────────────────┘ │
│                                      │
│ Output (WorkerResult)                 │
│ ┌──────────────────────────────────┐ │
│ │ 西安热门景点:                    │ │
│ │ 1. 兵马俑  2. 大雁塔...         │ │
│ └──────────────────────────────────┘ │
│                                      │
│ Error (如果有)                        │
│ ┌──────────────────────────────────┐ │
│ │ (红色区域，仅当 success=false)   │ │
│ └──────────────────────────────────┘ │
└──────────────────────────────────────┘
```

**边界处理**:
- 内容超长: 默认折叠到 300px 高度，显示 "展开全部" 按钮
- JSON 格式的 output: 用 `<pre>` 格式化显示

---

### 4.8 AgentTopology.vue — Agent 拓扑图

**Props**: 无 (数据由 composable 提供)

**State**:

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `workers` | `WorkerNode[]` | `[]` | 所有已注册 worker |
| `edges` | `RouterEdge[]` | `[]` | 路由边（频率） |
| `selectedWorker` | `string \| null` | `null` | 点击选中的 worker |
| `loading` | `boolean` | `false` | 加载态 |

**数据类型**:

```typescript
interface WorkerNode {
  name: string                    // "searcher"
  label: string                   // "搜索者"
  status: 'active' | 'idle' | 'inactive'
  total_calls: number
  success_rate: number            // 0-100
  avg_latency_ms: number
  last_called_at: string | null
  color: string                   // 节点颜色
}

interface RouterEdge {
  from: string                    // orchestrator | worker_name
  to: string                      // worker_name
  frequency: number               // 路由次数
  recent_count: number            // 最近 7 天路由次数(用于线宽)
}
```

**渲染方式**: CSS Flex 纯布局 (不使用 Canvas / SVG 图表库)

布局方案:

```
               ┌──────────────┐
               │ Orchestrator  │  ← 居中，最大节点
               │   42 calls    │
               └──────┬───────┘
         ┌────────────┼───────┬───────────┐
         ▼            ▼       ▼           ▼
   ┌─────────┐  ┌─────────┐  ┌────────┐  ┌─────────┐
   │ Searcher │  │ Profiler│  │Executor│  │  Coach   │
   │ 15 calls │  │  8 calls│  │12 calls│  │  5 calls │
   │ 92% ✓    │  │  88% ✓  │  │ 100% ✓ │  │  95% ✓   │
   └─────────┘  └─────────┘  └────────┘  └─────────┘
```

**线宽**: `border-width: max(1px, min(6px, frequency / maxFrequency * 6))`

**节点状态**:

| 状态 | 显示 |
|------|------|
| `active` | 实心边框，正常亮度 |
| `idle` | 半透明，灰色文字 (最近 7 天未调用) |
| `inactive` | 完全灰色，斜体 "未注册" 标记 |

**边界处理**:
- 0 个 worker: "Worker 尚未注册"
- 所有 worker inactive: "所有 worker 均处于空闲状态"

---

### 4.9 MetricsDashboard.vue — 指标面板

**Props**:

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `days` | `number` | `7` | 统计天数 |
| `metrics` | `AgentMetrics[]` | `[]` | 指标数据 |
| `loading` | `boolean` | `false` | 加载态 |

**数据类型**:

```typescript
interface AgentMetrics {
  id: number
  date: string
  agent_name: string
  total_calls: number
  success_count: number
  error_count: number
  avg_latency_ms: number
  p50_latency_ms: number
  p95_latency_ms: number
  total_token_estimate: number
}
```

**子组件**:

#### 4.9.1 MetricsSummaryBar.vue — 顶部汇总

纯数字展示:

```
总编排: 42  |  成功率: 95.2%  |  平均延迟: 1.2s |  今日 Token: 128K
```

#### 4.9.2 WorkerSuccessChart.vue — 成功率柱状图 (纯 CSS)

水平柱状图，每个 worker 一行:

```
Searcher     ████████████████████░ 92%   (>=90%: 绿色)
Profiler     ████████████████░░░░ 80%   (75-90%: 黄色)
Executor     ████████████████████ 100%  (>=90%: 绿色)
Coach        ██████████████████░░ 88%   (75-90%: 黄色)
```

CSS 实现: 每个 bar 是 `div`，宽度用 `style.width = rate + '%'`。

#### 4.9.3 LatencyTrendChart.vue — 延迟趋势图 (纯 CSS)

柱状堆积图——每天两根柱子并排 (P50 / P95):

```
 延迟 (ms)
 800 │  ██
 600 │  ██ ██
 400 │  ██ ██ ██
 200 │  ██ ██ ██ ██
     └─────────────────
       6/23 6/24 6/25 6/26
       ▓ = P50  ▒ = P95
```

颜色: P50 用浅蓝, P95 用深蓝。

#### 4.9.4 ErrorPieChart.vue — 错误分布饼图 (纯 CSS)

用 CSS `conic-gradient()` 绘制饼图:

```css
.error-pie {
  width: 120px; height: 120px;
  border-radius: 50%;
  background: conic-gradient(
    var(--color-danger) 0% 40%,
    var(--color-accent) 40% 75%,
    var(--color-text-muted) 75% 90%,
    var(--color-border) 90% 100%
  );
}
```

右侧用图例列表标注错误类型。

---

### 4.10 SSEMonitor.vue — 实时编排监控

**Props**:

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `active` | `boolean` | `false` | 是否正在监听 |
| `events` | `SSEEvent[]` | `[]` | 事件列表 |
| `maxEvents` | `number` | `50` | 最大保留事件数 |

**SSEEvent 数据类型**:

```typescript
type SSEEventType = 'plan' | 'worker_start' | 'worker_done' | 'synthesis' | 'error'

interface SSEEvent {
  id: string
  type: SSEEventType
  data: Record<string, any>
  timestamp: number
  status: 'pending' | 'running' | 'done' | 'failed'  // 仅 worker_start 使用
}
```

**UI 渲染**:

```
┌─── SSE Monitor ─────────────────────┐
│ ● 已连接    (3 个 worker 运行中)      │
│                                      │
│ [09:15:23] ◉ plan: 分析意图...       │
│   └─ 意图: travel_planning          │
│   └─ 子任务: searcher, profiler      │
│                                      │
│ [09:15:24] ◎ searcher: 搜索热门景点  │
│              ◌ 旋转动画...           │
│                                      │
│ [09:15:25] ● searcher: ✓ 345ms      │  ← 绿色
│                                      │
│ [09:15:28] ◉ synthesis: 生成回复...  │
│                                      │
│ [09:15:30] ✓ 编排完成 (2.1s)        │  ← 绿色
└──────────────────────────────────────┘
```

**事件状态指示**:

| 事件 | 前缀 | 颜色 | 动画 |
|------|------|------|------|
| plan | `◉` | 灰色 | 无 |
| worker_start | `◎` | 蓝色 | CSS 旋转动画 |
| worker_done (成功) | `●` | 绿色 | 无 |
| worker_done (失败) | `●` | 红色 | 无 |
| synthesis | `◉` | 绿色 | 无 |
| error | `✕` | 红色 | 无 |

---

## 5. 数据流图

```
┌──────────────────────────────────────────────────────────────┐
│                        前端 UI                                 │
├──────────────────────────────────────────────────────────────┤
│  useObserve composable (状态 + 业务逻辑)                       │
│  ┌────────────────────────────────────────────────────┐      │
│  │  state:                                             │      │
│  │  - orchestrations: OrchestrationSummary[]           │      │
│  │  - selectedOrchestrationId: string | null           │      │
│  │  - currentTraceSpans: AgentTraceSpan[]              │      │
│  │  - metrics: AgentMetrics[]                          │      │
│  │  - filter: ObserveFilter                            │      │
│  │  - loading / error                                  │      │
│  │                                                     │      │
│  │  actions:                                           │      │
│  │  - fetchList(filter) ────┐                          │      │
│  │  - fetchTrace(id) ───────┤                          │      │
│  │  - fetchMetrics(days) ───┤                          │      │
│  │  - onSSEEvent() ←────────┼── useSSE                 │      │
│  └──────────────────────────┼────────────────────────┘      │
│                             │                                │
├─────────────────────────────┼────────────────────────────────┤
│                    请求/响应 │                                │
└─────────────────────────────┼────────────────────────────────┘
                              │
               ┌──────────────┼──────────────┐
               ▼              ▼              ▼
        GET /traces    GET /traces/{id}   GET /metrics
               │              │              │
               ▼              ▼              ▼
┌──────────────────────────────────────────────────────────────┐
│                        后端 API                                │
├──────────────────────────────────────────────────────────────┤
│  agent.py 新增路由:                                           │
│  - GET /traces → 从 AgentTrace 表查询列表 (按时间降序)         │
│  - GET /traces/{id} → 查询同 orchestration_id 的所有 span      │
│  - GET /metrics → 从 AgentMetrics 表聚合查询                    │
│                                                              │
│  数据库:                                                      │
│  - agent_traces (AgentTrace 模型)                             │
│  - agent_metrics (AgentMetrics 模型)                          │
│  - 双写策略: SQLite (结构化) + Markdown (可读)                 │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                        SSE 流                                 │
│                                                              │
│  POST /agent/orchestrate  (增强版)                             │
│  → 在编排过程中主动推送 SSE 事件到 EventSource                │
│                                                              │
│  事件流:                                                     │
│  event: plan          {intent, subtasks}                     │
│  event: worker_start  {worker, objective}                    │
│  event: worker_done   {worker, elapsed_ms, success, summary} │
│  event: synthesis     {reply}                                │
└──────────────────────────────────────────────────────────────┘
```

---

## 6. 状态管理设计

### 6.1 决策: 新增 `useObserve` composable

不扩展现有的 `useAgent.ts`，而是新建独立的 `useObserve.ts`。理由:

1. `useAgent.ts` 职责是对话、评估、计划调度等核心交互逻辑，已较重
2. Observe 面板的数据是**查询型**（读取 traces / metrics），与对话的**写入型**不同
3. Observe 面板在 agent sidebar 内部，不需要全局分享到其他页面

### 6.2 useObserve 接口设计

```typescript
// composables/useObserve.ts

export interface ObserveFilter {
  agent_name?: string
  date?: string
  success?: boolean
  limit: number
}

export function useObserve() {
  const orchestrations = ref<OrchestrationSummary[]>([])
  const currentTraceSpans = ref<AgentTraceSpan[]>([])
  const metrics = ref<AgentMetrics[]>([])
  const filter = ref<ObserveFilter>({ limit: 20 })
  const selectedOrchestrationId = ref<string | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const autoRefresh = ref(true)

  // 计算属性
  const selectedOrchestration = computed(() =>
    orchestrations.value.find(o => o.orchestration_id === selectedOrchestrationId.value) ?? null
  )

  // 方法
  async function fetchList() { /* 调用 getTraces(filter.value) */ }
  async function selectOrchestration(id: string) { /* 调用 getTraceDetail(id) */ }
  async function fetchMetrics(days?: number, agentName?: string) { /* 调用 getMetrics(...) */ }
  function updateFilter(partial: Partial<ObserveFilter>) { /* 合并 filter + 重新 fetchList */ }
  function refresh() { /* fetchList + 如有选中则 selectOrchestration + fetchMetrics */ }
  function toggleAutoRefresh() { /* 启动/停止 3 秒轮询 */ }

  onUnmounted(() => stopAutoRefresh())

  return {
    orchestrations: readonly(orchestrations),
    currentTraceSpans: readonly(currentTraceSpans),
    metrics: readonly(metrics),
    filter: readonly(filter),
    selectedOrchestrationId: readonly(selectedOrchestrationId),
    selectedOrchestration,
    loading: readonly(loading),
    error: readonly(error),
    autoRefresh: readonly(autoRefresh),
    fetchList, selectOrchestration, fetchMetrics, updateFilter, refresh, toggleAutoRefresh,
  }
}
```

### 6.3 SSE 状态管理

```typescript
// composables/useSSE.ts

export function useSSE() {
  const connected = ref(false)
  const events = ref<SSEEvent[]>([])
  const maxEvents = 50

  function connect() {
    // new EventSource → 监听 plan/worker_start/worker_done/synthesis 事件
    // worker_done 事件对应更新 worker_start 的 status
    // 断开时自动重连 (指数退避: 1s→2s→4s→8s→max 30s)
  }

  function disconnect() { /* eventSource.close() */ }

  onUnmounted(() => disconnect())

  return { connected, events: readonly(events), connect, disconnect }
}
```

### 6.4 API 客户端扩展

```typescript
// api/agent.ts 新增

export function getTraces(params: {
  limit?: number
  agent_name?: string
  date?: string
  success?: boolean
}): Promise<OrchestrationSummary[]> {
  const query = new URLSearchParams()
  if (params.limit) query.set('limit', String(params.limit))
  if (params.agent_name) query.set('agent_name', params.agent_name)
  if (params.date) query.set('date', params.date)
  if (params.success !== undefined) query.set('success', String(params.success))
  return get(`/agent/traces?${query.toString()}`)
}

export function getTraceDetail(orchestrationId: string): Promise<AgentTraceSpan[]> {
  return get(`/agent/traces/${orchestrationId}`)
}

export function getMetrics(params: {
  days?: number
  agent_name?: string
}): Promise<AgentMetrics[]> {
  const query = new URLSearchParams()
  if (params.days) query.set('days', String(params.days))
  if (params.agent_name) query.set('agent_name', params.agent_name)
  return get(`/agent/metrics?${query.toString()}`)
}
```

### 6.5 状态分布总结

| 状态 | 位置 | 原因 |
|------|------|------|
| 编排列表数据 | `useObserve.orchestrations` | 跨组件共享 (列表 + 右侧详情) |
| 筛选条件 | `useObserve.filter` | 列表和详情需要共用筛选上下文 |
| 选中编排 ID | `useObserve.selectedOrchestrationId` | 列表和详情需要同步 |
| 当前 Trace 详情 | `useObserve.currentTraceSpans` | 瀑布图组件消费 |
| 指标数据 | `useObserve.metrics` | 指标面板消费 |
| SSE 事件 | `useSSE.events` | 独立 composable，仅 SSE 监控面板使用 |
| UI 内部状态 (hover, tab) | 组件局部 state | 不跨组件共享，无需提升 |
| 面板显隐 | 组件局部 state | 由 `AgentPanel.activeTab` 决定 |

---

## 7. 边界状态处理

### 7.1 OrchestrationList

| 状态 | UI 表现 |
|------|---------|
| **Empty** | 居中显示空状态 + 说明文字 "暂无编排记录" + 触发提示 |
| **Loading** | 5 行骨架屏，每行 3 个不同宽度的灰色块脉冲动画 |
| **Error** | 错误提示 + "重试" 按钮，保留原有数据不清空 |
| **Filter empty** | "没有匹配的编排" + "清除筛选" 按钮 |

### 7.2 TraceWaterfall

| 状态 | UI 表现 |
|------|---------|
| **Empty** | "无法加载 Trace 数据"，显示编排 ID |
| **Loading** | 6 行水平骨架条，每行随机宽度模拟瀑布图 |
| **Error** | 错误消息 + 重试按钮 |
| **100+ spans** | 瀑布图可滚动；默认只展开前 20 条，底部 "展开剩余 N 条" |
| **Single span** | 只有一个 plan span 的简单展示 |
| **All failed** | 所有 bar 红色半透明，每条 bar 左侧 ! 图标 |
| **Zero latency** | 最小宽度 4px 细条，hover 显示 "0ms" |
| **Orch running** | SSE 事件实时追加 span，动画淡入 |

### 7.3 MetricsDashboard

| 状态 | UI 表现 |
|------|---------|
| **Empty** | "暂无指标数据，编排后将自动生成" |
| **Loading** | 汇总数字区 4 个骨架圆形，图表区骨架柱 |
| **Error** | 错误消息 + 重试按钮 |
| **Zero error** | 饼图显示 100% 一个色块，图例 "无错误" |

### 7.4 SSEMonitor

| 状态 | UI 表现 |
|------|---------|
| **Disconnected** | 顶部红色条 "SSE 已断开，自动重连中..." + 脉冲动画 |
| **No events** | "等待编排事件..." + 呼吸灯动画 |
| **Long running** | worker_start 超 10 秒显示黄色 "执行中 (10s+)" |
| **Timeout (60s)** | 自动标记为 failed，红色 "超时" |
| **Buffer overflow** | 超过 50 条自动移除最早事件 |

### 7.5 AgentTopology

| 状态 | UI 表现 |
|------|---------|
| **Empty** | "Worker 尚未注册" |
| **All idle** | 所有节点灰色半透明 + "所有 worker 处于空闲状态" |
| **No stats** | "暂无统计数据" |

---

## 8. 交互设计

### 8.1 核心交互流程

```
用户打开 Observe Tab
  │
  ├─→ fetchList() 加载最近 20 条编排
  │     ├─ 成功 → 渲染列表 (时间降序)
  │     └─ 失败 → 显示错误态 + 重试按钮
  │
  ├─→ 用户点击某条编排
  │     ├─ 高亮选中条目
  │     ├─ selectOrchestration(id) → 加载 Trace 详情
  │     └─ 右侧详情区默认展示瀑布图
  │
  ├─→ 用户 hover span bar → SpanTooltip 浮层 (跟随鼠标)
  │
  ├─→ 用户点击 span bar → SpanDetailDrawer 从底部滑入
  │     ├─ 显示完整 input / output / error
  │     └─ 点击背景或 ✕ 关闭
  │
  ├─→ 用户切换详情 tab (瀑布图 / 拓扑图 / 指标)
  │
  └─→ 实时编排发生时 → SSE 推送到 SSEMonitor
```

### 8.2 筛选交互

| 操作 | 行为 |
|------|------|
| 选择 agent_name 下拉 | 立即触发 `updateFilter`，重新加载列表 |
| 选择日期 | 同上 |
| 点击成功/失败按钮 | 切换 `filter.success`，"全部" 取消选中 |
| 点击预设时间 (今天/7天/30天) | 设置日期范围 |
| 切换自动刷新开关 | 启动/停止 3 秒轮询 |

### 8.3 瀑布图 Hover 交互

- 鼠标移入 span bar → 浮层显示在鼠标位置上方
- 浮层内容: `[span_type] agent_name — latency_ms — objective[:60]`
- 浮层跟随鼠标移动
- 鼠标移出 → 浮层延迟 100ms 消失

### 8.4 瀑布图 Click 交互

- 点击 span bar → 抽屉从右侧滑入 (80% 宽度)
- 抽屉内容: 基本信息表 + Objective + Input + Output + Error(可选)
- 点击抽屉外背景或 ✕ → 抽屉滑出
- 动画: CSS `transform: translateX` + `transition: 0.2s ease`

### 8.5 拓扑图 Click 交互

- 点击 worker 节点 → 节点放大 + 高亮，其他节点淡化
- 底部出现 stats 面板 (slide-up 动画)
- 再次点击或点击空白 → 收起

### 8.6 SSE Monitor 交互

- 纯展示，无用户交互
- 自动滚动到底部 (用户向上滚动时暂停)
- 用户手动滚到底部 → 恢复自动滚动

---

## 9. 实施步骤

### Phase 1: 后端基础设施

1. 实现 `AgentTrace` 模型 + 结构化 Trace 写入 (双写策略)
2. 实现 `AgentMetrics` 模型 + 每日聚合
3. 实现 `GET /api/v1/agent/traces` 和 `GET /api/v1/agent/traces/{id}`
4. 实现 `GET /api/v1/agent/metrics`
5. 增强 SSE 流，增加 `worker_start` / `worker_done` 事件

### Phase 2: 前端 — Observe Tab 基础

1. 创建 `useObserve.ts` composable
2. 创建 `useSSE.ts` composable
3. 在 `api/agent.ts` 新增 traces / metrics 接口
4. 在 `AgentPanel.vue` 新增第 5 个 tab "观察"
5. 创建 `ObservePanel.vue` (左右分栏骨架)
6. 创建 `ObserveFilterBar.vue`
7. 创建 `OrchestrationList.vue` + `OrchestrationItem.vue`

### Phase 3: 瀑布图

1. 创建 `TraceWaterfall.vue` (核心组件)
2. 实现时间轴标尺
3. 实现 span bar 渲染 + 颜色映射
4. 实现并行 worker 分组算法
5. 创建 `SpanTooltip.vue` (hover 浮层)
6. 创建 `SpanDetailDrawer.vue` (点击展开抽屉)
7. 处理长编排 (100+ spans) 的折叠

### Phase 4: 拓扑图 + 指标

1. 创建 `AgentTopology.vue` + `TopologyNode.vue`
2. 实现 CSS Flex 布局拓扑
3. 实现点击 worker 展开 stats 面板
4. 创建 `MetricsDashboard.vue` + 4 个子组件
5. 创建 `MetricsStickyBar.vue`

### Phase 5: SSE 实时监控

1. 创建 `SSEMonitor.vue` + `SSEEventItem.vue`
2. 实现 `useSSE` 的连接/重连/断开
3. 实现事件状态动画
4. 实现自动滚动逻辑

---

## 附录 A: 扩展 AgentPanel.vue 变更点

`AgentPanel.vue` 的 `activeTab` 类型需扩展:

```typescript
const activeTab = ref<'chat' | 'tasks' | 'log' | 'kb' | 'observe'>('chat')
```

Tab 按钮新增:

```html
<button class="tab-btn" :class="{ active: activeTab === 'observe' }" @click="activeTab = 'observe'">
  观察
</button>
```

---

## 附录 B: 类型定义汇总

```typescript
// types/agent-observe.ts

export interface ObserveFilter {
  agent_name?: string
  date?: string
  success?: boolean
  limit: number
}

export interface OrchestrationSummary {
  orchestration_id: string
  intent: string
  workers_used: string[]
  total_latency_ms: number
  success: boolean
  created_at: string
  reply_preview: string
}

export interface AgentTraceSpan {
  id: string
  orchestration_id: string
  span_type: 'plan' | 'worker_dispatch' | 'worker_execute' | 'synthesis' | 'safety_check' | 'persist'
  agent_name: string
  parent_span_id: string | null
  objective: string
  input_summary: string
  output_summary: string
  latency_ms: number
  token_estimate: number | null
  success: boolean
  error_message: string | null
  metadata_json: string | null
  created_at: string
}

export interface AgentMetrics {
  date: string
  agent_name: string
  total_calls: number
  success_count: number
  error_count: number
  avg_latency_ms: number
  p50_latency_ms: number
  p95_latency_ms: number
  total_token_estimate: number
}

export interface WorkerNode {
  name: string
  label: string
  status: 'active' | 'idle' | 'inactive'
  total_calls: number
  success_rate: number
  avg_latency_ms: number
  last_called_at: string | null
  color: string
}

export interface RouterEdge {
  from: string
  to: string
  frequency: number
  recent_count: number
}

export interface SSEEvent {
  id: string
  type: 'plan' | 'worker_start' | 'worker_done' | 'synthesis' | 'error'
  data: Record<string, any>
  timestamp: number
  status: 'pending' | 'running' | 'done' | 'failed'
}
```

---

## 附录 C: CSS 变量扩展

```css
:root {
  /* Waterfall color palette */
  --waterfall-plan:       #9E9E9E;
  --waterfall-dispatch:   #90CAF9;
  --waterfall-execute:    #42A5F5;
  --waterfall-synthesis:  #66BB6A;
  --waterfall-safety:     #EF5350;
  --waterfall-safety-pass:#66BB6A;
  --waterfall-persist:    #AB47BC;
}
```
