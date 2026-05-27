# 多 Agent 协作架构 — 一主多从设计 v1

> 成熟度: 🟡 实验阶段 — 5 Worker 单层编排已可用。
> 已知局限: Worker > 7 时 _plan() prompt 超出 1024 token budget。
> 触发升级: 当 Worker 数量 ≥ 7 或 _plan() 用量 > 80%，引入 MidOrchestrator 分层。


## 零、架构选型依据

基于 2026 年 5 月行业共识：
- Google DeepMind (180种配置): Supervisor-Worker 比单 Agent 强 90.2%
- Anthropic/OpenAI/Microsoft/LangChain 全部收敛到 Orchestrator-Subagent
- AWS Arbiter Pattern: Supervisor 的下一代进化（语义匹配 + 动态生成）
- 3-5 个 Agent 最优，超过 20 个劣化

选择: **轻量 Supervisor-Worker**，扩展已有 Harness，不引入重框架

## 一、总体架构

```
用户 "帮我安排明天的导游工作"
        │
        ▼
┌───────────────────────────────────────────┐
│         Orchestrator (DeepSeek)            │
│                                             │
│  1. 意图理解 + 任务分解                      │
│  2. 生成子任务 → 分发给对应 Worker            │
│  3. 汇总 Worker 结果 → 整合输出              │
├───────────────────────────────────────────┤
│                                             │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ │
│  │  Searcher  │ │ Profiler  │ │  Scheduler │ │
│  │  信息检索   │ │  个人画像   │ │  日程执行   │ │
│  │            │ │            │ │            │ │
│  │ 搜索景点   │ │ 了解偏好    │ │ 写入日程   │ │
│  │ 查餐厅     │ │ 花销水平    │ │ 创建TODO   │ │
│  │ 找路线     ｜ │ 行为习惯    │ │ 设定提醒    │ │
│  │ 联网/本地  │ │ 历史数据    │ │ 触发评估    │ │
│  └───────────┘ └───────────┘ └───────────┘ │
│                                             │
├───────────────────────────────────────────┤
│          Shared Context / Blackboard        │
│   ┌─────────┐ ┌──────────┐ ┌────────────┐ │
│   │ 用户画像  │ │ 任务状态   │ │ 对话/结果    │ │
│   │ (SQLite) │ │ (内存)    │ │ (上下文)    │ │
│   └─────────┘ └──────────┘ └────────────┘ │
└───────────────────────────────────────────┘
```

## 二、Worker Agent 定义

每个 Worker 是独立的 Agent，有专属 system prompt 和工具集:

### 1. Searcher Agent (信息检索)
- 能力: 搜索、检索、信息聚合
- 工具: WebSearch、现有数据库查询、本地知识库
- 模型: 轻量模型即可（Qwen Flash / 免费）
- 输出: 结构化信息摘要

### 2. Profiler Agent (个人画像)
- 能力: 用户偏好分析、历史数据查询、习惯推断
- 工具: SQLite 查询 (todo_items, quality_progress, 历史摘要)
- 模型: 轻量模型
- 输出: 用户偏好报告 + 约束条件

### 3. Scheduler Agent (日程执行)
- 能力: 创建日程、写入 TODO、设定提醒
- 工具: todo_items CRUD、优先级评估触发
- 模型: 无需 LLM（纯函数调用 + 规则）
- 输出: 写入确认

## 三、Orchestrator 工作流

```python
class Orchestrator:
    async def handle(self, user_message: str) -> str:
        # Step 1: 意图分析 + 任务分解
        plan = await self._decompose(user_message)
        # plan = {
        #   "intent": "travel_planning",
        #   "subtasks": [
        #     {"agent": "searcher", "query": "搜索XX城市热门景点"},
        #     {"agent": "profiler", "query": "查询用户偏好和预算"},
        #   ],
        #   "dependencies": []
        # }

        # Step 2: 并行执行独立子任务
        results = await asyncio.gather(
            self.searcher.search(plan.subtasks[0]),
            self.profiler.profile(plan.subtasks[1]),
        )

        # Step 3: 整合结果 + 生成方案
        synthesis = await self._synthesize(plan.intent, results)

        # Step 4: 可选 → 创建日程
        if plan.get("create_schedule"):
            await self.scheduler.create(synthesis.tasks)

        return synthesis.reply
```

## 四、目录结构

```
backend/agent/
├── orchestrator.py          ← 新增: 编排器核心
├── workers/                 ← 新增: Worker Agent 目录
│   ├── __init__.py
│   ├── base.py             ← Worker 基类
│   ├── searcher.py         ← 信息检索 Worker
│   ├── profiler.py         ← 个人画像 Worker
│   └── scheduler_worker.py ← 日程执行 Worker
├── harness.py              ← 已有
├── plugin_base.py          ← 已有
├── ...                     ← 已有文件不变
└── plugins/                ← 已有
```

## 五、数据流

```
POST /api/v1/agent/orchestrate
  { "message": "帮我安排明天导游工作" }
       │
       ▼
  Orchestrator.handle()
       │
       ├─→ Searcher.search("XX城市热门景点")
       │       └→ 返回: [{景点1}, {景点2}, ...]
       │
       ├─→ Profiler.profile()
       │       └→ 返回: {偏好: 历史文化, 预算: 中等, 体力: 一般}
       │
       ▼
  Orchestrator._synthesize(results)
       └→ 整合输出:
           "根据你的偏好推荐以下路线:
            上午: 故宫 (历史文化)
            中午: 老北京炸酱面 (人均50)
            下午: 颐和园 (步行适中)
            是否需要加入日程？"
       │
       ▼ (用户确认后)
  Scheduler.create(tasks)
       └→ INSERT INTO todo_items [...]
       └→ 返回确认
```

## 六、实施计划

| Phase | 内容 | 说明 |
|-------|------|------|
| **M1** Worker 基类 | base.py — 统一接口、消息协议 | 1 文件 |
| **M2** Searcher | searcher.py — 联网搜索 + 本地检索 | 1 文件 |
| **M3** Profiler | profiler.py — 用户画像 + 偏好查询 | 1 文件 |
| **M4** Orchestrator | orchestrator.py — 编排核心 | 1 文件 |
| **M5** API + 前端 | 新端点 + 聊天面板集成 | 3 文件 |
| **M6** 集成测试 | 端到端验证 | - |

总计约 7 个新文件，对现有代码无破坏性修改。
