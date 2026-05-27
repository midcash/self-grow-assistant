"""异步事件总线 — 发布订阅 + 故障隔离

参考 2026 最佳实践:
- 单个订阅者失败不影响其他订阅者 (故障隔离)
- 断路器模式: 连续失败 N 次后暂时摘除
- 内置事件类型用于智能体内部通信
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """内置事件类型"""
    PRIORITY_CHANGED = "priority.changed"
    TASK_DEADLINE_NEAR = "task.deadline_near"
    USER_IDLE = "user.idle"
    AGENT_ERROR = "agent.error"
    PLUGIN_LOADED = "plugin.loaded"
    PLUGIN_UNLOADED = "plugin.unloaded"
    SCHEDULE_TICK = "schedule.tick"
    VOICE_ALERT_TRIGGERED = "voice.alert_triggered"


@dataclass
class Event:
    """事件"""
    type: EventType | str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = ""


Handler = Callable[[Event], Coroutine[Any, Any, None]]


class CircuitBreaker:
    """断路器: 连续失败 N 次后暂时断开"""

    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.is_open = False

    def record_success(self) -> None:
        self.failure_count = 0
        self.is_open = False

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

    def can_try(self) -> bool:
        if not self.is_open:
            return True
        if time.time() - self.last_failure_time > self.recovery_timeout:
            self.is_open = False
            self.failure_count = 0
            logger.info("Circuit breaker reset (recovery timeout elapsed)")
            return True
        return False


class EventBus:
    """异步事件总线

    特性:
    - 发布订阅模式
    - 故障隔离: 单个 handler 异常不影响其他 handler
    - 断路器: 连续失败自动摘除
    - 异步并发: 同事件多个 handler 并发执行
    """

    def __init__(self):
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)
        self._breakers: dict[str, CircuitBreaker] = {}

    def subscribe(self, event_type: EventType | str, handler: Handler) -> None:
        """订阅事件"""
        self._subscribers[event_type].append(handler)
        self._breakers.setdefault(event_type, CircuitBreaker())

    def unsubscribe(self, event_type: EventType | str, handler: Handler) -> None:
        """取消订阅"""
        subs = self._subscribers.get(event_type, [])
        if handler in subs:
            subs.remove(handler)

    async def publish(self, event: Event) -> None:
        """发布事件 (异步并发，故障隔离)

        每个 handler 独立执行，单个失败不影响其他。
        断路器打开时跳过该类型事件的所有 handler。
        """
        event_type = event.type if isinstance(event.type, str) else event.type.value
        handlers = self._subscribers.get(event_type, [])
        if not handlers:
            return

        breaker = self._breakers.get(event_type)
        if breaker and not breaker.can_try():
            logger.debug(f"Circuit breaker open for '{event_type}', skipping {len(handlers)} handlers")
            return

        async def _safe_invoke(handler: Handler) -> None:
            try:
                await handler(event)
                if breaker:
                    breaker.record_success()
            except Exception as e:
                logger.error(f"Handler {handler.__name__} failed for event '{event_type}': {e}")
                if breaker:
                    breaker.record_failure()

        tasks = [_safe_invoke(h) for h in handlers]
        await asyncio.gather(*tasks, return_exceptions=True)

    @property
    def subscriber_count(self) -> dict[str, int]:
        return {k: len(v) for k, v in self._subscribers.items()}
