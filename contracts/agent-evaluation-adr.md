# ADR: Agent评估系统架构决策

> 决策日期: 2026-07-02
> 触发背景: 用户识别到项目违背"先评估后部署"原则，要求补齐Agent评估体系
> 状态: 已采纳

---

## 决策背景

当前项目有完善的Agent多智能体架构和可观测性，但`contracts/goal-achievement-level3-spec.md`中规划的评估系统（AgentEvaluationRun模型、EvalRunner、评估用例）从未实现。

用户提供了一份Agent评估理论文档，阐述了从EDD到上线监控的完整生命周期方法论，并指出当前项目"可观测性(上线后)显著领先于评估(上线前)"的倒挂问题。

触发决策的核心问题：**如何在不破坏现有架构的前提下，建立完整的Agent评估体系？**

---

## 决策1: 评估模块独立于可观测性模块

### 选项

| 选项 | 描述 |
|------|------|
| A: 扩展observability | 在现有的`backend/agent/observability/`中添加评估逻辑 |
| B: 新建evaluation模块 | 在`backend/agent/evaluation/`独立建模块 |
| C: 评估逻辑内嵌各Worker | 每个Worker自带评估方法 |

### 决策: 选项B — 新建独立模块

### 论证

- **职责分离**: 可观测性是**被动采集**（记录生产Trace），评估是**主动测试**（构造用例→运行→打分）。两者数据结构不同（Trace Span vs EvalScore），不应混淆
- **Google Agent Bake-Off模式**: 评估是独立于生产的离线行为，建议独立模块
- **SOLID原则**: observability模块不需要因为评估需求而膨胀。Observability捕捉运行时行为，Evaluation衡量离线质量
- **选项C不可行**: Worker职责是执行业务逻辑，评估是对Worker行为的元判断，不应耦合
- **选项A不够**: 扩展observability会导致模块职责不清，未来维护困难

### 后果

- 简化: 两个模块各自独立演进，评估模块可以有自己的DB表、API路由、前端组件
- 复杂化: 评估结果同时写入TraceCollector（集成到现有可观测性看板），需要在runner中调用tracer API

---

## 决策2: LLM-as-Judge复用现有LLM插件

### 选项

| 选项 | 描述 |
|------|------|
| A: 新建独立Judge模型 | 部署一个专门用于评估的模型 |
| B: 复用现有LLM插件 | LLMJudge使用同一个DeepSeek/Qwen适配器 |
| C: 纯规则评估 | 只用基于代码的断言，不用LLM judge |

### 决策: 选项B — 复用现有LLM插件

### 论证

- **资源约束**: 桌面应用不应强制用户部署第二个模型
- **实践验证**: Google Gemini、OpenAI GPT-4作为裁判与人类一致性>85%，是行业标准方法
- **低温度可分离**: judge调用使用temperature=0.2（与Worker的temperature=0.7区分），确保评分一致性
- **选项C不足**: 开放式Agent输出（如Coach的CBT辅导）无法用纯规则判断好坏

### 后果

- 简化: 无需新的模型部署、API配置、插件开发
- 风险: judge和worker使用同一模型，存在self-enhancement bias（模型倾向给自己的输出高分）。缓解: prompt中明确"你正在评估另一个系统的输出，保持客观"，deviation > 1.0分时降级处理

---

## 决策3: 评估数据集以Python代码定义

### 选项

| 选项 | 描述 |
|------|------|
| A: Python模块 | 数据集定义为.py文件中的EvalExample列表 |
| B: JSON/YAML文件 | 数据集定义为静态配置文件 |
| C: 数据库存储 | 数据集存储在AgentEvalDataset表中 |

### 决策: 选项A — Python模块

### 论证

- **版本控制**: Python代码随Worker一起提交，数据集和Worker同步更新
- **类型安全**: EvalExample是dataclass，IDE可检查字段拼写
- **灵活性**: 可以在数据集中使用TaskBrief对象、lambda断言、动态生成用例
- **与Worker代码共存**: datasets/searcher.py和workers/searcher.py在同一仓库，修改Worker时自然记得更新数据集
- **选项B局限**: JSON无法表达复杂类型（TaskBrief对象、函数断言）
- **选项C局限**: 数据库数据容易和生产数据混淆，且不易版本控制

### 后果

- 简化: 数据集是代码，pytest直接import运行
- 后果: 非技术人员无法编辑数据集（但本项目为单开发者项目，无此需求）

---

## 决策4: 评估器使用Evaluator模式而非策略模式

### 选项

| 选项 | 描述 |
|------|------|
| A: Evaluator模式 | 每个评估维度是独立的Evaluator类（PromptEvaluator, RAGEvaluator...） |
| B: 策略模式 | 单个Evaluator类通过注入策略函数切换行为 |
| C: 单一类+switch | 一个Evaluator类通过eval_type参数分支 |

### 决策: 选项A — Evaluator模式

### 论证

- **开闭原则**: 新增评估维度只需新增一个Evaluator类，不需修改现有代码
- **多态替换**: EvalRunner通过工厂方法`_get_evaluator(component)`统一调度，所有Evaluator实现相同的BaseEvaluator接口
- **独立测试**: 每个Evaluator可独立单元测试，mock其依赖
- **选项B**: 策略函数太多会导致参数爆炸
- **选项C**: switch分支会随着评估维度增加而膨胀

### 后果

- 简化: 新增评估维度零侵入现有代码
- 复杂化: 需要维护BaseEvaluator抽象接口（但接口本身简单，只有evaluate和evaluate_batch两个方法）

---

## 决策5: 两阶段发布闸门(smoke + release)

### 选项

| 选项 | 描述 |
|------|------|
| A: 单级闸门 | 一个固定的通过/不通过阈值 |
| B: 两级闸门 | smoke(快速,低阈值) + release(完整,高阈值) |
| C: 无闸门 | 只出分数,不设闸门 |

### 决策: 选项B — 两级闸门

### 论证

- **开发流程匹配**: smoke用于日常开发快速验证(3分钟内), release用于发布前完整检查
- **Smoke Gate**: prompt.avg_score >= 3.0, tool_call.pass_rate >= 0.8
- **Release Gate**: prompt >= 4.0, rag >= 0.9, reasoning >= 3.5, tool_call >= 0.9
- **选项A**: 固定阈值过严则日常开发太慢，过松则失去意义
- **选项C**: 无闸门则评估失去强制力

### 后果

- 简化: 开发者和发布流程都有明确的量化标准
- 风险: 阈值需要根据实际数据校准，初期可能需要调整

---

## 决策6: API同步返回评估结果（初期）

### 选项

| 选项 | 描述 |
|------|------|
| A: 同步API | POST /evaluation/run 阻塞等待完成,直接返回EvalReport |
| B: 异步API | POST返回run_id, GET轮询状态,完成后再获取结果 |
| C: SSE流式 | 评估过程中通过SSE推送进度 |

### 决策: 选项A — 同步API（初期）

### 论证

- **数据集规模小**: 初期共约30个评估用例,LLM调用约30-50次,即使同步也<2分钟
- **实现简单**: FastAPI直接返回结果,前端无需轮询/SSE逻辑
- **开发阶段**: 评估是开发者手动触发的工具,不是用户面功能

### 后果

- 简化: 前端API调用和状态管理大幅简化
- 后续演化: 如果数据集增长到100+用例,可改为选项B(BackgroundTasks + 轮询)
