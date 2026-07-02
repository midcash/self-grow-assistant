# Agent评估系统规格 v1

> 成熟度: 🔴 草案 — Phase 0 合约先行，代码尚未实现。
> 参考: Google Agent Bake-Off 评估框架 + 美团龙猫论文 + AI Engineering EDD理念

---

## 一、这个功能要解决什么问题

### 1.1 背景

当前项目拥有完善的 Agent 多智能体架构（5 Workers + Orchestrator）和可观测性基础设施（TraceCollector + MetricsAggregator），但**完全没有 Agent 质量评估能力**。

现状问题：
- Worker 的 system_prompt 质量无法量化（写得是好是坏不知道）
- Tool calling 决策正确性无法验证（MCP 是否该调用、参数是否正确）
- RAG 检索质量无法衡量（召回率、准确率、幻觉率）
- 推理和规划过程无法评估（GoalDecomposer 分解质量、Coach CBT 遵循度）
- 每次修改代码后，无法判断 Agent 能力是变好还是变坏

### 1.2 核心目标

建立一套完整的 Agent 评估流水线，覆盖从组件到集成的全链路质量评估：

1. **LLM-as-Judge 引擎**：用大模型当裁判，对 Worker 输出进行多维度评分
2. **组件评估**：对 Prompt / ToolCall / RAG / Reasoning / Trajectory 五个维度分别量化
3. **评估数据集**：为每个 Worker 建立黄金测试集（至少 5 个用例）
4. **自动化流水线**：EvalRunner 一键运行所有评估，输出 EvalReport
5. **发布闸门**：基于阈值判断是否允许发布（smoke / release 两级）

---

## 二、影响面分析

### 2.1 新增模块

```
backend/agent/evaluation/          ← 新模块，与 observability/ 平级
├── __init__.py
├── judge.py                       ← LLM-as-Judge 核心引擎
├── rubric.py                      ← 评分rubric数据结构
├── bias.py                        ← 偏差缓解策略
├── dataset.py                     ← EvalExample/EvalDataset 数据结构
├── datasets/                      ← Worker 黄金测试集
│   ├── searcher.py / profiler.py / scheduler.py
│   ├── goal_decomposer.py / coach.py / orchestrator.py
├── evaluators/                    ← 组件评估器
│   ├── base.py / prompt_eval.py / tool_call_eval.py
│   ├── reasoning_eval.py / rag_eval.py / trajectory_eval.py
├── runner.py                      ← EvalRunner 编排器
├── gates.py                       ← ReleaseGate 发布闸门
└── default_gates.py               ← 预定义闸门
```

### 2.2 修改现有模块

| 模块 | 改动 | 原因 |
|------|------|------|
| `backend/models.py` | 新增 AgentEvaluationRun / AgentEvaluationResult / AgentEvalDataset 三个表 | 持久化评估结果 |
| `backend/main.py` | 注册 evaluation router | 暴露评估 API |
| `backend/routers/` | 新增 evaluation.py | 评估 REST API |
| `frontend/src/api/agent.ts` | 新增评估 API 函数 | 前端调用 |
| `frontend/src/components/agent/observe/ObservePanel.vue` | 新增 Evaluation tab | 前端展示 |

### 2.3 不修改的模块

| 模块 | 原因 |
|------|------|
| `backend/agent/workers/base.py` (TaskBrief/WorkerResult协议) | 评估系统读取 Worker 输出，不修改协议 |
| `backend/agent/orchestrator.py` | 评估系统独立运行，不侵入编排流程 |
| `backend/agent/observability/` | 评估结果通过 TraceCollector API 写入，不修改 tracer 内部 |

### 2.4 新增 API 端点

```
POST /api/v1/agent/evaluation/run           ← 触发评估
GET  /api/v1/agent/evaluation/runs          ← 运行历史
GET  /api/v1/agent/evaluation/runs/{id}     ← 运行详情
GET  /api/v1/agent/evaluation/datasets      ← 数据集列表
GET  /api/v1/agent/evaluation/summary       ← 仪表盘摘要
```

---

## 三、成功标准

### 3.1 Phase 1-4 完成标准（核心）

1. LLMJudge 可对任意文本进行多维度评分（含偏差缓解）
2. 每个 Worker 至少有 5 个评估用例
3. 五类评估器（prompt / tool_call / reasoning / rag / trajectory）均可正常运行
4. EvalRunner 一键运行 → 输出完整 EvalReport
5. ReleaseGate 可根据阈值判断通过/不通过

### 3.2 Phase 5-6 完成标准（接口层）

6. 评估 API 全部可用（POST run / GET runs / GET datasets / GET summary）
7. 前端 EvaluationPanel 正确展示 Empty / Loading / Running / Error / HasRuns 五种状态

### 3.3 质量门禁

```bash
venv/Scripts/python -m pytest tests/ -v    # 所有测试通过
cd frontend && npm run build              # 前端构建成功
```

### 3.4 数据流验证

```
触发评估 → EvalRunner加载数据集 → Evaluator评分 → LLMJudge打分
→ EvalReport聚合 → ReleaseGate检查 → 写DB → 前端展示
```
