"""优先级评估引擎接口"""

from abc import abstractmethod
from dataclasses import dataclass, field

from backend.agent.plugin_base import PluginBase, PluginManifest


@dataclass
class ScoredTask:
    """评分后的任务"""
    todo_id: int
    content: str
    category: str = ""
    priority_score: float = 0.0     # 最终优先级 0-1
    urgency_score: float = 0.0      # 紧急度
    importance_score: float = 0.0   # 重要度
    algorithm_score: float = 0.0    # 算法评分
    llm_score: float = 0.0          # LLM 评分
    llm_reasoning: str = ""         # LLM 判断理由
    suggested_action: str = ""      # 建议行动
    is_deadline_near: bool = False  # 是否临近截止
    long_task_protection: float = 1.0  # 长任务保护系数


class PriorityEngineBase(PluginBase):
    """优先级评估引擎基类

    能力: 'priority'
    每 20 分钟调用 evaluate() 评估所有未完成任务
    """

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name=self.__class__.__name__,
            version="1.0.0",
            capabilities=["priority"],
        )

    @abstractmethod
    async def evaluate(self, tasks: list[dict],
                       context: dict | None = None) -> list[ScoredTask]:
        """评估任务优先级并排序

        Args:
            tasks: 未完成任务列表 [{id, content, deadline, importance, today_progress, today_quota, ...}]
            context: 上下文 {current_time, user_state, ...}

        Returns:
            按 priority_score 降序排列的 ScoredTask 列表
        """
        ...

    @abstractmethod
    def needs_alert(self, scored_task: ScoredTask) -> bool:
        """判断是否需要语音提醒 (score > 0.7)"""
        ...
