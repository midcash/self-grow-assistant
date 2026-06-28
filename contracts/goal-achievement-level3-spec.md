# Goal Achievement Level3 升级规格

> 成熟度: 草稿
> 决策日期: 2026-06-25
> 范围: 规格文档。本文不代表功能已经实现。

## 0. 结论

本次升级把项目叙事从:

```text
AI 日程规划助手
```

升级为:

```text
Agentic Goal Achievement System

Plan -> Execute -> Track -> Reflect -> Replan -> Evaluate
```

核心目标不是继续证明“能生成计划”，而是证明系统具备长期目标 Agent 能力: 规划、执行跟踪、记忆、反思、动态重规划、工具调用治理和评估。

## 1. 这个功能要解决什么问题

当前系统已经具备多 Agent 编排、目标分解、优先级评估、MCP 检索和记忆雏形，但主链路仍偏向:

```text
用户提出目标
-> Agent 分解目标
-> 写入 Todo / GoalTask
-> 定时提醒
```

这能证明项目不是普通聊天机器人，但还不能充分证明“长期任务闭环”。

现有短板:

- 计划生成后，缺少结构化复盘。
- 用户连续失败后，没有明确的自适应重规划协议。
- 记忆主要是摘要和历史记录，不能稳定检索长期行为模式。
- 工具调用边界不够显式，难以展示 Tool-driven Agent 能力。
- 缺少 Evaluation，无法证明 Agent 的计划质量和干预有效性。
- Web Search 与 Safety 尚未形成可控的工具治理规格。

升级后的目标场景:

```text
用户: 我要 30 天学会 LangGraph

Agent:
1. 创建长期目标
2. 分解阶段任务和每日任务
3. 跟踪每日执行情况
4. 发现连续偏离
5. 反思失败原因
6. 自动生成调整方案
7. 必要时调用搜索、日程、提醒等工具
8. 记录评估结果，形成可复盘证据
```

## 2. 当前系统原状

### 2.1 Worker 协议

Worker 通信协议定义在 `backend/agent/workers/base.py`:

- `TaskBrief`: Orchestrator 分发给 Worker 的 8 字段输入协议。
- `WorkerResult`: Worker 返回给 Orchestrator 的 6 字段输出协议。
- `execute_with_retry()`: 已提供超时和重试包装。

约束:

- Level3 第一阶段不得破坏 `TaskBrief` 和 `WorkerResult`。
- 若后续确实需要修改协议，必须先更新 `contracts/agent-plugin-spec.md`，再修改 `base.py`，最后更新所有 Worker 和协议测试。

### 2.2 多 Agent 编排

当前 `backend/agent/orchestrator.py` 已注册:

```text
searcher
profiler
executor
goal_decomposer
coach
```

`Orchestrator.handle()` 已具备:

- LLM 规划。
- Worker 分派。
- 并行与依赖任务执行。
- 结果综合。
- 记忆写入。
- 编排日志。

已知限制:

- `_plan()` 明确写有“当前不联网搜索，searcher 只能查本地数据库和 LLM 知识”。
- 规划结果是单次请求计划，不是长期循环状态机。
- Worker 调用由 Orchestrator 路由，但缺少统一 Tool Registry 与工具调用审计。

### 2.3 长期目标模型

当前 `backend/models.py` 已有:

```text
Goal
GoalTask
```

当前 `backend/agent/motivation_engine.py` 已有:

- `MotivationEngine.tick()`
- `_calc_pressure()`
- `_escalate_goal_tasks()`

已知限制:

- 压力公式较粗。
- 提醒升级不等于重新规划。
- GoalTask 与 TodoItem 的同步关系不够完整。
- 缺少“为什么失败”“怎么调整”的反思记录。

### 2.4 记忆系统

当前已有:

```text
AgentConversation
AgentMemoryDigest
data/agent-memory/digest
data/agent-memory/plan-logs
```

已知限制:

- 可以保存摘要，但不支持语义相似度检索。
- 不能稳定回答“用户过去在哪类目标上容易失败”。
- Reflection 结果没有沉淀为可复用经验。

### 2.5 MCP / RAG

Searcher 已有 MCP 外部知识库查询能力:

- `_needs_mcp()`
- `_search_mcp()`
- `query_knowledge_hub`

已知限制:

- 这更接近外部知识库检索，不等于通用 Web Search。
- 工具列表由 Searcher 内部管理，Orchestrator 侧还没有统一 MCP Client / Tool Registry。

## 3. 架构决策

### 3.1 决策

采用“增量式 Goal Achievement Loop”，不重写现有 Agent 框架。

升级方式:

```text
现有 Orchestrator / Worker / Plugin 架构
        +
Goal Achievement Loop
        +
Tool Registry
        +
Reflection / Evaluation / Replanning
        +
Semantic Memory
```

### 3.2 考虑过的选项

选项 A: 引入 LangGraph 重写。

优点:

- 天然支持状态图和循环。
- 面试时容易解释。

缺点:

- 与当前自研 Harness、Worker、Plugin 体系重叠。
- 改动范围大。
- 项目叙事容易变成“用了框架”，而不是“实现了 Agent 系统”。

结论: 不采用。

选项 B: 保持现有架构，只加更多 Worker。

优点:

- 改动小。

缺点:

- 容易继续堆 Agent 名称，不能解决闭环问题。
- Evaluation、Safety、Tool Audit 没有统一落点。

结论: 不作为主方案。

选项 C: 在现有架构上新增 Goal Achievement Loop。

优点:

- 复用当前 Orchestrator、Worker、Goal、MotivationEngine。
- 可分阶段落地。
- 能清楚展示长期任务 Agent 的工程能力。

缺点:

- 需要新增循环状态、评估记录和工具治理。
- API 与前端面板需要扩展。

结论: 采用。

### 3.3 后果

被简化:

- 不需要替换现有 Agent 框架。
- 不需要大规模迁移前端。
- Worker 协议在第一阶段保持稳定。

被复杂化:

- 需要新增目标循环状态。
- 需要维护工具调用审计。
- 需要新增 Reflection / Evaluation 数据。
- 需要定义 Safety Gate，防止 Agent 自动执行高风险操作。

## 4. 能力规格

### 4.1 Function Calling / Tool-driven Agent

需求:

让 Agent 不只是“生成文本”，而是能通过受控工具完成动作。

第一批工具:

```text
create_goal
update_goal_progress
create_todo
update_todo
search_memory
search_knowledge
generate_reflection
propose_replan
```

后续工具:

```text
web_search
calendar_write
send_notification
```

协议原则:

- 工具必须注册到 Tool Registry。
- 每次工具调用必须保存审计记录。
- 写操作必须返回结构化结果。
- 高风险工具必须经过 Safety Gate。
- Worker 协议暂不改，工具调用作为 Worker 内部能力或 Orchestrator 辅助能力接入。

建议新增数据模型:

```text
AgentToolCall
- id
- request_id
- tool_name
- input_json
- output_json
- status
- error_message
- risk_level
- created_at
```

### 4.2 Semantic Memory

需求:

让系统能够检索用户长期行为模式，而不是只读最近摘要。

示例问题:

```text
用户最近在哪类任务上拖延最多？
用户过去失败的目标有什么共同点？
用户完成率高的计划通常有什么特征？
```

第一阶段实现:

不强制引入外部向量数据库，优先采用本地 SQLite + 简化 embedding 存储。

建议新增数据模型:

```text
AgentSemanticMemory
- id
- source_type: conversation / reflection / goal / todo / digest
- source_id
- content
- embedding_json
- tags
- created_at
```

检索策略:

```text
先关键词过滤
再 embedding 相似度排序
最后交给 Profiler / Reflection 使用
```

成功标准:

- 能按目标、任务、情绪、失败原因检索历史片段。
- Reflection Agent 能引用过去相似案例。
- 不破坏现有 `AgentMemoryDigest`。

### 4.3 Reflection Agent

需求:

系统每天或每个目标周期生成结构化反思:

```text
计划完成率
执行偏差
失败原因
拖延模式
下次调整建议
```

建议新增 Worker:

```text
reflection
```

职责:

- 读取 Goal、GoalTask、TodoItem、AgentSemanticMemory。
- 计算目标执行情况。
- 识别偏差原因。
- 输出可被 Replanning 使用的结构化建议。

建议新增数据模型:

```text
AgentReflection
- id
- goal_id
- date
- completion_rate
- skipped_count
- overdue_count
- deviation_reason
- pattern_summary
- suggested_adjustment
- created_at
```

成功标准:

- 至少能生成日级反思。
- 连续 3 天未达标时能明确指出偏差。
- 反思结果能进入 Semantic Memory。

### 4.4 Adaptive Replanning

需求:

当用户持续失败时，系统不只是提醒，而是调整计划。

示例:

```text
原计划: 每天学习 2 小时
连续 3 天失败
系统建议: 每天 30 分钟 + 周末补 90 分钟
```

建议新增 Worker:

```text
replanner
```

职责:

- 输入 Reflection 结果。
- 生成新计划候选。
- 说明调整理由。
- 标记需要用户确认的改动。

规则:

- 降低任务强度属于中风险，必须提示用户确认。
- 删除目标、删除历史任务、批量改动未来 7 天以上计划属于高风险，必须禁止自动执行。
- 未确认前只创建 replan proposal，不直接覆盖用户计划。

建议新增数据模型:

```text
AgentReplanProposal
- id
- goal_id
- reflection_id
- reason
- proposed_changes_json
- status: pending / accepted / rejected / expired
- created_at
- decided_at
```

### 4.5 Evaluation

需求:

让项目能证明 Agent 是否真的有效。

评估维度:

```text
计划质量
工具调用正确率
任务完成率提升
重规划采纳率
提醒有效率
幻觉 / 错误率
```

建议新增数据模型:

```text
AgentEvaluationRun
- id
- eval_name
- passed
- score
- metrics_json
- failure_reason
- created_at
```

成功标准:

- 至少 5 个离线 eval case。
- 每个 case 能断言“是否需要反思”“是否需要重规划”“是否允许自动执行工具”。
- pytest 中覆盖核心规则。

### 4.6 Web Search

需求:

让 Searcher 支持真实外部信息查询，适用于学习路线、岗位要求、技术资料更新等场景。

第一阶段只定义接口，不直接绑定供应商:

```text
WebSearchTool.search(query, freshness, max_results)
```

约束:

- 搜索结果必须带来源 URL。
- 涉及医疗、法律、金融等高风险内容时，只允许总结，不给确定性建议。
- Web Search 默认只读，不允许写外部系统。
- 若联网能力不可用，必须降级为本地知识库，并明确说明“未联网”。

### 4.7 Safety

需求:

保证 Agent 执行工具时不会越权或破坏用户数据。

风险等级:

```text
low:
  读取本地任务、读取目标、搜索记忆、生成反思

medium:
  创建 Todo、更新目标进度、创建重规划候选

high:
  删除数据、批量修改未来计划、写外部日历、发送外部消息
```

规则:

- low 可自动执行。
- medium 可在当前会话内执行，但必须记录 ToolCall。
- high 必须用户确认，第一阶段默认不自动执行。
- Safety 拒绝结果必须写入 ToolCall 审计。

## 5. 接口 / 协议影响面分析

### 5.1 Worker 协议

第一阶段不修改:

```text
TaskBrief
WorkerResult
```

新增 Worker 只实现现有协议:

```text
reflection
replanner
```

如果后续需要让 `WorkerResult` 原生携带工具调用链，再单独升级 `contracts/agent-plugin-spec.md`。

### 5.2 LLM Adapter 协议

当前 `LLMAdapterBase` 只有:

```text
chat
chat_stream
evaluate_urgency
```

Function Calling 有两种实现路径。

路径 A: Harness 侧解析工具调用。

LLM 仍返回 JSON 文本，由 Orchestrator / Worker 解析并调用 Tool Registry。

优点:

- 不改 `LLMAdapterBase`。
- 兼容 DeepSeek / Qwen 当前实现。

缺点:

- 工具调用不够原生。

路径 B: 扩展 `LLMAdapterBase`。

新增:

```text
chat_with_tools(messages, tools, tool_choice) -> ToolCallingResponse
```

优点:

- 更符合 Function Calling 叙事。

缺点:

- 会修改插件协议。
- 需要更新所有 LLM Adapter 和协议测试。

决策:

- 第一阶段采用路径 A，先完成工具治理和闭环。
- 第二阶段再评估是否升级 `LLMAdapterBase`。

### 5.3 API 影响

建议新增端点，暂不删除现有端点:

```text
# Phase 0: Observability + Safety
GET  /api/v1/agent/traces?orchestration_id=&agent_name=&date=&limit=
GET  /api/v1/agent/traces/{orchestration_id}        ← 完整 Trace 树
GET  /api/v1/agent/metrics?days=7&agent_name=       ← Agent 指标聚合

# Phase 1-3: Goal Loop / Reflection / Replan
GET  /api/v1/agent/goals/{goal_id}/loop
POST /api/v1/agent/goals/{goal_id}/reflect
POST /api/v1/agent/goals/{goal_id}/replan
POST /api/v1/agent/replans/{proposal_id}/accept
POST /api/v1/agent/replans/{proposal_id}/reject

# Phase 1: ToolCall
GET  /api/v1/agent/tool-calls

# Phase 5: Evaluation
POST /api/v1/agent/evaluations/run
GET  /api/v1/agent/evaluations
```

后续实现前，需把最终端点同步到 `contracts/api-spec.md`。

### 5.4 数据库影响

建议新增表:

```text
agent_traces              ← Phase 0: 结构化 Trace
agent_metrics             ← Phase 0: Agent 指标聚合
agent_tool_calls          ← Phase 1
agent_semantic_memories   ← Phase 4
agent_reflections         ← Phase 2
agent_replan_proposals    ← Phase 3
agent_evaluation_runs     ← Phase 5
```

不删除、不迁移:

```text
data/
dist/data/
todo_items
goals
goal_tasks
agent_memory_digests
agent_conversations
```

### 5.5 前端影响

建议在 Agent 面板增加:

```text
Phase 0 (优先):
  Agent Trace 瀑布图
  Agent 拓扑图（Worker 路由关系 + 频率）
  Agent 指标面板（成功率 / 延迟趋势）

Phase 2-5 (后续):
  目标闭环视图
  反思记录
  重规划候选
  工具调用审计
  评估结果
```

第一阶段可以只做后端与测试，前端最小展示可后置。

## 6. 成功标准

### 6.1 功能成功标准

给定一个长期目标:

```text
30 天学习 LangGraph，目标完成 20 小时学习
```

系统必须能:

1. 创建 Goal。
2. 分解 GoalTask 和 Todo。
3. 记录每日执行结果。
4. 计算目标完成率和偏差。
5. 生成 Reflection。
6. 连续失败后生成 ReplanProposal。
7. 用户确认后应用调整。
8. 将反思和调整写入记忆。
9. 保存工具调用审计。

### 6.2 工程成功标准

必须通过:

```bash
venv/Scripts/python -m pytest tests/ -v
cd frontend && npm run build
```

新增测试覆盖:

- Worker 协议不变。
- 结构化 Trace 在编排后正确写入（按 orchestration_id 可查询完整 Trace 树）。
- Reflection 生成规则。
- ReplanProposal 不自动覆盖用户计划。
- Safety Gate 阻止高风险工具自动执行并写入 Trace（span_type=safety_check）。
- ToolCall 审计记录。
- Agent 指标按 Worker 聚合正确（计数、延迟分位数）。
- Evaluation case 能运行并输出分数。

### 6.3 面试展示成功标准

项目可用一句话解释:

```text
我实现了一个面向长期目标管理的 Agentic Workflow 系统，具备规划、执行跟踪、语义记忆、反思、动态重规划、工具调用审计和离线评估能力。
```

演示链路:

```text
创建目标
-> 自动拆解
-> 模拟三天未完成
-> 系统反思原因
-> 生成新计划
-> 用户确认
-> 查看工具调用与评估记录
```

### 4.8 Observability — Agent 协同可观测性

需求:

让多 Agent 协同过程从"黑盒"变为"白盒"。每次编排的完整调用链路、各 Worker 输入输出、延迟分布、错误模式均可追溯和可视化，便于判断架构优劣。

当前局限:

- 编排日志为 Markdown 文件，通过正则解析提取 Worker 信息（`backend/routers/agent.py:130-162`）
- 无结构化 Trace 存储，无法按 Worker / 时间 / 成功率查询
- 无实时编排进度推送，前端只能看到最终回复文本
- 无历史指标聚合，无法回答"哪个 Worker 最慢""重构后性能变化"

#### 4.8.1 结构化 Agent Trace

建议新增数据模型:

```text
AgentTrace
- id
- orchestration_id          ← 一次编排的唯一 ID（UUID）
- span_type: plan | worker_dispatch | worker_execute | synthesis | persist | safety_check
- agent_name: orchestrator | searcher | profiler | executor | goal_decomposer | coach | reflection | replanner
- parent_span_id            ← 构建调用树（NULL = 根 span）
- objective                 ← 任务目标摘要
- input_summary             ← 输入摘要 (user_message 截断 或 TaskBrief.objective)
- output_summary            ← 输出摘要 (WorkerResult.content[:300])
- latency_ms                ← 阶段耗时
- token_estimate            ← token 估算（可选）
- success                   ← 是否成功
- error_message
- metadata_json             ← 额外指标 (confidence, sources, tool_call_ids, risk_level)
- created_at
```

Span 类型说明:

```text
plan:             LLM 意图分析 + 任务分解耗时
worker_dispatch:  Orchestrator → Worker 的路由决策
worker_execute:   Worker.execute() 的执行耗时和结果
synthesis:        Orchestrator._synthesize() 汇总耗时
persist:          记忆写入耗时
safety_check:     SafetyGate 检查结果 (允许/拒绝)
```

一次编排产生的 Trace 树示例:

```text
[orchestration_id: abc-123]
├── plan (orchestrator, 450ms)
├── worker_dispatch → searcher (5ms)
├── worker_execute → searcher (345ms, success)
├── worker_dispatch → profiler (3ms)
├── worker_execute → profiler (456ms, success)
├── synthesis (orchestrator, 230ms)
├── safety_check (5ms, allowed)
└── persist (120ms)
```

#### 4.8.2 实时编排 SSE 流

在现有 `POST /agent/chat/stream` (文本 SSE) 基础上，增强为**编排进度流**——在 LLM 文本流中嵌入 Worker 生命周期事件:

```text
event: plan
data: {"intent": "goal_reflection", "subtasks": [{"id":"searcher","objective":"查询完成率"}, ...]}

event: worker_start
data: {"worker": "searcher", "objective": "查询历史完成率"}

event: worker_done
data: {"worker": "searcher", "elapsed_ms": 345, "success": true, "summary": "完成率 45%"}

event: worker_start
data: {"worker": "profiler", "objective": "分析拖延模式"}

event: worker_done
data: {"worker": "profiler", "elapsed_ms": 456, "success": true, "summary": "连续3天未达标"}

event: synthesis
data: {"reply": "根据分析，你最近..."}
```

约束:

- 与现有 `chat/stream` 兼容（纯 chat 模式只发 text chunk，编排模式增加 worker 事件）
- Worker 事件中的 `summary` 不超过 200 字，避免 SSE 帧过大
- 失败 Worker 的 `error` 字段只包含错误类型码，不含堆栈

#### 4.8.3 Agent 指标聚合

建议新增数据模型:

```text
AgentMetrics (每日聚合快照)
- id
- date
- agent_name
- total_calls
- success_count
- error_count
- avg_latency_ms
- p50_latency_ms
- p95_latency_ms
- total_token_estimate
- updated_at
```

聚合策略:

- 每天凌晨由 scheduler 从 `AgentTrace` 聚合前一天数据
- 或每次编排后实时增量更新当天记录

#### 4.8.4 可观测性前端

在 Agent 面板新增:

- **Trace 瀑布图**: 展示一次编排中各 span 的调用时序、耗时、成败。横向为时间轴，纵向为 span 列表
- **Agent 拓扑图**: 可视化当前 Worker 注册关系（节点 = Worker，边 = 编排路由频率）
- **指标面板**: 各 Worker 7/30 天成功率、P50/P95 延迟趋势图

#### 4.8.5 可观测性成功标准

- 每次编排生成结构化 Trace 记录，可从 API 查询（按 orchestration_id / agent_name / date 筛选）
- 前端可查看最近 N 次编排的调用链路瀑布图
- Agent 指标可按 Worker 聚合查询（日/周）
- Safety Gate 拒绝事件写入 Trace（span_type=safety_check, success=false）
- 不破坏现有 Markdown 日志（双写策略：Trace 入库 + Markdown 文件保留）
- `GET /api/v1/agent/traces` 和 `GET /api/v1/agent/metrics` 可被前端消费

---

## 7. 分阶段实施路线

### Phase 0: Observability + Safety Foundation（新增）

目标:

- 在新增更多 Agent 能力之前，先建立可观测基础设施和安全治理
- 确保后续每个新增 Worker / Tool 自动纳入 Trace 和审计

主要产出:

```text
AgentTrace 模型
AgentMetrics 模型
结构化 Trace 写入（双写 Markdown + SQLite）
编排 SSE 流增强（worker_start / worker_done 事件）
SafetyGate 接入 Trace
Trace API (查询单次编排 Trace 树)
Metrics API (按 Worker / 日期聚合)
Trace 瀑布图前端组件
Agent 拓扑图前端组件
```

### Phase 1: Tool Registry + Safety + Audit

目标:

- 定义统一工具注册与调用入口。
- 记录每次工具调用。
- 建立风险等级。

主要产出:

```text
ToolRegistry
SafetyGate
AgentToolCall
基础工具: create_todo / update_goal_progress / search_memory
```

### Phase 2: Reflection Agent

目标:

- 生成目标执行反思。
- 将反思写入数据库和语义记忆。

主要产出:

```text
ReflectionWorker
AgentReflection
POST /agent/goals/{goal_id}/reflect
```

### Phase 3: Adaptive Replanning

目标:

- 根据 Reflection 生成重规划候选。
- 用户确认后再应用。

主要产出:

```text
ReplannerWorker
AgentReplanProposal
accept / reject API
```

### Phase 4: Semantic Memory

目标:

- 支持历史行为模式检索。
- 支持 Reflection 使用相似历史。

主要产出:

```text
AgentSemanticMemory
embedding 生成与检索
search_memory tool
```

### Phase 5: Evaluation

目标:

- 建立离线评估集。
- 证明 Agent 决策质量。

主要产出:

```text
AgentEvaluationRun
5 个 eval case
pytest 覆盖
```

### Phase 6: Web Search

目标:

- 将真实外部信息查询纳入 Searcher。
- 对搜索结果进行来源标注与风险控制。

主要产出:

```text
WebSearchTool
source citation
联网不可用降级策略
```

## 8. 非目标

本次升级不做:

- 不重写为 LangGraph。
- 不删除现有 Agent Harness。
- 不破坏 `TaskBrief` / `WorkerResult`。
- 不删除或重建 `data/`、`dist/data/`。
- 不自动执行高风险外部操作。
- 不承诺医疗、法律、金融等高风险建议的正确性。

## 9. 后续需要同步的合同

进入实现前，需要依次同步:

1. `contracts/api-spec.md`
   - 补充 Goal Loop、Reflection、Replan、ToolCall、Evaluation 端点。

2. `contracts/agent-plugin-spec.md`
   - 若选择 `chat_with_tools`，补充 LLM Adapter 新协议。
   - 若第一阶段采用 Harness 侧工具解析，则只补 Tool Registry 说明。

3. `contracts/mcp-integration-analysis.md`
   - 若 Web Search 通过 MCP Server 接入，补充工具命名、超时、降级策略。

4. `tests/test_workers.py`
   - 保留协议测试。
   - 增加 Level3 闭环测试。
