# self-grow — 自我成长智能助手

> 一个具备秘书级自主能力的 AI 个人助手。从品质追踪到多 Agent 编排，从被动响应到主动提醒。

## 架构

```
┌──────────────────────────────────────────────────────┐
│                    Vue 3 前端                         │
│  Dashboard │ Qualities │ DailyInput │ Report         │
│              AgentPanel (右下角悬浮)                   │
├──────────────────────────────────────────────────────┤
│                  FastAPI (39 端点)                     │
├──────────────────────────────────────────────────────┤
│            Orchestrator (Supervisor-Worker)            │
│  ┌──────────┬──────────┬──────────┬──────────┬─────┐ │
│  │ Searcher │ Profiler │ Executor │GoalDecomp│Coach│ │
│  │ 多源检索  │ 画像+差距 │ 日程写入  │ 目标分解  │CBT  │ │
│  └──────────┴──────────┴──────────┴──────────┴─────┘ │
├──────────────────────────────────────────────────────┤
│  MotivationEngine    PriorityEngine    Scheduler      │
│  目标压力扫描         紧急度评估        20分钟定时      │
├──────────────────────────────────────────────────────┤
│  Memory: Hot(上下文) / Warm(SQLite) / Cold(Markdown)  │
│  MCP Client ──→ 外部 RAG 知识库                       │
└──────────────────────────────────────────────────────┘
```

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.12+ / FastAPI / SQLAlchemy / SQLite |
| AI | DeepSeek API / Qwen3-TTS / MCP SDK / CBT 框架 |
| 前端 | Vue 3 / Vite / ECharts / Tailwind CSS |
| Agent | Supervisor-Worker / 8 字段 TaskBrief / 三层记忆 |
| 桌面 | pywebview / PyInstaller → .exe |
| 测试 | pytest / pytest-asyncio (15 tests) |

## 快速开始

```bash
# 1. 安装依赖
python -m venv venv
venv\Scripts\pip install -r backend/requirements.txt
cd frontend && npm install && npm run build && cd ..

# 2. 配置 API Key
# 编辑 agent-config.yaml，填入 DeepSeek 和 Qwen 的 API Key

# 3. 启动
venv\Scripts\python run.py
# 访问 http://127.0.0.1:8000
```

## 运行测试

```bash
venv\Scripts\python -m pytest tests/ -v
# 15 passed ✓
```

## 核心设计决策

### 为什么 Supervisor-Worker 而不是 Peer-to-Peer

2026 年五大厂商（Anthropic/OpenAI/Microsoft/Google/LangChain）全部收敛到 Supervisor-Worker。Peer-to-Peer GroupChat 因 O(n²) 通信爆炸和 17.2× 错误放大已被淘汰。

### 为什么 TaskBrief 是 8 字段

对齐 2026 行业标准：发给谁(task_id)、做什么(objective)、在什么范围(context/constraints)、用什么标准(expected_format/output_schema)、容错参数(max_retries/timeout_seconds)。新增 Worker 不改协议。

### 为什么记忆分三层

不同类型的信息衰减速度不同。Hot 层处理当前对话（~4096 tokens），Warm 层存结构化数据（跨会话可查），Cold 层存 Markdown 知识（永久可读）。MicroCompact 在 Hot 和 Warm 之间做零 LLM 成本的压缩。

### 为什么 MotivationEngine 用压力累积而不是定时提醒

参考 NeoPsyke (2026) 的 Id-Ego-Superego 模型：目标越临近 deadline、进度越落后 → pressure 越高 → 提醒升级（正常→紧急→语音播报）。提醒 3 次未处理后自动升级。

### 为什么 MCP 按需调用而不是每次调用

Searcher 先查本地 DB + 知识库，结果不足 3 条或任务含"文档/知识库"关键词时才通过 stdio 子进程调外部 RAG MCP Server。避免无关查询浪费外部 API 调用。

## 目录结构

```
self-grow/
├── backend/
│   ├── agent/              # Agent 核心
│   │   ├── orchestrator.py # Supervisor-Worker 编排
│   │   ├── motivation_engine.py  # 自主动机引擎
│   │   ├── workers/        # 5 个 Worker
│   │   └── plugins/        # LLM/TTS/Priority/Notify
│   ├── routers/            # API 路由
│   ├── models.py           # 12 张数据表
│   └── main.py             # FastAPI 入口
├── frontend/src/           # Vue 3 前端
├── contracts/              # 架构文档
├── tests/                  # pytest 测试
├── data/                   # 用户数据 + 记忆
└── agent-config.yaml       # 配置文件
```

## License

MIT
