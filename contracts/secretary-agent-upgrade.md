# 秘书级自主智能体 — 架构升级方案

> 成熟度: 🟡 实验阶段 — Goal/Coach/MotivationEngine 新上线，5 Phase 全通。
> 已知局限: GoalDecomposer 仅匹配最新 active goal；MotivationEngine 压力公式待校准。
> 触发升级: 积累 1 个月使用数据后，根据提醒准确率调参。


## 零、2026 行业共识：从被动到自主的范式跃迁

三个核心突破定义了 2026 年的自主 Agent 架构：

| 突破 | 代表项目 | 核心思想 |
|------|---------|---------|
| **动机引擎** | NeoPsyke (2026.03) | Id(动机积累)→Ego(规划调解)→Superego(治理) 闭环 |
| **目标分解器** | APEX Agent (2026.03) | 递归分解 + 三层世界模型（战略/战术/反射） |
| **记忆权重博弈** | 七层投射架构 (2026.05) | 冲突记忆竞争→权重调整→自反思触发 |

### 动机引擎如何工作（NeoPsyke）

```
Id 维护内部驱动力:
  - 有用性驱动:     长时间未帮助用户 → 压力累积
  - 目标关注驱动:    ddl临近但进度落后 → 压力累积
  - 互动驱动:       用户长时间未互动 → 压力累积

压力 > 阈值 → 自主脉冲 → Ego 规划 → Superego 审查 → 执行

成功 → 压力释放回基线
失败/被拒 → 压力不释放，继续累积，下次更强
```

### 这和 cron 定时器的本质区别

```
cron:     "每 20 分钟查一次" — 不关心上次结果，不关心用户状态
动机引擎:  "你该关注了"       — 基于状态变化，压力自然涨落
```

---

## 一、self-grow 现状对照

| 2026 标准能力 | self-grow 当前 | 差距 |
|-------------|---------------|------|
| **动机引擎** | 无。调度器是固定 cron | 没有压力累积，没有自适应触发 |
| **目标模型+分解** | 无。只有 TodoItem | 不知道"面试准备"是需要分解的目标 |
| **差距分析** | Profiler 只看完成率 | 不知道"距ddl还有3天，进度30%" |
| **持续提醒升级** | needs_alert 单次判断 | 没有"提醒3次还没做→升级为紧急" |
| **辅导对话** | Chat prompt 一句话 | 没有结构化辅导框架 |
| **自主性** | 0。所有行为由用户触发 | 没有自主动机 |

---

## 二、架构升级总览

```
当前:                              升级后:

  Orchestrator                        Orchestrator
    ├── Searcher                        ├── Searcher
    ├── Profiler                        ├── Profiler → 含 GapAnalyzer
    └── Executor                        ├── Executor
                                        ├── GoalDecomposer  ← 新
                                        └── Coach           ← 新

  无                                 MotivationEngine  ← 新
  无                                 Goal + GoalTask 模型 ← 新
```

---

## 三、新增核心模块

### 3.1 Goal + GoalTask 数据模型

```python
class Goal(Base):
    id, title, description, deadline
    status: "active" | "paused" | "completed"
    target_metric: str        # 如 "投20份简历"
    current_progress: float   # 如 6.0 → 完成30%
    importance: int
    pressure: float           # MotivationEngine 计算
    reminder_count: int       # 已提醒次数
    last_reminded_at: datetime

class GoalTask(Base):
    id, goal_id(FK), content, category
    status, daily_quota, today_progress
```

### 3.2 MotivationEngine（动机引擎）

```python
class MotivationEngine:
    async def tick(self):
        for goal in active_goals:
            days_left = (goal.deadline - today).days
            required_daily = (target - progress) / max(days_left, 1)
            actual_daily = self._calc_actual_daily(goal)
            gap = max(required_daily - actual_daily, 0)
            goal.pressure = gap * (1.0 / max(days_left, 1))
        
        urgent = [g for g in active_goals if g.pressure > 0.5]
        for g in urgent:
            g.reminder_count += 1
            # 提醒3次未处理 → 升级为紧急
            if g.reminder_count >= 3:
                TTS播报: "紧急！{g.title}还剩{g.days_left}天，
                         进度{g.progress_pct}%，已提醒{g.reminder_count}次"
```

### 3.3 GoalDecomposer（目标分解 Worker）

参考 APEX 三层分解：

```
用户: "准备5月30日面试"
  → 战略层: {goal, subgoals: [技术准备, 简历优化, 模拟面试, 公司调研]}
  → 战术层: "技术准备" → [刷题3题/天, 系统设计1案例/天]
  → 操作层: 自动创建 TodoItem + GoalTask
```

### 3.4 Coach（心理辅导 Worker）

参考 Structure Matters RCT (N=66) — 多 Agent FSM 优于单 Agent：

```
状态机: 共情倾听 → 识别模式 → 认知重构 → 行动计划 → 复盘

CBT 框架:
  1. 识别自动负性思维 (ANTs)
  2. 检验思维真实性
  3. 替代为建设性思维
  4. 制定行为实验
```

---

## 四、开发路线图

| Phase | 内容 | 文件数 |
|-------|------|--------|
| **P1** Goal 基础 | Goal + GoalTask 模型 + CRUD API | 2 改 |
| **P2** GoalDecomposer | 目标分解 Worker + 注册 | 1 新 + 1 改 |
| **P3** MotivationEngine | 压力计算 + 提醒升级 + 集成 scheduler | 1 新 + 1 改 |
| **P4** Coach | CBT 辅导 Worker + 注册 | 1 新 + 1 改 |
| **P5** GapAnalyzer | Profiler 增强：目标进度差距 | 1 改 |

**总计: 3 新文件 + 5 文件修改**

---

## 五、与 2026 三大架构的定位对比

| 维度 | NeoPsyke | APEX | 七层投射 | self-grow 升级后 |
|------|----------|------|---------|-----------------|
| 动机模型 | Id/Ego/Superego | Free Energy | 记忆权 | MotivationEngine |
| 目标分解 | 无 | 递归beam search | 无 | LLM三层分解 |
| 辅导 | 无 | 无 | 无 | CBT状态机 |
| 规模 | 玩具级 | 研究级 | 概念级 | 可用级桌面应用 |

self-grow 的优势：不是研究项目，是能跑的个人软件。学的架构思想，落的简单实现。
