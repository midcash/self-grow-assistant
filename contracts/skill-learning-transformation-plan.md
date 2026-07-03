# 技能学习追踪器 — 改造计划

> 决策日期: 2026-07-03
> 触发背景: 当前"自我成长可视化系统"定位过泛，多 Agent 架构优势无法充分发挥
> 改造目标: 收窄为"技能学习追踪器"，让 Supervisor-Worker 架构在长任务分析拆解场景中发挥真实价值

---

## 一、新项目 vs 改造现有项目

### 结论：改造现有项目，不开新项目

### 1.1 决策分析

| 维度 | 新项目 | 改造现有 |
|------|--------|---------|
| Agent 编排核心 | 需重写 orchestrator.py (572行) + 5 Worker + 重做集成 | 直接复用，只改 Worker prompt |
| 插件体系 | 需重写 Harness + 4 插件工厂 + 配置系统 | 直接复用 |
| 评估体系 | 需重写 EvalRunner + 5 Evaluator + 36 用例 + LLMJudge | 直接复用框架，改数据集 |
| 可观测性 | 需重写 Trace/Metrics/Safety/Monitor + 12 张监控表 | 直接复用 |
| 记忆系统 | 需重写三层记忆 + ContextOptimizer | 直接复用 |
| MCP 集成 | 需重写 MCP Client + Searcher 外部检索 | 直接复用 |
| 数据库 + API 框架 | 需重写 FastAPI + SQLAlchemy + 所有路由 | 复用框架，改模型和端点 |
| 前端框架 | 需重写 Vue3 + Vite + ECharts + 路由 + 组件 | 复用框架，改页面 |
| 124 个测试 | 需全部重写 | 保留评估/监控测试，更新 Worker 测试 |

**保留的代码资产估值**：约 60-70% 的代码是可直接复用的基础设施。丢弃重写的成本远高于改造。

### 1.2 改造的核心原则

- **保留**：Agent 编排框架、插件体系、评估流水线、可观测性、记忆系统、MCP 集成
- **改造**：数据模型（重命名+重构）、Worker system_prompt（注入技能学习领域知识）、前端页面（去掉榜样、新增技能树）
- **删除**：明星榜样模块、看板背景图模块、通用品质的 6 分类体系、Live2D 相关代码（已禁用且与技能学习无关）

---

## 二、删除清单（减少上下文占用）

### 2.1 后端删除

| 文件/目录 | 原因 |
|----------|------|
| `backend/routers/role_models.py` | 明星榜样 API，与技能学习无关 |
| `backend/routers/dashboard_bg.py` | 看板背景图上传，非核心功能 |
| `backend/services/role_model_service.py` | 榜样服务层 |
| `backend/routers/qualities.py` | 品质 CRUD → 改为技能 CRUD（重写而非删除） |
| `data/images/role_models/` | 12 张明星种子图片 |

### 2.2 数据模型删除

| 模型 | 原因 |
|------|------|
| `RoleModel` | 明星榜样表 |
| `RoleModelQuality` | 榜样品质关联表 |
| `CategoryMapping` | 旧 6 分类映射 → 改为 SkillPracticeType 映射 |
| `Quality` | 重命名为 `Skill` |
| `QualityLevel` | 重命名为 `SkillLevel` |
| `QualityProgress` | 重命名为 `SkillProgress` |

### 2.3 前端删除

| 文件 | 原因 |
|------|------|
| `frontend/src/views/RoleModels.vue` | 榜样浏览页 |
| `frontend/src/views/Qualities.vue` | 品质管理页 → 改为技能管理页 |
| `frontend/src/components/agent/Live2DAvatar.vue` | Live2D 已禁用且与技能学习无关 |
| `frontend/src/components/agent/VoiceWave.vue` | 语音波形，与技能学习无关 |
| `frontend/src/components/agent/EmotionBadge.vue` | 情绪标签，非核心 |

### 2.4 API 端点删除

| 端点 | 原因 |
|------|------|
| `GET /api/v1/role-models` | 榜样列表 |
| `GET /api/v1/role-models/{id}` | 榜样详情 |
| `POST /api/v1/role-models/{id}/adopt/{quality_id}` | 采纳榜样 |
| `POST /api/v1/role-models/{id}/upload-image` | 上传榜样图片 |
| `GET /api/v1/dashboard/background` | 背景图获取 |
| `POST /api/v1/dashboard/background` | 背景图上传 |

### 2.5 配置和种子数据删除

| 位置 | 内容 |
|------|------|
| `backend/database.py` | `_seed_role_models()` 函数及 12 位明星种子数据 |
| `agent-config.yaml` | `live2d` 配置段 |
| `backend/agent/config.py` | `live2d.enabled` 相关配置项 |

### 2.6 预估上下文减少量

| 类别 | 删除行数（估算） |
|------|-----------------|
| 后端榜样模块 | ~400 行 |
| 前端榜样页面 | ~250 行 |
| 榜样种子数据 | ~300 行 |
| Live2D 前端组件 | ~200 行 |
| 背景图模块 | ~100 行 |
| 旧 6 分类相关 | ~150 行 |
| **合计** | **~1400 行** |

---

## 三、数据模型重构

### 3.1 核心模型：Skill（替代 Quality）

```python
class Skill(Base):
    """用户正在学习的技能"""
    id: int PK
    name: str(50)              # 如 "Python 数据分析"
    description: str(200)      # 如 "使用 pandas/numpy 进行数据清洗和可视化"
    icon: str(20)              # 图标标识
    target_level: int          # 目标等级 1-5
    category: str(30)          # 技能大类: 编程/语言/乐器/运动/设计/其他
    created_at: datetime
    is_active: bool
```

### 3.2 等级体系：SkillLevel（保留 5 级，改描述）

```python
DEFAULT_LEVELS = [
    (1, "入门期", "了解基本概念，需要教程和指导才能完成练习", 0),
    (2, "学习期", "能独立完成基础练习，但遇到新问题需要查阅资料", 100),
    (3, "应用期", "能完成中等难度项目，开始形成自己的方法论", 300),
    (4, "熟练期", "能处理复杂问题，可以教初学者", 600),
    (5, "精通期", "已经成为你的标签能力，别人因这项技能记住你", 1000),
]
```

### 3.3 练习类型映射：SkillPracticeType（替代 CategoryMapping）

```python
class SkillPracticeType(Base):
    """不同练习类型对该技能的贡献权重"""
    skill_id: int FK
    practice_type: str(30)     # 学习/练习/项目/复习/教学
    score_per_duration: float  # 每分钟积分
    score_per_completion: int  # 每次完成积分
```

4 种练习类型替代旧 6 分类：

| 练习类型 | 含义 | 默认积分权重 |
|---------|------|------------|
| 学习 | 看教程/读书/看视频 | 0.05/分钟 + 3/次 |
| 练习 | 做题/写代码/弹琴 | 0.10/分钟 + 5/次 |
| 项目 | 做完整项目/作品 | 0.15/分钟 + 10/次 |
| 复习 | 回顾笔记/间隔重复 | 0.08/分钟 + 3/次 |

### 3.4 技能树节点（新增）

```python
class SkillTreeNode(Base):
    """技能树节点——一项技能的子技能拆解"""
    id: int PK
    skill_id: int FK
    parent_node_id: int | None  # 父节点，NULL=根节点
    name: str(100)              # 如 "pandas 数据清洗"
    description: str(300)
    order: int                  # 同级排序
    estimated_hours: float      # 预估学习小时数
    mastery_pct: float = 0.0    # 掌握程度 0-100
    status: str = "locked"      # locked/unlocked/in_progress/mastered
```

### 3.5 保留不变的模型

| 模型 | 说明 |
|------|------|
| `TodoItem` | 改为 4 种练习类型，字段不变 |
| `Goal` / `GoalTask` | 保持不变 |
| `AgentConversation` / `AgentMemoryDigest` | 保持不变 |
| 所有 Agent 监控/评估表（12 张） | 保持不变 |

---

## 四、Worker 改造方案

### 4.1 CoachWorker — 从通用 CBT 到学习心理教练

**当前 system_prompt 问题**：针对"焦虑/紧张/自卑"等通用情绪，不了解技能学习的特有心理模式。

**改造后 system_prompt 新增**：

```
你是技能学习心理教练。除通用 CBT 框架外，你还专精以下学习心理学概念：

学习高原期 (Learning Plateau):
  - 信号: 用户投入时间不变但技能速度下降
  - 原因: 从"快速上手期"进入"刻意练习期"，需要改变策略
  - 干预: 建议切换练习类型（从学习→项目）、交叉训练、降低期望

教程地狱 (Tutorial Hell):
  - 信号: 用户大量时间在看教程/读书，很少做项目/练习
  - 原因: 教程给虚假的"学到东西"的成就感，回避真正的挑战
  - 干预: 建议"先做再学"——先尝试做项目，遇到问题再查资料

冒名顶替综合症 (Impostor Syndrome):
  - 信号: 用户觉得"我其实不会""别人都比我厉害"
  - 原因: 技能学习中的正常阶段，尤其在学习 3-6 个月时出现
  - 干预: 引导回顾自己的项目/作品，用客观证据反驳主观感受

完美主义拖延:
  - 信号: 用户一直在"准备"而不开始做项目
  - 原因: 害怕做出不够好的东西
  - 干预: 建议"先做出能用的版本，再迭代优化"
```

### 4.2 GoalDecomposerWorker — 从通用目标拆解到技能树拆解

**当前 system_prompt 问题**：拆解对任何目标一视同仁，不了解技能的层级依赖关系。

**改造后 system_prompt 新增**：

```
你是技能学习路径规划专家。将"学 X"拆解为技能树时遵循：

技能树拆解规则:
  1. 依赖分析: A 技能是 B 技能的前置条件 → A 必须在 B 之前
     例: pandas 依赖 Python 基础 → Python 基础必须先学
  2. 颗粒度控制: 每个叶子节点的预估学习时间在 2-10 小时之间
     太粗(>20h): 需要继续拆分
     太细(<1h): 合并到上级
  3. 项目驱动: 每个子技能关联一个迷你项目/练习
     例: "学完 pandas 数据清洗" → 项目: "清洗一份脏数据集，输出统计摘要"
  4. 输出 skill_tree JSON 结构

输出格式:
{
  "skill_tree": {
    "name": "Python 数据分析",
    "nodes": [
      {
        "name": "Python 基础",
        "order": 1,
        "estimated_hours": 20,
        "children": [
          {"name": "变量和数据类型", "estimated_hours": 3, "project": "写一个温度转换器"},
          {"name": "函数和类", "estimated_hours": 5, "project": "写一个简易计算器"},
          ...
        ]
      },
      {
        "name": "pandas 数据处理",
        "order": 2,
        "depends_on": ["Python 基础"],
        "estimated_hours": 15,
        ...
      }
    ]
  }
}
```

### 4.3 ProfilerWorker — 从通用习惯分析到刻意练习分析

**当前 system_prompt 问题**：只看完成率和时间分布，不懂技能学习的专业指标。

**改造后新增分析维度**：

```
你是技能学习数据分析师。除基本统计外，你还分析：

刻意练习指标:
  - 练习类型分布: 学习:练习:项目:复习 的比例是否健康
    初学者: 4:4:1:1 → 正常
    高原期: 7:2:1:0 → 警告: 在"教程地狱"
    进阶者: 2:3:3:2 → 健康比例
  - 新内容占比: 本周练习中有多少是"第一次遇到的内容"
    过高(>80%): 可能没有足够复习
    过低(<20%): 可能在舒适区重复
  - 难度递增: 本周任务的平均复杂度是否高于上周
    连续 3 周不增长 → 可能在学习高原期
  - 间隔重复: 同一子技能的练习间隔是否合理
    连续 2 天练同一内容 → 可能不需要
    超过 7 天未复习 → 可能遗忘

技能速度 (Skill Velocity):
  - 定义: 日均技能积分增长量
  - 健康: > 5 分/天
  - 减速: 连续 7 天 < 3 分/天 → 触发高原检测
  - 停滞: 连续 14 天 < 1 分/天 → 需要干预
```

### 4.4 SearcherWorker — 从通用搜索到学习资源策展

**当前 system_prompt 问题**：搜索不区分资源质量、难度等级、学习场景。

**改造后新增**：

```
你是学习资源策展人。搜索时关注：

资源筛选标准:
  - 难度匹配: 根据用户当前技能等级筛选资源
    Level 1 入门期 → 找"零基础""入门""新手友好"内容
    Level 3 应用期 → 找"进阶""实战""最佳实践"内容
  - 类型多样性: 同一主题提供多种形式的资源
    视频教程、文字教程、交互式练习、项目源码
  - 来源可信度: 官方文档 > 知名教程平台 > 个人博客
  - 时效性: 编程类优先 2 年内的内容，理论类可放宽

搜索策略:
  当用户卡住时 → 优先搜索"常见错误""常见坑""debug 指南"
  当用户想进阶时 → 搜索"进阶路线""源码分析""设计模式"
  当用户做项目时 → 搜索"项目实战""完整教程""示例代码"
```

### 4.5 SchedulerWorker — 保持结构，增加间隔重复

**改造内容**：在排程时引入间隔重复策略。

```
排程时考虑:
  - 新学习的内容: 第二天安排一次简短复习（15-20% 的原始学习时间）
  - 一周前学的内容: 安排一次复习检查
  - 项目任务: 安排在用户精力最好的时间段（从 Profiler 数据推断）
  - 周末: 安排较大块的项目时间
```

---

## 五、前端改造方案

### 5.1 页面变更

| 旧页面 | 新页面 | 改动 |
|--------|--------|------|
| Dashboard (看板) | SkillDashboard (技能看板) | 品质卡片→技能卡片，新增技能树概览 |
| DailyInput (录入) | PracticeInput (练习录入) | 分类从 6→4，增加练习类型选择 |
| CheckIn (打卡) | PracticeCheckIn (练习打卡) | 增加练习类型筛选，练习时长统计 |
| Qualities (品质) | Skills (技能管理) | 新建技能→附带自动技能树拆解 |
| Report (报告) | LearningReport (学习报告) | 新增技能速度曲线、练习类型分布饼图 |
| RoleModels (榜样) | **删除** | — |

### 5.2 新增组件

| 组件 | 用途 |
|------|------|
| `SkillTree.vue` | 可视化技能树（树形展开/收起，节点状态着色） |
| `SkillCard.vue` | 单个技能卡片（替代 QualityCard） |
| `PracticeTypeBadge.vue` | 练习类型标签（学习/练习/项目/复习） |
| `SkillVelocityChart.vue` | 技能速度趋势图 |

### 5.3 保留不变的组件

| 组件 | 说明 |
|------|------|
| `NavBar.vue` | 底部导航，改标签文案 |
| `RadarChart.vue` | 技能雷达图，数据源改为技能 |
| `Heatmap.vue` | 练习热力图 |
| `TrendLine.vue` | 成长趋势折线图 |
| 所有 Agent Panel 相关组件 | 保持不变 |
| 所有 Observe 相关组件 | 保持不变 |

---

## 六、评估数据集改造

### 6.1 需重写的评估用例

当前 36 个评估用例全部基于通用"自我成长"场景。需新增技能学习领域用例：

| Worker | 旧用例数 | 新增技能学习用例 | 保留的通用用例 |
|--------|---------|----------------|--------------|
| Coach | 7 | 4 (高原检测/教程地狱/冒名顶替/完美主义) | 3 (CBT 框架结构性测试) |
| GoalDecomposer | 6 | 4 (技能树结构/依赖正确性/颗粒度/项目关联) | 2 (JSON 有效性) |
| Profiler | 5 | 4 (速度检测/比例健康度/高原检测/间隔分析) | 1 (基础统计) |
| Searcher | 7 | 3 (难度匹配/资源多样性/来源可信度) | 4 (MCP 决策) |
| Scheduler | 5 | 2 (间隔重复排程/精力优化) | 3 (基础 CRUD) |
| Orchestrator | 6 | 3 (技能学习全链路编排) | 3 (路由正确性) |

### 6.2 新增 Rubric

```python
# rubric.py 新增
SKILL_COACH_RUBRIC = RubricDimension(
    name="skill-coach-quality",
    dimensions=["learning_psychology_accuracy", "actionability", "personalization"],
    ...
)

SKILL_DECOMPOSITION_RUBRIC = RubricDimension(
    name="skill-decomposition",
    dimensions=["dependency_correctness", "granularity", "project_alignment"],
    ...
)
```

---

## 七、分阶段实施路线

### Phase 1: 清理 (预计改动 ~1400 行删除)

1. 删除榜样模块：`role_models.py`、`role_model_service.py`、`RoleModels.vue`、种子数据
2. 删除背景图模块：`dashboard_bg.py`、Dashboard 背景上传 UI
3. 删除 Live2D 组件和相关配置
4. 跑 124 个测试确认无破坏
5. 前端 `npm run build` 确认通过

### Phase 2: 数据模型重构

1. `Quality` → `Skill`，`QualityLevel` → `SkillLevel`，`QualityProgress` → `SkillProgress`
2. `CategoryMapping` → `SkillPracticeType`，6 分类 → 4 练习类型
3. 新增 `SkillTreeNode` 模型
4. 更新 `schemas.py`
5. 更新所有 service 层
6. 更新路由（删除 qualities 旧端点，新增 skills 端点）
7. 更新 `contracts/api-spec.md`

### Phase 3: Worker Prompt 改造（核心）

1. 改造 5 个 Worker 的 `system_prompt`（不改变 `execute()` 逻辑）
2. 更新 `CAPABILITY_KEYWORDS` 映射
3. 更新评估数据集（新增 20 个技能学习用例）
4. 运行评估流水线，确保 SMOKE_GATE 通过

### Phase 4: 前端改造

1. 删除 RoleModels 页面，修改导航
2. Dashboard → SkillDashboard（技能卡片 + 技能树概览）
3. Qualities → Skills（新建技能 + 自动拆解触发）
4. DailyInput → PracticeInput（4 分类 + 练习类型选择）
5. Report → LearningReport（新增技能速度/练习分布图）
6. 新增 SkillTree 可视化组件
7. `npm run build` 验证

### Phase 5: 集成验证

1. 全量测试 `pytest tests/ -v`
2. 全量评估 `POST /agent/evaluation/run` + RELEASE_GATE
3. 前端构建 `npm run build`
4. 端到端测试：创建技能 → 自动拆解 → 每日练习 → 进度追踪 → AI 分析

---

## 八、风险与缓解

| 风险 | 缓解 |
|------|------|
| 重命名导致大量 import 路径断裂 | Phase 2 用全局搜索替换，运行测试即时反馈 |
| Worker prompt 改造后质量下降 | 旧评估 + 新评估双轨验证，SMOKE_GATE 兜底 |
| 数据迁移（旧 Quality 数据如何处理） | 开发环境 `data/self-grow.db` 为测试数据，直接重建；不处理生产迁移（当前无生产用户） |
| 技能树拆解质量依赖 LLM | GoalDecomposer 评估数据集覆盖 4 个技能场景，QA 闸门不通过不发布 |
| 前端改造成本高 | 优先复用现有组件（RadarChart/Heatmap/TrendLine 不改），只改数据绑定和文案 |

---

## 九、非目标

- 不引入新的 Agent 框架（如 LangGraph）
- 不修改 `TaskBrief` / `WorkerResult` 协议
- 不修改插件接口
- 不删除评估/监控/记忆系统
- 不删除 `data/` 或 `dist/data/` 目录
- 不实现社交/多人功能
- 不实现移动端 App
