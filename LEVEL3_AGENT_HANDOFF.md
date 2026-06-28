# Level3 Agent 开发交接文档

> 目标读者: Claude Code / 后续开发 Agent
> 创建日期: 2026-06-25
> 交接范围: Level3 长期目标达成闭环开发任务
> 关联规格: `contracts/goal-achievement-level3-spec.md`
> 放置说明: 原计划写入 `contracts/level3-agent-handoff.md`，但当前 `contracts/` 目录存在写入 ACL 限制；本文件放在项目根目录，便于 Claude Code 入口读取。

## 0. 使用方式

后续开发时，请先阅读本文，再按 Agent 职责创建对应开发 Agent。

本文不是功能实现代码，而是任务编排合同。任何 Agent 开发前必须遵守项目 SDD 约束:

1. 新功能先看 `contracts/`。
2. 不破坏 `TaskBrief` / `WorkerResult`。
3. 不删除 `data/`、`dist/data/`。
4. 后端、前端、合同文件边界清晰。
5. 完成后必须可验证。

## 1. Level3 总目标

将项目从“AI 日程规划助手”升级为:

```text
Agentic Goal Achievement System
Plan -> Execute -> Track -> Reflect -> Replan -> Evaluate
```

系统需要展示:

- Tool-driven Agent
- Safety Gate
- ToolCall Audit
- Semantic Memory
- Reflection
- Adaptive Replanning
- Evaluation
- 可视化 Goal Loop

## 2. 全局开发边界

所有 Agent 都必须遵守:

- 禁止删除 `data/`。
- 禁止删除 `dist/data/`。
- 禁止删除 `data/agent-memory/plan-logs/`（存量 Markdown 日志保留，双写策略）。
- 禁止重写为 LangGraph。
- 禁止破坏 `backend/agent/workers/base.py` 中的 `TaskBrief` / `WorkerResult`。
- 禁止前端 Agent 修改 `backend/`。
- 禁止后端 Agent 修改 `frontend/`。
- 禁止跳过合同直接实现新增 API。
- 禁止高风险工具自动执行。
- **新增约束**: Orchestrator 集成只由 Observability Agent 执行，其他 Agent 不得直接修改 `orchestrator.py`。

Level3 第一阶段必须保持:

```text
TaskBrief: 8 字段
WorkerResult: 6 字段
```

新增 Worker 只能实现现有协议。

若必须修改协议，必须另开合同任务:

```text
先改 contracts/agent-plugin-spec.md
再改 backend/agent/workers/base.py
最后改全部 Worker 和 tests/test_workers.py
```

## 2.3 Level3 关键定义默认值

进入实现前，Contract Agent 必须将以下默认值同步到合同；在合同未细化前，开发 Agent 按本节默认值实现 MVP。

### Goal Loop 状态机默认阈值

```text
healthy: 最近 3 天完成率 >= 70%，且无 pending replan

drifting: 最近 2 天完成率 < 50%，或 skipped_count >= 2

needs_reflection: drifting 成立，且最近 24 小时没有 AgentReflection

needs_replan: 最近一次 reflection 后仍连续 2 天 drifting，或 completion_rate < 30%

waiting_confirmation: 存在 status=pending 的 AgentReplanProposal
```

### Goal progress 默认计算公式

```text
current_progress = done_goal_tasks / total_goal_tasks * target_metric_numeric
```

如果 `GoalTask` 不足以计算，则退化为同目标相关 Todo 的完成率。`target_metric` 中提取第一个数字作为目标值；没有数字时按 1 处理。

### SemanticMemory MVP 策略

MVP 阶段 `embedding_json` 允许为空。`search_memory` 只做 keyword/tag 检索。embedding 相似度属于增强项，不能阻塞 R4 / T6。

### Replan apply 风险矩阵

```text
low: 调整单条 Todo 的 duration_minutes、date，或创建 1 条 Todo
medium: 一次修改 2-7 天内的多个 Todo，需要用户确认后执行
high: 删除 Goal、删除历史 Todo、批量修改未来 7 天以上计划、写外部系统，默认拒绝
```

### 工具范围默认裁剪

MVP 必做工具:

```text
create_todo
update_goal_progress
search_memory
```

MVP 后置或占位工具:

```text
create_goal: 复用现有 Goal API，ToolRegistry 可先占位
update_todo: Phase 3 后实现
search_knowledge: 封装现有 Searcher/MCP 能力，Phase 3 后实现
generate_reflection: Reflection service 等价实现
propose_replan: Replanner service 等价实现
```

### Reflection 触发时机

MVP 只实现手动 API 触发。scheduler / Orchestrator 自动触发属于增强项。

### orchestrator.py 修改权

Reflection/Replanner Agent 只提供 Worker 实现。`backend/agent/orchestrator.py` 的注册由 Team Lead / Architect Agent 在增强阶段统一修改，避免多 Agent 写入冲突。
## 3. 建议创建的 Agent

建议创建 13 类 Agent（含 1 个总控 Agent + 12 个执行 Agent）:

```text
0. Team Lead / Architect Agent
1. Contract Agent
2. Backend Data Agent
3. Backend Tooling Agent
4. Backend Observability Agent      ← 新增: 结构化 Trace + Metrics + SSE
5. Backend Goal Loop Agent
6. Reflection Agent
7. Replanner Agent
8. Backend API Integration Agent
9. Evaluation Agent
10. Frontend Agent
11. Frontend Observability Agent    ← 新增: Trace 瀑布图 + 拓扑图 + 指标面板
12. QA / Integration Agent
```

推荐分批:

```text
第〇批 (Foundation): Contract Agent (可观测性+安全合同), Backend Data Agent,
                    Backend Observability Agent, Backend Tooling Agent
第一批: Goal Loop Agent, Reflection Agent, Replanner Agent
第二批: Backend API Integration Agent, Evaluation Agent,
       Frontend Agent, Frontend Observability Agent, QA Agent
```

每个 Agent 应只读取与自己职责相关的文件，避免上下文过载。

## 4.0 Team Lead / Architect Agent

### 职责

总控 Agent，负责拆解、排期、边界判断和最终验收。原则上不直接写业务代码。

### 文件边界

可读:

```text
contracts/
backend/agent/
backend/models.py
backend/routers/agent.py
frontend/src/api/agent.ts
tests/
```

可写:

```text
contracts/
PROGRESS.md
```

### 输入

- `contracts/goal-achievement-level3-spec.md`
- 本交接文档
- 各 Agent 完成报告

### 输出

- 分批任务计划
- 接口冻结说明
- 验收清单
- 是否允许进入下一阶段的判断

### 任务

| ID | 任务 | 输入 | 输出 | 验证 |
|---|---|---|---|---|
| A0-1 | 确认 Level3 开发顺序 | 本文、Level3 spec | 阶段执行顺序 | 每阶段依赖关系清楚 |
| A0-2 | 检查是否破坏 Worker 协议 | 后端变更 | 协议检查结论 | `tests/test_workers.py` 协议测试通过 |
| A0-3 | 最终合并验收 | 全部 Agent 输出 | 可提交结论 | pytest + frontend build 通过 |

## 4.1 Contract Agent

### 职责

只负责规格、API 合同、插件合同和安全规则。

### 文件边界

可写:

```text
contracts/api-spec.md
contracts/agent-plugin-spec.md
contracts/mcp-integration-analysis.md
contracts/goal-achievement-level3-spec.md
```

不可写:

```text
backend/
frontend/
tests/
```

### 输入

- `contracts/goal-achievement-level3-spec.md`
- 当前 `contracts/api-spec.md`
- 当前 `contracts/agent-plugin-spec.md`
- 当前 `contracts/mcp-integration-analysis.md`

### 输出

- Level3 API 合同（含 Trace / Metrics / SSE 端点）
- Tool Registry 合同（含 Trace span_type 枚举）
- Safety 风险等级
- Web Search 降级策略

### 任务

| ID | 任务 | 输入 | 输出 | 验证 |
|---|---|---|---|---|
| C1 | 补充 Level3 API 合同 | Level3 spec | `api-spec.md` 新增 Reflection / Replan / ToolCall / Evaluation / **Trace / Metrics** 端点 | 每个端点有 method、path、body、response |
| C2 | 补充 Tool Registry 合同 | Level3 spec | `agent-plugin-spec.md` 新增 Tool / Safety / Audit / **Trace span_type 枚举** 规则 | 明确 low/medium/high 风险行为 |
| C3 | 补充 Web Search / MCP 合同 | Level3 spec | `mcp-integration-analysis.md` 补充 WebSearchTool | 明确联网失败 fallback |
| C4 | 补充 Level3 验收 checklist | Level3 spec | `goal-achievement-level3-spec.md` 新增 checklist | 每项可映射到测试或 UI 行为 |
| C5 | 定义 Goal Loop 状态机阈值 | Level3 spec | healthy/drifting/needs_reflection/needs_replan/waiting_confirmation 判定规则 | 每个状态有可测试条件 |
| C6 | 定义 Goal progress 计算公式 | Goal/GoalTask/TodoItem | `current_progress` 更新口径与数据来源 | T5 可按公式实现并单测 |
| C7 | 定义 Replan apply 风险矩阵 | Safety 规则、P5 schema | low/medium/high 变更边界 | P5b/P5c 可据此判断是否应用 |
| C8 | 明确 embedding 与 SemanticMemory MVP 策略 | Level3 spec、MCP 现状 | MVP 使用 keyword/tags，embedding_json 可为空；语义向量作为增强项 | T6/R4 不依赖 embedding 也能通过 |
| C9 | 明确首批工具范围与非 MVP 工具归属 | Level3 spec | create_goal/update_todo/search_knowledge/generate_reflection/propose_replan 的归属说明 | 规格工具清单与任务表一致 |
| C10 | 定义 Trace span_type 枚举与 SSE 事件格式 | Level3 spec 4.8 | api-spec.md 补充 span_type 列表 (plan/worker_dispatch/worker_execute/synthesis/persist/safety_check)、SSE 事件名和 payload schema | O3/O4/F02 可不猜格式直接开发 |

### 完成定义

合同变更完成后，Backend / Frontend Agent 可以不猜接口直接开发。

## 4.2 Backend Data Agent

### 职责

只负责数据模型和数据库安全初始化。

### 文件边界

可写:

```text
backend/models.py
backend/database.py
tests/
```

不可写:

```text
frontend/
contracts/
```

### 输入

- Contract Agent 的数据模型定义
- `backend/models.py`
- `backend/database.py`

### 输出

- 新增 SQLAlchemy 模型
- 安全建表机制
- 数据模型测试

### 任务

| ID | 任务 | 输入 | 输出 | 验证 |
|---|---|---|---|---|
| D0a | 验证 MVP 表可被现有初始化发现 | D1-D4 模型、`Base.metadata.create_all` | 新模型被 `backend.models` 导入后，启动时可安全创建缺失表，不删除旧数据 | 临时 DB 和现有 DB 均可创建 ToolCall / Reflection / Replan / SemanticMemory 表；不新增复杂迁移系统 |
| D1 | 新增 ToolCall 模型 | C2 | `AgentToolCall` | pytest 可创建、查询一条 tool call |
| D2 | 新增 Reflection 模型 | C1 | `AgentReflection` | pytest 可保存 goal_id、completion_rate |
| D3 | 新增 ReplanProposal 模型 | C1 | `AgentReplanProposal` | pytest 验证 pending/accepted/rejected 状态 |
| D4 | 新增 SemanticMemory 模型 | C2 | `AgentSemanticMemory` | pytest 可按 tag/source_type 查询 |
| D5 | 新增 EvaluationRun 模型并验证初始化 | C1、`Base.metadata.create_all` | `AgentEvaluationRun`，且可被现有初始化创建 | pytest 可写入 score、metrics_json；临时 DB 可创建 evaluation 表 |

### 完成定义

所有 Level3 表可以被创建和查询，且不影响现有 `Goal`、`GoalTask`、`TodoItem`。

## 4.3 Backend Tooling Agent

### 职责

负责 Tool Registry、Safety Gate、ToolCall 审计和基础工具。

### 文件边界

可写:

```text
backend/agent/tools/
backend/agent/__init__.py
tests/
```

必要时可读:

```text
backend/models.py
backend/database.py
backend/services/
```

不可写:

```text
frontend/
contracts/
```

### 输入

- Contract Agent 的 Tool / Safety 合同
- Backend Data Agent 的 `AgentToolCall`
- 当前 Todo / Goal 模型

### 输出

- `ToolRegistry`
- `SafetyGate`
- 工具调用审计
- 基础工具

### 任务

| ID | 任务 | 输入 | 输出 | 验证 |
|---|---|---|---|---|
| T1 | 实现 ToolRegistry 基类 | C2 | `backend/agent/tools/registry.py` | 单测注册、查找、调用 fake tool |
| T2 | 实现 SafetyGate | C2 | `backend/agent/tools/safety.py` | 单测 low 放行、high 阻止 |
| T3 | 实现 ToolCall 审计写入 | D1、T1 | 调用工具时写 `AgentToolCall` | 单测成功/失败都落库 |
| T4 | 实现 `create_todo` 工具 | T1、T2、T3、D1 | 工具写入 TodoItem 并记录 ToolCall | 单测传入 date/content 后生成 Todo，且审计落库 |
| T5 | 实现 `update_goal_progress` 工具 | T1、T2、T3、D1、C6 | 按公式更新 Goal.current_progress 并记录 ToolCall | 单测进度变更符合公式并记录 ToolCall |
| T6 | 实现 `search_memory` 工具 | D4、T1、C8 | 关键词/tag 检索 SemanticMemory；MVP 不依赖 embedding | 单测输入 query 返回命中片段，embedding_json 为空也可用 |
| T7 | 注册 `search_knowledge` 工具 | C9、现有 Searcher/MCP 能力 | 统一 ToolRegistry tool，封装已有知识库/MCP 查询 | 单测 fake MCP/本地知识查询返回 sources |
| T8 | 记录非 MVP 工具占位 | C9 | create_goal/update_todo/generate_reflection/propose_replan 的归属文档或 tool stub | 任务表和规格工具清单无缺口 |

### Safety 验证要求

必须覆盖:

```text
low: 自动执行
medium: 可执行，但必须审计
high: 不执行，但写 rejected audit
```

### 完成定义

后续 Reflection / Replanner / Web Search Agent 可以复用统一工具层，不需要各自实现审计和安全判断。

## 4.4 Backend Goal Loop Agent

### 职责

负责 Goal Achievement Loop 的后端状态聚合，不负责具体 AI 推理。

### 文件边界

可写:

```text
backend/routers/agent.py
backend/services/
tests/
```

不可写:

```text
frontend/
contracts/
```

### 输入

- `Goal`
- `GoalTask`
- `AgentReflection`
- `AgentReplanProposal`
- `AgentToolCall`

### 输出

- `GET /api/v1/agent/goals/{goal_id}/loop`
- 目标闭环状态 JSON

### 任务

| ID | 任务 | 输入 | 输出 | 验证 |
|---|---|---|---|---|
| L1 | 实现 Goal Loop 状态计算 | Goal、GoalTask、AgentReflection、AgentReplanProposal、C5 | healthy/drifting/needs_reflection/needs_replan/waiting_confirmation | 单测不同阈值条件返回不同状态 |
| L2 | 实现 Goal Loop API | L1 | `GET /agent/goals/{goal_id}/loop` | TestClient 返回完整 loop JSON |
| L3 | 处理空数据状态 | L2 | 无 reflection/proposal 时正常返回 | 单测新 goal 返回默认状态 |
| L4 | 实现 ToolCall 列表 API | D1、T3 | `GET /agent/tool-calls` | TestClient 可按 limit 返回记录 |

### 输出 JSON 建议

```json
{
  "goal": {},
  "loop_status": "healthy",
  "latest_reflection": null,
  "pending_replan": null,
  "recent_tool_calls": [],
  "metrics": {
    "completion_rate": 0.0,
    "skipped_count": 0,
    "overdue_count": 0
  }
}
```

### 完成定义

Frontend Agent 可以通过一个端点展示目标闭环总览。

## 4.5 Reflection Agent

### 职责

负责目标复盘逻辑。

### 文件边界

可写:

```text
backend/agent/workers/reflection.py
backend/services/
tests/
```

必要时可写:

```text
backend/agent/orchestrator.py
```

不可写:

```text
frontend/
contracts/
```

### 输入

- Goal
- GoalTask
- TodoItem
- SemanticMemory
- Tooling Agent 提供的工具层

### 输出

- `backend/services/reflection_service.py` 负责计算和写库
- `ReflectionWorker` 只包装 service 并返回 `WorkerResult`
- `POST /agent/goals/{goal_id}/reflect` 直接调用 service
- `AgentReflection`
- 可检索 memory 记录

### 任务

| ID | 任务 | 输入 | 输出 | 验证 |
|---|---|---|---|---|
| R1 | 实现目标完成率计算服务 | Goal、GoalTask、TodoItem | completion_rate / skipped / overdue 统计函数 | 单测构造 Todo，断言完成率 |
| R2 | 实现 Reflection service 写库 | R1、D2 | service 生成 `AgentReflection` 记录 | 单测调用 service 后数据库有 reflection |
| R3 | 提供 Reflection 手动 API handler/service 接口 | C1、R2 | 可被 API Integration Agent 挂载的手动触发方法；scheduler/orchestrator 触发后置 | service 级单测返回 reflection JSON 结构 |
| R4 | Reflection 进入记忆 | R2、D4 | 同步写 `AgentSemanticMemory` | 单测 reflection 后 memory 有记录 |
| R5 | 实现 ReflectionWorker 包装层 | R1、R2 | `backend/agent/workers/reflection.py` | Worker 返回 `WorkerResult.success=True` |
| R6 | 注册 ReflectionWorker（增强项，MVP 可后置） | R5 | Orchestrator 可路由到 reflection | 单测关键词命中 reflection worker |

### 完成定义

系统可以对一个长期目标生成结构化复盘，但不会直接修改计划。

## 4.6 Replanner Agent

### 职责

负责动态重规划。所有重规划必须先生成 proposal，不能直接覆盖计划。

### 文件边界

可写:

```text
backend/agent/workers/replanner.py
backend/services/
tests/
```

必要时可写:

```text
backend/agent/orchestrator.py
```

不可写:

```text
frontend/
contracts/
```

### 输入

- `AgentReflection`
- Goal / GoalTask / TodoItem
- SafetyGate
- ToolCall 审计

### 输出

- `backend/services/replanner_service.py` 负责规则判断、proposal 写库和 apply
- `ReplannerWorker` 只包装 service 并返回 `WorkerResult`
- `AgentReplanProposal`
- accept / reject API
- 受控应用计划变更

### 任务

| ID | 任务 | 输入 | 输出 | 验证 |
|---|---|---|---|---|
| P1 | 实现 replan 规则判断 | AgentReflection / R2 输出 | 判断是否连续失败/需重规划 | 单测 3 天失败返回 true |
| P2 | ReplanProposal 写库 service | P1、D3 | pending proposal | 单测不会修改原 Todo |
| P3 | 提供 Replan API handler/service 接口 | C1、P2 | 可被 API Integration Agent 挂载的 handler 或 service 方法 | service 级单测返回 proposal_id |
| P4 | 提供 Reject Replan handler/service 接口 | C1、P3 | 可被 API Integration Agent 挂载的 reject 方法 | service 级单测状态变 rejected，Todo 不变 |
| P5a | 定义 Replan change schema | P2、C7 | 支持 adjust_duration / move_date / create_todo，并标注风险等级 | 单测 schema 和风险等级校验 |
| P5b | 实现单条低风险变更应用 | P5a、T4、T5 | 优先复用工具/service 应用 Todo/Goal 调整，并写 ToolCall | 单测 Todo 被正确修改且审计落库 |
| P5c | 提供 Accept Replan handler/service 接口 | P5b | 可被 API Integration Agent 挂载的 accept 方法 | service 级单测 accepted 后应用变更 |
| P6 | 实现 ReplannerWorker 包装层 | P1、P2 | `backend/agent/workers/replanner.py` | Worker 返回 proposal JSON |
| P7 | 注册 ReplannerWorker（增强项，MVP 可后置） | P6 | Orchestrator 可路由到 replanner | 单测关键词命中 replanner worker |

### Safety 要求

必须阻止:

```text
删除 Goal
删除历史 Todo
批量修改未来 7 天以上计划
写外部日历
发送外部消息
```

### 完成定义

用户连续失败后，系统能生成重规划候选；只有用户 accept 后才应用允许范围内的变更。

## 4.7 Backend API Integration Agent

### 职责

统一负责把各后端 service/handler 挂载到 `backend/routers/agent.py`，降低多个 Agent 同时修改同一路由文件造成的冲突。

### 文件边界

可写:

```text
backend/routers/agent.py
tests/
```

可读:

```text
backend/services/
backend/agent/tools/
backend/models.py
contracts/api-spec.md
```

不可写:

```text
frontend/
contracts/
backend/agent/workers/
```

### 输入

- C1 API 合同
- L2 的 Loop 查询能力
- L4 的 ToolCall 查询能力
- R3 的 Reflection handler/service 接口
- P3 / P4 的 Replan / Reject handler/service 接口
- P5c 的 Accept handler/service 接口
- E3 / E4 的 Evaluation handler/service 接口

### 输出

- `backend/routers/agent.py` 中统一挂载的 Level3 API
- TestClient 集成测试

### 任务

| ID | 任务 | 输入 | 输出 | 验证 |
|---|---|---|---|---|
| API1a | 挂载 Goal Loop API | C1、L2 | `GET /agent/goals/{goal_id}/loop` | TestClient 返回 loop JSON |
| API1b | 挂载 ToolCall 列表 API | C1、L4 | `GET /agent/tool-calls` | TestClient 返回 tool-calls JSON |
| API2 | 挂载 Reflection API | C1、R3 | `POST /agent/goals/{id}/reflect` | TestClient 返回 reflection JSON |
| API3a | 挂载 Replan / Reject API | C1、P3、P4 | replan、reject 端点 | TestClient 覆盖 pending/rejected |
| API3b | 挂载 Accept Replan API | C1、P5c | accept 端点 | TestClient 覆盖 accepted 并验证数据变更 |
| API4 | 挂载 Evaluation API | C1、E3、E4 | evaluations run/list 端点 | TestClient 返回 score 和历史记录 |

### 完成定义

`backend/routers/agent.py` 的 Level3 路由由单一 Agent 集成，其他后端 Agent 不直接并行修改该文件。
## 4.8 Evaluation Agent

### 职责

负责离线评估和可证明性。

### 文件边界

可写:

```text
tests/evals/
backend/agent/evaluation/
tests/
```

不可写:

```text
frontend/
contracts/
```

### 输入

- 固定 eval cases
- Reflection / Replan / Safety 可调用接口
- `AgentEvaluationRun`

### 输出

- EvalRunner
- Evaluation API
- Evaluation 历史记录

### 任务

| ID | 任务 | 输入 | 输出 | 验证 |
|---|---|---|---|---|
| E1 | 定义 5 个离线 eval case | Level3 spec | `tests/evals/goal_cases.json` | 每个 case 有 input、expected |
| E2 | 实现 EvalRunner | E1、D5 | 运行 case 并输出 score | 单测 fake case 通过 |
| E3 | 提供 Evaluation run handler/service 接口 | C1、E2 | 可被 API Integration Agent 挂载的 run 方法 | service 级单测返回 score |
| E4 | 提供 Evaluation 列表 handler/service 接口 | D5 | 可被 API Integration Agent 挂载的 list 方法 | service 级单测返回历史记录 |

### Eval Case 必须覆盖

```text
1. 正常完成目标，不需要 replan
2. 连续 3 天失败，需要 reflection
3. 连续失败后需要 replan proposal
4. high risk change 必须被拒绝
5. 工具调用失败必须写审计
```

### 完成定义

项目可以用固定 eval case 证明 Level3 关键决策可测。

## 4.9 Frontend Agent

### 职责

负责 Level3 可视化和用户操作，不碰后端。

### 文件边界

可写:

```text
frontend/src/api/agent.ts
frontend/src/components/agent/
frontend/src/views/
frontend/src/types/
```

不可写:

```text
backend/
contracts/
tests/
```

### 输入

- `contracts/api-spec.md`
- Goal Loop API
- Reflection API
- Replan API
- ToolCall API
- Evaluation API

### 输出

- API 封装
- Goal Loop 状态视图
- Reflection 记录视图
- ReplanProposal 确认 UI
- ToolCall 审计列表
- Evaluation 结果视图

### 任务

| ID | 任务 | 输入 | 输出 | 验证 |
|---|---|---|---|---|
| F1 | Agent API 封装 | C1 | `frontend/src/api/agent.ts` 增加 Level3 方法 | TypeScript build 通过 |
| F2 | 目标闭环状态组件 | F1 | 显示 completion/reflection/replan 状态 | mock 数据渲染正常 |
| F3 | Reflection 记录视图 | F1 | 展示完成率、偏差原因、建议 | 页面无溢出，字段齐全 |
| F4 | ReplanProposal 确认 UI | F1 | accept/reject 按钮 | 点击调用对应 API |
| F5 | ToolCall 审计列表 | F1 | 展示 tool、risk、status、time | mock 列表可滚动查看 |
| F6 | Evaluation 结果视图 | F1 | 展示 score、passed、failure_reason | build 通过 |

### UI 约束

- 不做营销页。
- 不用解释性大段文字。
- 工作台式布局，信息密度适中。
- 空状态、加载态、错误态必须存在。
- 移动端不能出现文本重叠。

### 完成定义

前端能展示 Level3 闭环并允许用户 accept / reject replan。

## 4.10 QA / Integration Agent

### 职责

负责最终集成验证，不实现业务功能。

### 文件边界

可写:

```text
tests/
```

必要时可写:

```text
PROGRESS.md
```

不可写:

```text
backend/业务实现文件
frontend/业务实现文件
contracts/接口合同
```

### 输入

- 所有 Agent 完成结果
- 测试命令
- 合同验收清单

### 输出

- 集成测试报告
- 失败点列表
- 是否可提交结论

### 任务

| ID | 任务 | 输入 | 输出 | 验证 |
|---|---|---|---|---|
| Q1 | Worker 协议回归测试 | 全部后端变更 | 确认 `TaskBrief/WorkerResult` 未破坏 | `tests/test_workers.py` 通过 |
| Q2a | MVP API 集成测试 | Loop / Reflection / Replan-Reject API | 覆盖 loop/reflect/replan/reject | TestClient 全过 |
| Q2b | 完整 API 集成测试 | ToolCall / Replan-Accept / Evaluation / Frontend 依赖 API | 覆盖 accept/eval/frontend 依赖接口 | TestClient 全过 |
| Q3 | Safety 回归测试 | Tooling | high risk 不执行但写审计 | pytest 断言 ToolCall status |
| Q4 | 前端构建验证 | F1-F6 | 构建产物 | `cd frontend && npm run build` |
| Q5 | 总质量门禁 | 所有任务 | 可提交增量 | pytest + frontend build 全过 |

### 必跑命令

```bash
venv/Scripts/python -m pytest tests/ -v
cd frontend && npm run build
```

### 完成定义

Level3 主链路可跑通:

```text
create goal
-> loop
-> reflect
-> replan
-> reject or accept
-> audit
-> eval
```

## 4.11 Backend Observability Agent

### 职责

负责 Agent 协同过程的可观测性基础设施——结构化 Trace、指标聚合、SSE 编排事件流。不负责业务逻辑。

### 文件边界

可写:

```text
backend/agent/observability/
backend/models.py
backend/routers/agent.py
tests/
```

必要时可读:

```text
backend/agent/orchestrator.py
backend/agent/workers/
backend/database.py
```

不可写:

```text
frontend/
contracts/
backend/services/ (业务层)
```

### 输入

- 当前 `orchestrator.py` 的 `_log_plan()` + `_persist_to_memory()` 实现
- 当前 `routers/agent.py` 的 `/activity` 端点（regex 解析 Markdown）
- Contract Agent C1 的 Trace / Metrics API 合同
- Backend Data Agent 的模型

### 输出

- `backend/agent/observability/tracer.py` — 结构化 Trace 写入（双写 Markdown + SQLite）
- `backend/agent/observability/metrics.py` — AgentMetrics 聚合
- `backend/agent/observability/sse.py` — 编排 SSE 事件发射器
- `AgentTrace` + `AgentMetrics` 模型
- Trace / Metrics API
- Orchestrator 集成（编排时写 Trace + 发 SSE 事件）

### 任务

| ID | 任务 | 输入 | 输出 | 验证 |
|---|---|---|---|---|
| O1 | 新增 AgentTrace 模型 | D0a 框架 | `AgentTrace` 模型 + 可被 `Base.metadata.create_all` 发现 | pytest 可创建、按 orchestration_id 查询 |
| O2 | 新增 AgentMetrics 模型 | D0a 框架 | `AgentMetrics` 模型 | pytest 可写入日期聚合记录 |
| O3 | 实现结构化 Tracer | O1、现有 `_log_plan` / `_persist_to_memory` | `backend/agent/observability/tracer.py` — `TraceCollector.record_span()` 双写 SQLite + Markdown | 单测模拟编排后，可通过 orchestration_id 查询完整 Trace 树 |
| O4 | 实现 SSE 事件发射器 | O3、现有 `chat/stream` | `backend/agent/observability/sse.py` — `emit_plan()` / `emit_worker_start()` / `emit_worker_done()` | 单测 SSE 流包含 worker_start + worker_done 事件 |
| O5 | 集成到 Orchestrator | O3、O4 | `Orchestrator.handle()` 在 plan/worker_dispatch/worker_execute/synthesis/persist 阶段自动写 Trace + SSE | 集成测试编排后 Trace 表有完整 span 树 |
| O6 | 实现 Trace API | O3 | `GET /agent/traces` + `GET /agent/traces/{orchestration_id}` | TestClient 按 orchestration_id 返回完整 span 树 JSON |
| O7 | 实现 Metrics API | O2、O3 | `GET /agent/metrics` 支持 days 和 agent_name 筛选 | TestClient 返回 Worker 成功率、P50/P95 延迟 |
| O8 | 存量 Markdown 日志兼容 | O3、现有 `_log_plan()` | 双写不破坏现有 plan-logs/ 结构，现有 `/activity` API 继续可用 | 现有 ActivityLog.vue 仍可渲染历史日志 |
| O9 | Safety Gate Trace 集成 | O5、T2 | SafetyGate 检查结果写入 span_type=safety_check 的 Trace | 单测被拒绝的 high risk 调用有 Trace 记录 |

### 数据流设计

```
Orchestrator.handle()
  │
  ├─ _plan()
  │    └─ tracer.record_span(span_type="plan", ...)
  │    └─ sse.emit_plan(...)
  │
  ├─ _execute_subtask() × N
  │    ├─ tracer.record_span(span_type="worker_execute", agent_name="searcher", ...)
  │    ├─ sse.emit_worker_start(worker="searcher", ...)
  │    ├─ worker_result = await worker.execute(brief)
  │    └─ sse.emit_worker_done(worker="searcher", elapsed_ms=..., success=...)
  │
  ├─ _synthesize()
  │    └─ tracer.record_span(span_type="synthesis", ...)
  │
  ├─ SafetyGate
  │    └─ tracer.record_span(span_type="safety_check", success=allowed, ...)
  │
  └─ _persist_to_memory()
       └─ tracer.record_span(span_type="persist", ...)
       └─ tracer.flush()  ← 批量写入 SQLite
```

### 完成定义

每次编排自动生成结构化 Trace，前端可通过 API 查看调用链路瀑布图和 Agent 指标趋势。

## 4.12 Frontend Observability Agent

### 职责

负责 Level3 可观测性前端可视化——Trace 瀑布图、Agent 拓扑图、指标面板。不碰后端。

### 文件边界

可写:

```text
frontend/src/api/agent.ts
frontend/src/components/agent/
frontend/src/types/
```

不可写:

```text
backend/
contracts/
tests/
```

### 输入

- `contracts/api-spec.md` 中 Trace / Metrics / SSE 端点
- 现有 `ActivityLog.vue`
- 现有 `AgentPanel.vue` 的 Tab 结构

### 输出

- SSE 事件监听 + Trace 瀑布图（横向甘特图）
- Agent 拓扑图（节点 = Worker，边 = 编排路由频率）
- Agent 指标面板（成功率、P50/P95 延迟趋势）
- 更新 AgentPanel Tab 增加 "Observe" 标签

### 任务

| ID | 任务 | 输入 | 输出 | 验证 |
|---|---|---|---|---|
| FO1 | Agent API 封装 — Trace + Metrics + SSE | C1 API 合同 | `frontend/src/api/agent.ts` 增加 `getTraces` / `getTraceTree` / `getMetrics` / `subscribeOrchestration` | TypeScript build 通过 |
| FO2 | Trace 瀑布图组件 | FO1、O6 | 横向时间轴展示一次编排的所有 span（plan→worker×N→synthesis→persist） | mock 数据渲染，各 span 颜色区分类型，延时标注 |
| FO3 | Agent 拓扑图组件 | FO1 | 展示当前 Worker 注册关系，节点大小按近期调用量缩放 | mock 拓扑渲染，点击节点展开详情 |
| FO4 | Agent 指标面板 | FO1、O7 | 7/30 天成功率折线 + P50/P95 延迟柱状图 | mock 数据渲染，可按 Worker 筛选 |
| FO5 | SSE 编排实时进度 | FO1、O4 | 编排过程中实时推送 Worker 执行状态（loading→done/fail） | 模拟 SSE 事件流，动画过渡正常 |
| FO6 | 更新 AgentPanel Tab | FO2-FO5 | 新增 "Observe" Tab，整合 Trace / 拓扑 / 指标 | build 通过，Tab 切换正常 |

### UI 约束

- Trace 瀑布图不使用第三方图表库，用 CSS flex + 绝对定位实现横向条形图
- Worker 不同状态用色板区分：plan=灰, execute=蓝, synthesis=绿, safety=红, persist=紫
- 拓扑图使用 CSS Grid + SVG 连线（或纯 DOM 节点 + CSS 连线）

### 完成定义

前端可在 "Observe" Tab 中查看最近编排的 Trace 瀑布图、Worker 拓扑关系和指标趋势。

## 4.13 目标导向依赖校验

从最终目标 `Observe -> Plan -> Execute -> Track -> Reflect -> Replan -> Evaluate` 反推，当前任务必须满足以下依赖:

- `Observe` 依赖 `AgentTrace`、`AgentMetrics`、Tracer（结构化写入）、SSE 事件发射器。因此 O1-O5 必须在第〇批完成。
- `Reflect` 依赖 `AgentReflection`；若要写入长期记忆，还依赖 `AgentSemanticMemory`，MVP 仅要求 keyword/tag memory。
- `Replan` 依赖 `AgentReplanProposal` 和 Reflection 输出；accept/apply 依赖 T4/T5 与 C7 风险矩阵。
- `Audit` 依赖 `AgentToolCall`、`ToolRegistry`、`SafetyGate`；所有写工具必须落审计且写入 Trace（span_type=safety_check）。
- `Evaluate` 依赖 `AgentEvaluationRun`，因此 D5 必须在 E1-E4 前完成。
- `Frontend` 依赖已冻结 API 合同和由 Backend API Integration Agent 挂载完成的 Loop / Reflection / Replan / ToolCall / Evaluation / Trace / Metrics API。
- **新增依赖**: `SafetyGate` 拒绝事件写入 Trace（O9 → T2 互依赖）。
- **新增依赖**: SSE 编排进度流依赖 Orchestrator 集成（O4、O5），必须在 O3 完成后推进。

因此 MVP 若包含 `R4 Reflection 进入记忆`，必须同时包含 `D4 SemanticMemory 模型`。完整 Evaluation 阶段开始前必须先完成 `D5 EvaluationRun 模型`。**第〇批完成后，编排即可从 Trace API 查询完整调用链路。**
## 5. 推荐开发顺序

严格建议按以下顺序推进:

```text
第〇批 (Observability + Safety Foundation):
  C1(可观测性端点), C2(安全规则) → O1, O2 → D1, D2, D3, D4, D0a → T1, T2, T3 → O3, O4, O5, O8
  → L1, L2, L3

第一批 (Goal Loop + Reflection + Replanning MVP):
  T4, T5 → R1, R2, R3, R4 → P1, P2, P3, P4
  → API1a, API2, API3a → Q1, Q2a, Q3

第二批 (Full Tooling + Replan Apply + Observability Frontend):
  T6, T7, T8 → R5 → P5a, P5b, P5c → L4 → O6, O7, O9 → API1b, API3b
  → FO1-FO6

第三批 (Evaluation + Full Frontend):
  D5 → E1-E4 → API4 → F1-F6 → Q2b, Q4, Q5
```

每一阶段完成后，Team Lead / Architect Agent 必须检查:

- 是否满足合同。
- 是否破坏已有协议。
- 是否可测试。
- **第〇批完成后必须确认: Trace 瀑布图可在本地查看编排调用链路。**
- 是否影响其他 Agent 的边界。

## 6. 上下文控制策略

为了避免 Claude Code / 子 Agent 上下文过载:

| Agent | 建议读取范围 | 避免读取 |
|---|---|---|
| Contract Agent | `contracts/` | 完整后端实现 |
| Backend Data Agent | `backend/models.py`, `backend/database.py`, `tests/` | 前端 |
| Backend Observability Agent | `backend/agent/orchestrator.py`, `backend/agent/observability/`, `backend/models.py`, `backend/routers/agent.py`, `tests/` | 前端、Worker 实现 |
| Backend Tooling Agent | `backend/agent/`, `backend/models.py`, `backend/database.py`, `tests/` | 前端页面 |
| Reflection Agent | `backend/agent/workers/`, `backend/services/`, `backend/models.py`, `tests/` | 整个前端、路由集成 |
| Replanner Agent | `backend/agent/workers/`, `backend/services/`, `backend/models.py`, `tests/` | 整个前端、路由集成 |
| Backend API Integration Agent | `backend/routers/agent.py`, `backend/services/`, `contracts/api-spec.md`, `tests/` | 前端、Worker 实现 |
| Frontend Agent | `contracts/api-spec.md`, `frontend/src/` | 后端实现 |
| Frontend Observability Agent | `contracts/api-spec.md`, `frontend/src/components/agent/`, `frontend/src/api/agent.ts` | 后端实现 |
| QA Agent | 全局可读 | 默认不改业务实现 |

## 7. 防幻觉交接规则

后续 Claude Code 创建 Agent 时，必须在任务提示中包含:

```text
你只能修改指定文件边界内的文件。
如果需要修改边界外文件，停止并报告原因。
所有新增 API 必须来自 contracts/api-spec.md。
不得修改 TaskBrief / WorkerResult。
不得删除 data/ 或 dist/data/。
每个任务完成后必须给出验证命令和结果。
```

每个 Agent 完成报告必须包含:

```text
1. 修改了哪些文件
2. 完成了哪些任务 ID
3. 输入/输出是否符合合同
4. 运行了哪些验证
5. 未完成事项或阻塞点
6. 是否触碰边界外文件
```

## 8. 最小可交付切片

如果要先做一个最小 Level3 MVP，建议只做:

```text
第〇批 MVP:
  C1, C2
  O1, O2, O3, O4, O5, O8
  D0a, D1, D2, D3, D4
  T1, T2, T3
  L1, L2, L3

第一批 MVP:
  R1, R2, R3, R4
  P1, P2, P3, P4
  Q1, Q2a, Q3
```

MVP 不要求:

- 完整前端 UI (含 Trace 瀑布图)
- Web Search
- embedding 相似度
- 完整 Evaluation Dashboard
- SSE 实时编排流（O4 为增强项）
- Metrics API 和前端面板

MVP 必须证明:

```text
编排过程有结构化 Trace（可从 API 查询调用链路树）
目标可反思
连续失败可生成重规划候选
工具调用有审计且 Trace 可关联
高风险动作被阻止且 Trace 留有 Safety 拒绝记录
原 Worker 协议未破坏
```

## 9. 最终质量门禁

开发结束必须通过:

```bash
venv/Scripts/python -m pytest tests/ -v
cd frontend && npm run build
```

如果其中任一失败，不得标记为完成。











