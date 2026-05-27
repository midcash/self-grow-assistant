"""加权评分算法 — 核心优先级评估引擎

双通道评估: 算法 (0.6) + LLM (0.4)

算法公式:
  urgency = e^(-λ × hours_until_deadline)
  importance = user_priority / 10
  long_task_protection = 1 + (1 - today_progress/today_quota) × 2
  time_decay = 1.0 / (1 + 0.01 × hours_since_created)
  final = urgency × importance × long_task_protection × time_decay
"""

import logging
import math
from datetime import datetime, timezone

from backend.agent.plugins.priority_engine.base import (
    PriorityEngineBase, ScoredTask, PluginManifest,
)

logger = logging.getLogger(__name__)


class WeightedScorer(PriorityEngineBase):
    """加权评分引擎

    配置参数:
    - urgency_lambda: 紧急度衰减系数 (默认 0.15)
    - long_task_factor: 长任务保护系数 (默认 2.0)
    - algorithm_weight: 算法权重 (默认 0.6)
    - llm_weight: LLM 权重 (默认 0.4)
    """

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="Weighted Priority Scorer",
            version="1.0.0",
            description="加权评分算法 + LLM 辅助的优先级评估引擎",
            capabilities=["priority"],
        )

    # === 主入口 ===

    async def evaluate(self, tasks: list[dict],
                       context: dict | None = None) -> list[ScoredTask]:
        if not tasks:
            return []

        context = context or {}
        now = datetime.now(timezone.utc)

        # 1. 算法评分
        algo_scored = [self._algorithm_score(t, now, context) for t in tasks]

        # 2. LLM 评分 (如果有 LLM 插件)
        llm_scored = await self._llm_score(tasks, context)

        # 3. 合并
        algo_weight = float(self.config.get("algorithm_weight", 0.6))
        llm_weight = float(self.config.get("llm_weight", 0.4))

        results = []
        for a in algo_scored:
            # 查找对应的 LLM 评分
            llm_s = 0.5
            llm_reasoning = ""
            llm_action = ""
            for l in (llm_scored or []):
                if l["task_index"] == a.todo_id or l.get("content") == a.content:
                    llm_s = l.get("urgency_score", 0.5)
                    llm_reasoning = l.get("reasoning", "")
                    llm_action = l.get("suggested_action", "")
                    break

            a.llm_score = llm_s
            a.llm_reasoning = llm_reasoning
            a.suggested_action = llm_action
            a.priority_score = algo_weight * a.algorithm_score + llm_weight * llm_s
            results.append(a)

        # 4. 按最终分数降序排列
        results.sort(key=lambda x: x.priority_score, reverse=True)
        return results

    def needs_alert(self, scored_task: ScoredTask) -> bool:
        return scored_task.priority_score > 0.4

    # === 算法评分 ===

    def _algorithm_score(self, task: dict, now: datetime, context: dict) -> ScoredTask:
        """计算单个任务的算法评分"""
        todo_id = task.get("id", 0)
        content = task.get("content", "")

        urgency = self._calc_urgency(task, now)
        importance = task.get("importance", 5) / 10.0
        long_protection = self._calc_long_task_protection(task)
        time_decay = self._calc_time_decay(task, now)

        algorithm_score = urgency * importance * long_protection * time_decay

        return ScoredTask(
            todo_id=todo_id,
            content=content,
            category=task.get("category", ""),
            urgency_score=urgency,
            importance_score=importance,
            algorithm_score=algorithm_score,
            priority_score=algorithm_score,
            is_deadline_near=urgency > 0.7,
            long_task_protection=long_protection,
        )

    def _calc_urgency(self, task: dict, now: datetime) -> float:
        """计算紧急度: e^(-λ × hours_until_deadline)

        λ = 0.15 意味着约 4.6 小时后紧急度减半
        """
        deadline_str = task.get("deadline")
        if not deadline_str:
            # 无截止日期，默认中等紧急度（确保能被提醒）
            return 0.5

        try:
            deadline = datetime.fromisoformat(deadline_str)
            hours_until = (deadline - now).total_seconds() / 3600.0
            if hours_until <= 0:
                return 1.0  # 已过期，最高紧急度
            lam = float(self.config.get("urgency_lambda", 0.15))
            return math.exp(-lam * hours_until)
        except (ValueError, TypeError):
            return 0.3

    def _calc_long_task_protection(self, task: dict) -> float:
        """计算长任务保护系数

        今日配额未完成 → 自动提权
        formula: 1 + (1 - progress/quota) × factor
        最大 3x
        """
        quota = task.get("today_quota", 0)
        if quota <= 0:
            return 1.0  # 非长任务

        progress = task.get("today_progress", 0)
        if progress >= quota:
            return 1.0

        factor = float(self.config.get("long_task_factor", 2.0))
        ratio = progress / quota
        protection = 1 + (1 - ratio) * factor
        return min(protection, 3.0)

    def _calc_time_decay(self, task: dict, now: datetime) -> float:
        """计算时间衰减

        formula: 1 / (1 + α × hours_since_created)
        α = 0.01, 防止旧任务无限堆积
        """
        created_str = task.get("created_at")
        if not created_str:
            return 1.0

        try:
            created = datetime.fromisoformat(created_str)
            hours_since = (now - created).total_seconds() / 3600.0
            return 1.0 / (1 + 0.01 * hours_since)
        except (ValueError, TypeError):
            return 1.0

    # === LLM 评分 ===

    async def _llm_score(self, tasks: list[dict], context: dict) -> list[dict]:
        """调用 LLM 辅助评估 (通过 harness 获取 llm 插件)"""
        try:
            # 延迟导入避免循环依赖
            from backend.agent.plugins.llm_adapter.base import LLMAdapterBase

            # 通过事件总线获取 llm 插件
            llm_plugin = None
            # harness 会在启动时注入到 context
            harness = context.get("_harness")
            if harness:
                llm_plugin = harness.registry.get("llm")

            if llm_plugin is None:
                return []

            assessments = await llm_plugin.evaluate_urgency(
                tasks,
                context=context.get("current_time", ""),
            )
            return [
                {
                    "task_index": i + 1,
                    "content": a.task_content,
                    "urgency_score": a.urgency_score,
                    "importance_score": a.importance_score,
                    "reasoning": a.reasoning,
                    "suggested_action": a.suggested_action,
                }
                for i, a in enumerate(assessments)
            ]
        except Exception as e:
            logger.warning(f"LLM scoring failed, using algorithm only: {e}")
            return []
