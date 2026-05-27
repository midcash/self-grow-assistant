# 个人日程智能体 — 架构设计文档 v2

> 成熟度: 🟢 稳定 — Harness + 插件体系已在实际开发中验证，4 个插件均可替换。


> 基于 2026 年 5 月主流实践：Google Agent Bake-Off、LangChain Harness Engineering、
> Open-LLM-VTuber、Persona Engine v3.0.2、华为云 Agent Harness Infra 等

---

## 零、2026 行业共识

```
Agent = Model（大脑） + Harness（操作系统）

Harness 负责：编排、调度、记忆、工具治理、预算控制、可观测性
Model 只是"计算单元"，Harness 才是生产级的关键
```

**LangChain 生产数据证明**：仅优化 Harness（不换模型），可将系统从 top-30 提升到 top-5。

---

## 一、总体架构（四层）

```
┌──────────────────────────────────────────────────────────────┐
│  Layer 4 — 表现层 (Presentation)                              │
│  ┌──────────────────┐  ┌──────────────────┐                  │
│  │ Live2D 悬浮形象    │  │ Agent Panel 面板  │                  │
│  │ (pixi-live2d)    │  │ (Vue 3 组件)      │                  │
│  │ · 表情系统        │  │ · 对话/设置/列表   │                  │
│  │ · 口型同步        │  │ · 语音波形         │                  │
│  └──────────────────┘  └──────────────────┘                  │
├──────────────────────────────────────────────────────────────┤
│  Layer 3 — 智能体核心 (Agent Core)                            │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              Agent Harness (线束层)                    │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │    │
│  │  │Plugin    │ │Event     │ │Lifecycle │ │Context   │ │    │
│  │  │Registry  │ │Bus       │ │Manager   │ │Optimizer │ │    │
│  │  │(工厂模式) │ │(发布订阅) │ │(热插拔)   │ │(Token预算)│ │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └─────────┘ │    │
│  └──────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │           插件层 (Plugin Layer) — Factory + Interface  │    │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │    │
│  │  │LLM     │ │TTS     │ │Priority│ │Notifier│        │    │
│  │  │Adapter │ │Engine  │ │Engine  │ │Engine  │        │    │
│  │  │Factory │ │Factory │ │Factory │ │Factory │        │    │
│  │  └────────┘ └────────┘ └────────┘ └────────┘        │    │
│  └──────────────────────────────────────────────────────┘    │
├──────────────────────────────────────────────────────────────┤
│  Layer 2 — 记忆层 (Memory)                                    │
│  ┌────────────┐ ┌────────────┐ ┌────────────────────┐       │
│  │ Hot Memory │ │ Warm Memory│ │ Cold Memory         │       │
│  │ (上下文窗口)│ │ (SQLite)   │ │ (Markdown 知识库)   │       │
│  │ 当前对话    │ │ 任务/品质   │ │ digest/ + wiki/     │       │
│  └────────────┘ └────────────┘ └────────────────────┘       │
├──────────────────────────────────────────────────────────────┤
│  Layer 1 — 基础设施 (Infrastructure)                          │
│  FastAPI + SQLite + APScheduler + pywebview                  │
└──────────────────────────────────────────────────────────────┘
```

---

## 二、Harness 核心设计（12 组件精简为 6 核心）

针对桌面应用场景，从 Google 12 组件模型中精选 6 个核心：

### 2.1 PluginRegistry（插件注册中心）— Factory 模式

```python
class PluginRegistry:
    """工厂模式 + 接口契约，参考 Open-LLM-VTuber 的 Factory 模式"""

    def __init__(self):
        self._plugins: dict[str, PluginBase] = {}
        self._factories: dict[str, type[PluginBase]] = {}

    def register_factory(self, capability: str, factory: type[PluginBase]):
        """注册插件工厂"""

    def create(self, capability: str, config: dict) -> PluginBase:
        """工厂方法创建插件实例"""

    def get(self, capability: str) -> PluginBase:
        """获取已加载的插件"""

    def hot_swap(self, capability: str, new_plugin: PluginBase):
        """热替换：先加载新插件，成功后再卸载旧插件"""
```

### 2.2 EventBus（事件总线）— 发布订阅 + 故障隔离

```python
class EventBus:
    """异步事件总线，参考 2026 最佳实践：故障隔离"""

    def __init__(self):
        self._subscribers: dict[str, list[callable]] = {}
        self._circuit_breakers: dict[str, CircuitBreaker] = {}

    async def publish(self, event: Event):
        """发布事件，单个订阅者失败不影响其他"""

    def subscribe(self, event_type: str, handler: callable):
        """订阅事件"""

    # 内置事件类型：
    # "priority.changed"    — 任务优先级发生变化
    # "task.deadline_near"  — 任务临近截止
    # "user.idle"           — 用户长时间未操作
    # "agent.error"         — 智能体异常
```

### 2.3 LifecycleManager（生命周期管理）— 热插拔

```python
class LifecycleManager:
    """管理所有插件的加载/卸载/健康检查"""

    async def load_all(self, config: dict) -> dict[str, bool]:
        """按依赖顺序加载所有插件"""

    async def health_check(self) -> dict[str, bool]:
        """定期健康检查（每 5 分钟）"""

    async def shutdown(self):
        """优雅关闭：反向依赖顺序卸载"""
```

### 2.4 ContextOptimizer（上下文优化器）— Token 预算

```python
class ContextOptimizer:
    """Token 预算控制，参考 Google 2026 四区模型"""

    # 绿区 (>50%): 正常执行
    # 黄区 (20-50%): 压缩上下文，语义摘要
    # 红区 (5-20%): 切换到轻量模型，跳过深度推理
    # 熔断区 (<5%): 强制收束，返回部分结果

    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens

    def optimize(self, messages: list) -> list:
        """压缩消息列表到预算内"""

    def should_use_heavy_model(self) -> bool:
        """判断是否可以使用重量级模型"""
```

### 2.5 ErrorHandler（错误处理器）— 断路器

```python
class ErrorHandler:
    """故障分类 + 断路器 + 优雅降级"""

    def classify(self, error: Exception) -> ErrorType:
        """分类：ModelError / NetworkError / PluginError / InternalError"""

    def handle(self, error: Exception, context: dict) -> FallbackAction:
        """根据错误类型返回降级策略"""
        # ModelError → 切换备选模型
        # NetworkError → 指数退避重试
        # PluginError → 隔离故障插件
        # InternalError → 记录 + 通知用户
```

### 2.6 ConfigLoader（配置驱动）— YAML 配置

```python
# agent-config.yaml
agent:
  name: "自我成长助手"
  cron: "*/20 * * * *"  # 每 20 分钟评估

plugins:
  llm:
    default: "deepseek"
    deepseek:
      api_base: "${DEEPSEEK_API_BASE}"
      api_key: "${DEEPSEEK_API_KEY}"
      model: "deepseek-v4-pro"
      max_tokens: 4096

  tts:
    default: "qwen"
    fallback: "edge"
    qwen:
      api_key: "${QWEN_API_KEY}"
      voice: "zh-CN-XiaoxiaoNeural"

  priority:
    urgency_lambda: 0.15      # 紧急度衰减系数
    long_task_factor: 2.0     # 长任务保护系数
    algorithm_weight: 0.6     # 算法权重
    llm_weight: 0.4           # LLM 权重

memory:
  hot_max_tokens: 4096
  warm_db_path: "data/self-grow.db"
  cold_path: "data/agent-memory/"
```

---

## 三、插件体系（Factory + Abstract Interface）

```
backend/agent/plugins/
│
├── llm_adapter/                    # LLM 适配器
│   ├── base.py                    # interface: chat(), stream(), classify_urgency()
│   ├── factory.py                 # LLMFactory: 按配置创建实例
│   ├── deepseek_v4.py             # DeepSeek V4 Pro
│   └── qwen.py                    # 通义千问 (备选)
│
├── tts_engine/                    # TTS 语音引擎
│   ├── base.py                    # interface: synthesize(text) -> bytes
│   ├── factory.py                 # TTSFactory
│   ├── qwen_tts.py                # Qwen3-TTS (主力)
│   └── edge_tts.py                # Edge TTS (备份)
│
├── priority_engine/               # 优先级评估
│   ├── base.py                    # interface: evaluate(tasks) -> ScoredTask[]
│   ├── factory.py                 # PriorityFactory
│   └── weighted_scorer.py         # 加权算法 + LLM 辅助
│
└── notifier/                      # 通知推送
    ├── base.py                    # interface: notify(alert) -> bool
    ├── factory.py                 # NotifierFactory
    ├── voice_alert.py             # TTS 语音提醒
    └── desktop_toast.py           # Windows Toast 通知
```

### 插件基类（参考 2026 主流设计）

```python
class PluginBase(ABC):
    """插件契约 — 所有插件必须实现"""

    # === 元数据 ===
    manifest: PluginManifest  # name, version, author, capabilities, config_schema

    # === 生命周期 ===
    async def on_load(self, config: dict) -> None: ...
    async def on_unload(self) -> None: ...
    async def health_check(self) -> bool: ...

    # === 能力声明 ===
    def capabilities(self) -> list[str]: ...

    # === 错误恢复 ===
    async def on_error(self, error: Exception) -> RecoveryAction: ...
```

---

## 四、优先级评估引擎（核心算法）

### 4.1 算法公式

```python
# 最终优先级 = 紧急度 × 重要性 × 长任务保护 × 时间衰减

urgency = e^(-λ × hours_until_deadline)
# λ = 0.15 (约 4.6 小时后紧急度减半)
# 距面试 1 小时 → 0.86
# 距面试 8 小时 → 0.30

importance = user_set_priority / 10  # 用户手动设定 1-10

long_task_protection = 1 + (1 - today_progress/today_quota) × 2
# 今日配额未完成 → 权重最大 3x
# 完成超过配额 → 保持 1x

time_decay = 1.0 / (1 + 0.01 × hours_since_created)
# 新任务不受影响，旧任务轻微衰减

final_score = urgency × importance × long_task_protection × time_decay
```

### 4.2 双通道评估（算法 + LLM 加权）

```
算法通道 (权重 0.6)              LLM 通道 (权重 0.4)
┌──────────────────┐          ┌──────────────────┐
│ 公式计算          │          │ DeepSeek V4 Pro    │
│ · 确定性          │          │ · 理解语义上下文    │
│ · 低延迟          │          │ · 发现隐含依赖      │
│ · 无成本          │          │ · 处理模糊情况      │
└──────────────────┘          └──────────────────┘
         │                            │
         └──────────┬─────────────────┘
                    ▼
            ┌──────────────┐
            │ 加权平均排序   │
            │ score > 0.7  │──→ 触发语音提醒
            │ score > 0.4  │──→ 角标提示
            │ score < 0.4  │──→ 静默记录
            └──────────────┘
```

### 4.3 长任务保护机制

采用 2026 年 TaskFlow-AI 和 personal-os 验证的模式：

```
论文初稿 (后天 23:59 截止)
├── 每日配额: 500 字
├── 今日完成: 100 字 → 完成率 20%
├── long_task_protection = 1 + (1 - 0.2) × 2 = 2.6x
└── 即使有其他紧急任务，论文也会保持可见的优先级

vs.

求职学习 (每天 2 小时)
├── 今日完成: 1.5 小时 → 完成率 75%
├── long_task_protection = 1 + (1 - 0.75) × 2 = 1.5x
└── 适度提权，但不会过度挤占其他任务
```

---

## 五、Live2D 管线（参考 Persona Engine v3.0.2）

```
┌─────────────────────────────────────────────────────────┐
│  Live2D 渲染管线 (前端)                                    │
│                                                         │
│  用户点击/语音 → Agent API → LLM 回复                      │
│       │                                                  │
│       ▼                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐           │
│  │ 文本解析  │ →  │ 情感标签  │ →  │ TTS 合成 │           │
│  │          │    │ [EMOTION] │    │ 音频输出 │           │
│  └──────────┘    └──────────┘    └──────────┘           │
│       │               │                │                │
│       ▼               ▼                ▼                │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐           │
│  │ 对话气泡  │    │ 表情切换  │    │ 口型同步  │           │
│  │ 显示文本  │    │ 开心/担心 │    │ 音频驱动  │           │
│  └──────────┘    └──────────┘    └──────────┘           │
│                                                         │
│  支持的表情标签：                                          │
│  [HAPPY] [WORRIED] [URGENT] [CALM] [THINKING] [ENCOURAGE]│
└─────────────────────────────────────────────────────────┘
```

### 悬浮层设计

```vue
<!-- App.vue -->
<template>
  <router-view />
  <!-- 全局悬浮，所有页面可见 -->
  <Live2DAvatar
    class="fixed bottom-4 right-4 z-50"
    :model="defaultModel"
    @click="togglePanel"
  />
  <AgentPanel v-if="panelVisible" @close="panelVisible = false" />
</template>
```

---

## 六、记忆系统（三层）

参考 2026 年 GBrain + personal-os 模式：

```
~/.agent-memory/              (实际路径: data/agent-memory/)
├── digest/                   # 每日任务摘要（自动生成）
│   └── 2026-05-13.md         # 今日完成/未完成/优先级变化
├── wiki/                     # 知识页面（同主题合并）
│   ├── habits.md             # 用户习惯分析
│   └── patterns.md           # 任务完成模式
├── domain/                   # 四域分类
│   ├── conversational/       # 对话历史摘要
│   ├── personal/             # 用户个人信息
│   ├── agent/                # Agent 自身状态
│   └── task/                 # 任务相关知识
└── index.md                  # 倒排索引

三层对应：
  Hot  (热)  → 当前对话上下文 (内存, 最大 4096 tokens)
  Warm (温)  → SQLite 结构化数据 (已有, todo_items + quality_progress)
  Cold (冷)  → Markdown 知识库 (新增, agent-memory/)
```

---

## 七、API 设计

```
# 智能体核心
GET    /api/v1/agent/status              # 智能体状态（插件列表 + 健康）
POST   /api/v1/agent/chat                # 对话（慌张时求最优解）
POST   /api/v1/agent/chat/stream         # 流式对话 (SSE)

# 优先级评估
POST   /api/v1/agent/evaluate            # 手动触发评估
GET    /api/v1/agent/tasks/priority      # 排序后的任务列表

# TTS 语音
POST   /api/v1/agent/tts                 # 文字转语音 → 返回音频流

# 调度控制
GET    /api/v1/agent/schedule/status     # 调度器状态
POST   /api/v1/agent/schedule/toggle     # 开关定时评估
PUT    /api/v1/agent/schedule/cron       # 修改 cron 表达式

# 记忆
GET    /api/v1/agent/memory/digest       # 获取今日摘要
GET    /api/v1/agent/memory/digest/{date}# 获取指定日期摘要
```

---

## 八、数据模型扩展

在现有 `backend/models.py` 基础上新增：

```python
class AgentTaskPriority(Base):
    """智能体任务优先级快照"""
    __tablename__ = "agent_task_priorities"
    id, todo_id, urgency_score, importance_score,
    final_score, llm_reasoning, evaluated_at

class AgentConversation(Base):
    """智能体对话历史"""
    __tablename__ = "agent_conversations"
    id, role (user/agent), content, emotion_tag,
    created_at

class AgentMemoryDigest(Base):
    """每日摘要（对应 cold memory digest/）"""
    __tablename__ = "agent_memory_digests"
    id, date, summary, completed_count,
    pending_count, top_priority_task, created_at
```

---

## 九、目录结构（最终）

```
self-grow/
├── backend/
│   ├── agent/                        # 新增：智能体模块
│   │   ├── __init__.py
│   │   ├── harness.py                # Harness 线束核心
│   │   ├── plugin_base.py            # 插件抽象契约
│   │   ├── plugin_registry.py        # 注册中心 (Factory 模式)
│   │   ├── event_bus.py              # 异步事件总线
│   │   ├── lifecycle.py              # 生命周期管理
│   │   ├── context_optimizer.py      # Token 预算控制
│   │   ├── error_handler.py          # 错误处理 + 断路器
│   │   ├── scheduler.py              # APScheduler 定时调度
│   │   ├── config.py                 # 配置加载器 (YAML)
│   │   └── plugins/
│   │       ├── __init__.py
│   │       ├── llm_adapter/
│   │       │   ├── __init__.py
│   │       │   ├── base.py
│   │       │   ├── factory.py
│   │       │   ├── deepseek_v4.py
│   │       │   └── qwen.py
│   │       ├── tts_engine/
│   │       │   ├── __init__.py
│   │       │   ├── base.py
│   │       │   ├── factory.py
│   │       │   ├── qwen_tts.py
│   │       │   └── edge_tts.py
│   │       ├── priority_engine/
│   │       │   ├── __init__.py
│   │       │   ├── base.py
│   │       │   ├── factory.py
│   │       │   └── weighted_scorer.py
│   │       └── notifier/
│   │           ├── __init__.py
│   │           ├── base.py
│   │           ├── factory.py
│   │           ├── voice_alert.py
│   │           └── desktop_toast.py
│   ├── routers/
│   │   └── agent.py                  # 智能体 API 路由
│   └── models.py                     # 扩展：新增 3 个模型
│
├── frontend/src/
│   ├── App.vue                       # 修改：添加 Live2DAvatar
│   ├── components/agent/
│   │   ├── Live2DAvatar.vue          # 悬浮 Live2D 形象
│   │   ├── AgentPanel.vue            # 展开面板
│   │   ├── VoiceWave.vue             # 语音波形动画
│   │   ├── EmotionBadge.vue          # 紧急任务角标
│   │   └── PriorityList.vue          # 优先级任务列表
│   ├── api/
│   │   └── agent.ts                  # 智能体 API 封装
│   └── composables/
│       └── useAgent.ts               # 智能体组合式函数
│
├── contracts/
│   ├── agent-architecture.md         # 本文档
│   └── agent-plugin-spec.md          # 插件契约规范
│
├── agent-config.yaml                 # 智能体配置文件
└── data/agent-memory/                # 冷记忆存储
```

---

## 十、开发路线图

| Phase | 内容 | 文件数 | 预计产出 |
|-------|------|--------|---------|
| **P1** Harness 核心 | plugin_base, registry, event_bus, lifecycle, config | 6 | 插件框架可运行 |
| **P2** LLM + TTS 插件 | deepseek_v4, qwen_tts, edge_tts + factories | 8 | 可对话、可语音 |
| **P3** 优先级引擎 | weighted_scorer, notifier, scheduler | 5 | 定时评估 + 语音提醒 |
| **P4** API + 数据模型 | agent router, models 扩展 | 2 | 前后端联通 |
| **P5** 前端 Live2D | Avatar, Panel, Wave, Badge, PriorityList, API | 6 | 可视交互 |
| **P6** 集成测试 | pytest + vite build + exe 打包 | - | 全链路通过 |

---

## 十一、与 2026 主流实践的符合度

| 2026 主流实践 | 本架构 | 状态 |
|-------------|--------|------|
| Agent = Model + Harness | Harness 作为独立线束层 | 符合 |
| Factory + Interface 插件模式 | PluginRegistry + Factory | 符合 |
| MCP 工具协议 | 预留 MCP 接口，Phase 4 实现 | 预留 |
| 三层记忆 (hot/warm/cold) | 上下文 + SQLite + Markdown | 符合 |
| Token 预算控制 | ContextOptimizer 四区模型 | 符合 |
| 断路器 + 故障隔离 | ErrorHandler + EventBus 隔离 | 符合 |
| 配置驱动 (YAML) | agent-config.yaml | 符合 |
| Emotion Tag → Live2D 表情 | [HAPPY]/[URGENT] 等标签 | 符合 |
| 双通道评估 (规则+LLM) | 算法 0.6 + LLM 0.4 | 符合 |
| HITL 人机协作 | 高风险操作需确认 | 预留 |
| EvalOps 质量飞轮 | Phase 6+ 引入 | 后续 |
