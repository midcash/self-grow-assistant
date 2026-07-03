# 会话交接文档: Agent评估体系 + 在线监控基线

> 会话日期: 2026-07-02 ~ 2026-07-03
> 交接目的: 新会话快速了解评估和监控模块的已完成工作、当前问题和后续计划
> 测试状态: 124 个测试全部通过 + 前端构建成功

---

## 一、当前已完成内容

### 1.1 评估系统 (Agent Evaluation)

#### 评估理念对齐

参照"Agent评估全流程"理论文档，项目现在覆盖了完整评估生命周期的核心阶段:
- **EDD 哲学**: 评估驱动开发，先建评估体系再继续开发
- **三把通用武器**: LLM-as-Judge / Code-based评估 / (人工评估暂缓)
- **全流程**: 模型选型(已有) → 组件评估 → 集成Pipeline → 发布闸门 → 上线监控

#### 已实现模块 (backend/agent/evaluation/)

```
backend/agent/evaluation/
├── __init__.py              ← 模块入口, 导出所有公共API
├── rubric.py                ← EvalRubric + RubricDimension (评分标准结构)
├── bias.py                  ← BiasMitigator (位置/冗长/自我强化偏差缓解)
├── judge.py                 ← LLMJudge (绝对评分/参照对比/成对比较)
├── dataset.py               ← EvalExample + EvalDataset (数据集结构)
├── runner.py                ← EvalRunner + EvalConfig + EvalReport
├── gates.py                 ← ReleaseGate + GateCondition + GateResult
├── default_gates.py         ← SMOKE_GATE + RELEASE_GATE (预定义闸门)
├── datasets/                ← 6个Worker黄金测试集 (36个评估用例)
│   ├── searcher.py          ← 7个用例 (prompt/MCP决策(4)/RAG(2))
│   ├── profiler.py          ← 5个用例 (prompt/推理(4))
│   ├── scheduler.py         ← 5个用例 (prompt/工具调用(4))
│   ├── goal_decomposer.py   ← 6个用例 (prompt/分解结构/JSON/颗粒度)
│   ├── coach.py             ← 7个用例 (prompt/CBT六场景)
│   └── orchestrator.py      ← 6个用例 (Worker路由/综合质量)
└── evaluators/              ← 5类组件评估器
    ├── base.py              ← BaseEvaluator抽象 + 通用断言运行器
    ├── prompt_eval.py       ← PromptEvaluator (Worker系统提示词评分)
    ├── tool_call_eval.py    ← ToolCallEvaluator (MCP决策/执行结果)
    ├── reasoning_eval.py    ← ReasoningEvaluator (LLM-as-Judge推理评分)
    ├── rag_eval.py          ← RAGEvaluator (检索相关性/来源/忠实度)
    └── trajectory_eval.py   ← TrajectoryEvaluator (Worker路由匹配)
```

#### API端点 (5个)

```
POST /api/v1/agent/evaluation/run        ← 触发评估流水线
GET  /api/v1/agent/evaluation/runs       ← 评估运行历史列表
GET  /api/v1/agent/evaluation/runs/{id}  ← 单次评估详情
GET  /api/v1/agent/evaluation/datasets   ← 可用数据集列表
GET  /api/v1/agent/evaluation/summary    ← 评估仪表盘摘要
```

#### 数据库表 (3个)

| 表名 | 用途 |
|------|------|
| `agent_evaluation_runs` | 评估运行记录 (eval_name/passed/score/duration_ms/...) |
| `agent_evaluation_results` | 单用例评估结果 (example_id/worker/eval_type/score/reasoning) |
| (AgentTrace/AgentMetrics 复用已有的可观测性表) | |

#### 发布闸门 (2级)

| 闸门 | 条件 |
|------|------|
| **SMOKE_GATE** | prompt>=3.0, tool_call>=3.0, trajectory>=3.0 |
| **RELEASE_GATE** | prompt>=4.0, tool_call>=4.0, reasoning>=3.5, rag>=3.5, trajectory>=3.5 |

#### 前端 (1个新增组件)

| 组件 | 位置 | 功能 |
|------|------|------|
| `EvaluationPanel.vue` | observe/目录 | 评估看板 (Empty/Loading/Running/Error/HasRuns 5状态) |
| `useEvaluation.ts` | composables/ | 评估状态管理 (run/select/fetch/trigger) |
| `ObservePanel.vue` | observe/目录 | 已修改: 新增"评估"tab |

#### 合约文档 (3份)

| 文件 | 内容 |
|------|------|
| `contracts/agent-evaluation-spec.md` | 评估系统规格 (需求/影响面/成功标准) |
| `contracts/agent-evaluation-adr.md` | 6个架构决策记录 (独立模块/复用LLM/代码数据集/Evaluator模式/两级闸门/同步API) |
| `contracts/api-spec.md` | 已更新: 新增第7章Agent评估API |

---

### 1.2 在线监控系统 (Online Monitoring)

#### 四维度监控基线

| 维度 | 实现组件 | 采集方式 | DB存储 |
|------|---------|---------|--------|
| **1. 质量与行为** | `QualitySampler` | 每10次聊天抽样1次 LLM-as-Judge评分 | `agent_quality_samples` |
| **2. 漂移与异常** | `Monitor` | 7天滚动基线 + 阈值偏离检测 | `agent_baselines` + `agent_anomalies` |
| **3. 成本/效率/延迟** | `TraceCollector`增强 | Token估算(字符数/3) + 成本($2/M tokens) | `agent_metrics.total_token_estimate` |
| **4. 安全/合规** | `SafetyScanner` | 每次对话扫描越狱/PII/有害内容 | `agent_safety_logs` |

#### 新增实现模块

```
backend/agent/observability/
├── quality_sampler.py   ← QualitySampler (采样率/轻量评分/持久化)
├── safety.py            ← SafetyScanner (越狱规则(7)/PII(4)/有害(6))
└── monitor.py           ← Monitor (基线重建/异常检测/阈值检查)

修改:
├── tracer.py            ← record_span() 新增 tokens_used/cost_estimate 参数
├── metrics.py           ← aggregate_daily() 从metadata_json提取token统计
└── (orchestrator.py)    ← handle() 在Step 5.6插入安全扫描+质量抽样+Token估算
```

#### 监控配置 (monitor.py MONITOR_CONFIG)

```python
baseline_window_days: 7       # 7天滚动窗口
anomaly_thresholds:
  success_rate:    下降 > 20%       → warning
  avg_latency_ms:  暴涨 > 2.0x      → warning
  p95_latency_ms:  暴涨 > 2.5x      → warning
  quality_score:   下降 > 1.0分     → warning/critical
  error_count:     暴涨 > 3.0x      → warning
  safety_score:    下降 > 20分      → critical
```

#### 新增API端点 (6个)

```
GET  /api/v1/agent/monitor/summary          ← 4维度一览 (质量/异常/成本/安全)
GET  /api/v1/agent/monitor/anomalies        ← 异常事件列表
GET  /api/v1/agent/monitor/quality-trend    ← 质量趋势图 (按天聚合)
GET  /api/v1/agent/monitor/safety-log       ← 安全日志列表
POST /api/v1/agent/monitor/rebuild-baseline ← 手动重建基线
POST /api/v1/agent/monitor/check            ← 手动触发异常检查
```

#### 新增DB表 (4个)

| 表名 | 关键字段 |
|------|---------|
| `agent_quality_samples` | orchestration_id / quality_score / quality_dims_json / sampling_rate |
| `agent_baselines` | metric_name / agent_name / baseline_value / std_dev / p50/p95 |
| `agent_anomalies` | anomaly_type / severity / current_value / baseline_value / deviation_pct |
| `agent_safety_logs` | orchestration_id / safety_score / jailbreak_attempt / pii_detected / harmful_content / flags_json |

#### 前端监控展示

| 展示位置 | 内容 |
|---------|------|
| **每条Agent回复下方** | 芯片指示器: `[S100]` 安全分/ `[Q4.2]` 质量分(抽样)/ `[~85t]` tokens |
| **底部栏** | 会话累计: `T:1280 $0.0026 3warn` |
| **观察→评估tab** | 评估运行历史+详情 (已有) |

#### 数据流 (一次完整对话)

```
用户输入 → Orchestrator.handle()
  ├─ _plan() → 意图分析 + Worker路由
  ├─ _execute_subtask() × N → Worker执行 (TraceCollector记录spans)
  ├─ _synthesize() → 结果合成
  ├─ _ensure_monitors() → 延迟初始化监控组件
  ├─ SafetyScanner.scan() → 越狱/PII/有害检测 (同步, <1ms)
  ├─ QualitySampler.maybe_sample() → 1/10抽样评分 (异步, LLM调用)
  ├─ Token/成本估算 → 字符数/3 ≈ tokens, ×$2/M ≈ cost
  ├─ 返回 monitoring: { safety, quality, tokens_estimated, cost_estimated }
  └─ 前端捕获 → messages[].monitoring → 显示芯片 + 累计摘要
```

---

### 1.3 测试覆盖

| 测试文件 | 测试数 | 覆盖内容 |
|---------|--------|---------|
| `tests/test_evaluation_judge.py` | 34 | rubric生成/score解析/偏差缓解/成对比较/错误处理 |
| `tests/test_evaluation_datasets.py` | 21 | 数据集结构/过滤/最小用例数/ID唯一性/维度覆盖 |
| `tests/test_evaluation_evaluators.py` | 17 | 断言运行/ToolCall MCP决策/Trajectory路由/错误处理 |
| `tests/test_evaluation_runner.py` | 20 | EvalConfig/EvalRunner流程/闸门检查/标签过滤 |
| `tests/test_observability_monitor.py` | 17 | 安全扫描(7)/质量抽样(4)/Monitor基线检测(6) |
| `tests/test_workers.py` | 15 | 已有测试(未改动) |
| **合计** | **124** | |

---

## 二、当前仍存在的问题

### 2.1 技术债

| # | 问题 | 严重程度 | 说明 |
|---|------|---------|------|
| 1 | **Token追踪是估算而非精确** | 中 | 当前用 `字符数/3` 估算token数。真正的token数需要从 `LLMResponse.tokens_used` 获取，但这要求修改所有5个Worker的 `_call_llm()` 调用点。建议后续改造 WorkerBase._call_llm 统一返回 token 数。 |
| 2 | **QualitySampler评分覆盖不完整** | 中 | 抽样率1/10意味着90%的对话没有质量评分。从统计角度这足够检测趋势漂移，但用户可能期望每条对话都能看到质量分。提高抽样率会增加LLM调用成本。 |
| 3 | **基线重建需手动触发** | 低 | `Monitor.rebuild_baseline()` 目前只能通过API手动调用。应加入每日定时任务(在AgentScheduler的tick中自动调用)。 |
| 4 | **安全扫描仅基于正则表达式** | 低 | 正则规则覆盖常见攻击模式，但无法检测精心构造的越狱(如分片指令、编码绕过)。正规安全检测需要专用模型或API。 |
| 5 | **单数据库写入无事务保护** | 低 | TraceCollector的span写入和SafetyScanner的日志写入都在独立Session中，无跨表事务。对监控场景影响不大，但极端情况下可能丢失少量数据。 |

### 2.2 设计限制

| # | 问题 | 说明 |
|---|------|------|
| 1 | **离线评估与在线监控的联系弱** | EvalRunner 和在线监控在代码上是两套独立系统。离线评估的结果(如发现prompt质量下降)不会自动触发在线监控的基线更新或告警。 |
| 2 | **评估数据集是静态代码** | 数据集写死在 `.py` 文件中，修改用例需要改代码。对于非技术用户不友好，但对当前单开发者场景够用。 |
| 3 | **无A/B测试和灰度发布** | 理论文档强调上线后的A/B测试和渐进式放量，但由于项目是桌面应用(SQLite + pywebview)，这些概念在此场景下不适用。如果未来改为SaaS架构，需要重新设计。 |

### 2.3 暂未实现的功能

| 功能 | 原因 |
|------|------|
| **人工评估接口** | 计划Phase 7但暂缓。当前离线评估的LLMJudge评分已能满足开发阶段需求。后续需要时可在EvaluationPanel中增加人工review功能。 |
| **评估调度自动化** | EvalRunner需手动触发(点击"Run Evaluation"按钮)。未接入AgentScheduler定时执行，因为评估运行需要LLM调用(有成本)，不适合无脑定时跑。建议后续在"代码提交前"的CI流程中集成。 |
| **前端评估趋势图** | EvaluationPanel目前展示单次运行结果，不支持多运行的趋势对比图(如折线图显示质量变化)。后续可接入ECharts展示。 |
| **WorkerResult.confidence 动态化** | 目前WorkerResult的confidence是硬编码的(0.8/0.85/0.95)，不是LLM自评的。改造需要让Worker在返回前调用LLM自评，增加一次LLM调用开销。 |

---

## 三、后续开发计划

### 短期 (下次会话可做)

1. **精确Token追踪**: 改造 `WorkerBase._call_llm()` 统一从 `LLMResponse.tokens_used` 获取真实token数，替换字符估算
2. **基线自动重建**: 在 `AgentScheduler` 每日tick中增加 `Monitor.rebuild_baseline()` 调用
3. **评估趋势图**: 在 EvaluationPanel 增加 ECharts 折线图，显示最近N次评估的趋势
4. **监控摘要看板**: 在观察→指标tab中集成 `/monitor/summary` 数据(质量趋势/异常告警/成本曲线)

### 中期

5. **评估调度集成**: 在 `pyproject.toml` 的 CI步骤中增加 `venv/Scripts/python -m pytest backend/agent/evaluation/` 一键评估
6. **安全扫描升级**: 接入内容安全API(如OpenAI moderation API)作为正则扫描的补充
7. **异常自动响应**: Monitor检测到critical异常时自动触发通知(已有Notifier插件)→暂停自动执行→记录事件
8. **Worker confidence动态化**: 让每个Worker在执行后调用一次轻量LLM自评，替换硬编码confidence

### 长期

9. **在线-离线评估打通**: 当Monitor检测到在线质量下降时，自动触发EvalRunner重新评估相关Worker
10. **A/B模型对比**: 利用PluginRegistry的热插拔特性，让两个LLM模型并行处理同一请求，自动对比质量
11. **用户反馈回路**: 在对话界面添加"赞/踩"按钮，收集用户反馈作为质量信号的补充来源

---

## 四、关键文件速查

### 评估核心

| 文件 | 关键内容 |
|------|---------|
| `backend/agent/evaluation/judge.py` | LLMJudge 三种评分模式, JSON解析容错 |
| `backend/agent/evaluation/runner.py` | EvalRunner 评估流水线编排 |
| `backend/agent/evaluation/gates.py` | ReleaseGate 闸门检查 |
| `backend/agent/evaluation/datasets/` | 6个Worker的36个评估用例 |
| `backend/agent/evaluation/evaluators/` | 5类组件评估器 |

### 监控核心

| 文件 | 关键内容 |
|------|---------|
| `backend/agent/observability/safety.py` | SafetyScanner 安全扫描规则 |
| `backend/agent/observability/quality_sampler.py` | QualitySampler 质量抽样评分 |
| `backend/agent/observability/monitor.py` | Monitor 基线+异常检测算法 |
| `backend/agent/orchestrator.py` | 监控钩子插入点 (Step 5.6) |

### 规格与合约

| 文件 | 内容 |
|------|------|
| `contracts/agent-evaluation-spec.md` | 评估系统规格 |
| `contracts/agent-evaluation-adr.md` | 6个架构决策记录 |
| `contracts/agent-observability-ui-design.md` | 可观测性UI设计(已有) |
| `contracts/goal-achievement-level3-spec.md` | Level3评估规划(已实现) |

### 前端

| 文件 | 内容 |
|------|---------|
| `frontend/src/components/agent/observe/EvaluationPanel.vue` | 评估看板 |
| `frontend/src/composables/useEvaluation.ts` | 评估状态管理 |
| `frontend/src/composables/useAgent.ts` | 监控捕获 (messages[].monitoring + monitorSummary) |
| `frontend/src/components/agent/AgentPanel.vue` | 监控芯片 + 底部摘要 |

---

## 五、开箱即用检查清单

新会话拿到项目后，按以下顺序验证:

```bash
# 1. 全部测试必须通过
venv/Scripts/python -m pytest tests/ -v
# 预期: 124 passed

# 2. 前端构建必须成功
cd frontend && npm run build
# 预期: built in Xs

# 3. 启动应用后访问评估看板
# 路径: Agent Panel → 观察tab → 评估tab
# 点击"Run Evaluation"观察是否能正常运行

# 4. 查看在线监控
# 路径: Agent Panel → 观察tab → 指标tab
# 每条对话下方应有 [S100] [Qx.x] [~xxxt] 芯片
```

---

## 六、架构变化总览

```
Before (本次会话前):                    After (本次会话后):

backend/agent/                          backend/agent/
├── orchestrator.py                     ├── orchestrator.py ← 监控钩子
├── workers/                            ├── workers/
├── observability/                      ├── observability/
│   ├── tracer.py                       │   ├── tracer.py ← token追踪
│   └── metrics.py                      │   ├── metrics.py ← token聚合
│                                       │   ├── quality_sampler.py ← NEW
│                                       │   ├── safety.py ← NEW
│                                       │   └── monitor.py ← NEW
│                                       └── evaluation/ ← NEW 完整模块
│                                           ├── judge.py (LLM-as-Judge)
│                                           ├── rubric.py / bias.py
│                                           ├── dataset.py / datasets/
│                                           ├── evaluators/ (5个评估器)
│                                           ├── runner.py (EvalRunner)
│                                           └── gates.py / default_gates.py
│
tests/                                  tests/
├── test_workers.py (15测试)            ├── test_workers.py (不变)
│                                       ├── test_evaluation_judge.py (34) ← NEW
│                                       ├── test_evaluation_datasets.py (21) ← NEW
│                                       ├── test_evaluation_evaluators.py (17) ← NEW
│                                       ├── test_evaluation_runner.py (20) ← NEW
│                                       └── test_observability_monitor.py (17) ← NEW

contracts/                              contracts/
├── agent-architecture.md               ├── agent-evaluation-spec.md ← NEW
├── api-spec.md                         ├── agent-evaluation-adr.md ← NEW
│                                       ├── api-spec.md (更新: +评估API)

frontend/src/                           frontend/src/
├── api/agent.ts                        ├── api/agent.ts (更新: +评估+监控类型)
├── composables/                        ├── composables/
│   ├── useAgent.ts                     │   ├── useAgent.ts (更新: +监控捕获)
│   └── useObserve.ts                   │   ├── useObserve.ts
│                                       │   └── useEvaluation.ts ← NEW
└── components/agent/observe/           └── components/agent/observe/
    ├── ObservePanel.vue                    ├── ObservePanel.vue (更新: +评估tab)
    ├── TraceWaterfall.vue                  └── EvaluationPanel.vue ← NEW
    ├── AgentTopology.vue
    └── MetricsDashboard.vue
```

---

## 七、知识链接

本会话的实现参考了以下理论和方法论:

1. **Agent评估全流程理论** → `超细致Agent评估全流程讲解及面试真题解析_原文.md`
   - EDD 评估驱动开发理念
   - 三把通用武器 (LLM-as-Judge / Code Evaluation / Human Evaluation)
   - 全生命周期: 模型选型 → 组件评估 → 集成测试 → Pipeline → 发布闸门 → 上线监控

2. **Google Agent Bake-Off / AI Engineering** → Harness工程模式
3. **美团龙猫论文** → 多轮Agent交互评估方法、固定环境+目标+评分标准
4. **Google Gemini Judge Cookbook** → LLM-as-Judge偏差缓解 (位置/冗长/自我强化)
5. **可观测性三支柱** → Logs + Traces + Metrics → Dashboard + Alerting
