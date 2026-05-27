"""上下文优化器 — Token 预算控制

参考 Google 2026 四区模型:
- 绿区 (>50% 剩余): 正常执行
- 黄区 (20-50% 剩余): 压缩上下文，语义摘要
- 红区 (5-20% 剩余): 切换轻量模型，跳过深度推理
- 熔断区 (<5% 剩余): 强制收束，返回部分结果
"""

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class BudgetZone(str, Enum):
    GREEN = "green"        # > 50% 剩余
    YELLOW = "yellow"      # 20-50% 剩余
    RED = "red"            # 5-20% 剩余
    CRITICAL = "critical"  # < 5% 剩余


class ContextOptimizer:
    """Token 预算控制器

    估算 token 数量 (简化: 中文 1 字 ≈ 0.5 token, 英文 1 词 ≈ 1.3 token)
    """

    def __init__(self, max_tokens: int = 4096):
        self.max_tokens = max_tokens
        self._estimated_used = 0

    def update_usage(self, messages: list[dict[str, str]]) -> None:
        """根据当前消息列表更新估算的 token 使用量"""
        total_text = "".join(m.get("content", "") for m in messages)
        self._estimated_used = self.estimate_tokens(total_text)

    @property
    def budget_remaining(self) -> int:
        return self.max_tokens - self._estimated_used

    @property
    def zone(self) -> BudgetZone:
        ratio = self.budget_remaining / self.max_tokens if self.max_tokens > 0 else 0
        if ratio > 0.5:
            return BudgetZone.GREEN
        elif ratio > 0.2:
            return BudgetZone.YELLOW
        elif ratio > 0.05:
            return BudgetZone.RED
        else:
            return BudgetZone.CRITICAL

    def estimate_tokens(self, text: str) -> int:
        """估算文本的 token 数量

        中文: ~0.5 token/字
        英文: ~1.3 token/词
        混合保守估计: ~0.75 token/字符
        """
        return int(len(text) * 0.75)

    def optimize_messages(self, messages: list[dict[str, str]],
                          system_prompt: str = "") -> list[dict[str, str]]:
        """根据当前预算区域优化消息列表

        策略:
        - GREEN: 不做任何处理
        - YELLOW: 摘要最早的消息
        - RED: 只保留 system + 最近 2 轮对话
        - CRITICAL: 只保留 system + 最近 1 轮对话
        """
        zone = self.zone

        # 更新估计用量
        all_text = "".join(m.get("content", "") for m in messages)
        self._estimated_used = self.estimate_tokens(all_text)

        if zone == BudgetZone.GREEN:
            return messages

        if zone == BudgetZone.YELLOW:
            # 保留 system + 最近 6 条
            return self._truncate(messages, keep_last=6)

        if zone == BudgetZone.RED:
            # 保留 system + 最近 4 条
            return self._truncate(messages, keep_last=4)

        # CRITICAL: 保留 system + 最近 2 条
        logger.warning("Token budget critical, truncating to last 2 messages")
        return self._truncate(messages, keep_last=2)

    def should_use_heavy_model(self) -> bool:
        """是否可以使用重量级模型 (需要深度推理时)"""
        return self.zone in (BudgetZone.GREEN, BudgetZone.YELLOW)

    def can_continue(self) -> bool:
        """是否还能继续对话"""
        return self.zone != BudgetZone.CRITICAL

    # === 内部 ===

    def _truncate(self, messages: list[dict[str, str]],
                   keep_last: int) -> list[dict[str, str]]:
        """截断消息列表，保留 system 消息和最后 N 条"""
        system_msgs = [m for m in messages if m.get("role") == "system"]
        non_system = [m for m in messages if m.get("role") != "system"]
        kept = non_system[-keep_last:] if len(non_system) > keep_last else non_system
        return system_msgs + kept
