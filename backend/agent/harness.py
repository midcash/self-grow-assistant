"""Agent Harness — 线束核心

Agent = Model + Harness (2026 行业公式)

Harness 是智能体的操作系统，负责:
- 插件注册与生命周期
- 事件总线
- 上下文优化
- 错误处理

用法:
    harness = AgentHarness()
    await harness.start(config)
    # ... 运行 ...
    await harness.shutdown()
"""

import logging
from pathlib import Path
from typing import Any

from backend.agent.plugin_registry import PluginRegistry
from backend.agent.event_bus import EventBus
from backend.agent.lifecycle import LifecycleManager
from backend.agent.context_optimizer import ContextOptimizer
from backend.agent.error_handler import ErrorHandler

logger = logging.getLogger(__name__)


class AgentHarness:
    """智能体线束 — 整合所有核心组件"""

    def __init__(self):
        self.registry = PluginRegistry()
        self.event_bus = EventBus()
        self.lifecycle = LifecycleManager()
        self.context_optimizer = ContextOptimizer(max_tokens=4096)
        self.error_handler = ErrorHandler()
        self._started = False
        self._config: dict[str, Any] = {}

    @property
    def is_started(self) -> bool:
        return self._started

    # === 启动 / 关闭 ===

    async def start(self, config: dict[str, Any]) -> None:
        """启动 Harness"""
        self._config = config
        self._started = True
        logger.info("Agent Harness started")
        logger.info(f"  - Max tokens: {self.context_optimizer.max_tokens}")
        logger.info(f"  - Registered factories: {self.registry.registered_factories}")

    async def shutdown(self) -> None:
        """关闭 Harness"""
        await self.lifecycle.shutdown()
        self._started = False
        logger.info("Agent Harness shut down")

    # === 便捷方法 ===

    def get_plugin(self, capability: str):
        """获取已加载的插件"""
        return self.registry.get(capability)

    async def publish_event(self, event_type, data: dict | None = None,
                            source: str = "") -> None:
        """发布事件"""
        from backend.agent.event_bus import Event
        await self.event_bus.publish(Event(
            type=event_type,
            data=data or {},
            source=source,
        ))

    def token_budget_zone(self):
        """当前 Token 预算区域"""
        return self.context_optimizer.zone

    async def health_check(self) -> dict[str, Any]:
        """全系统健康检查"""
        plugin_health = {}
        for cap, plugin in self.registry._plugins.items():
            try:
                healthy = await plugin.health_check()
                plugin_health[cap] = {
                    "name": plugin.manifest.name,
                    "version": plugin.manifest.version,
                    "loaded": plugin.is_loaded,
                    "healthy": healthy,
                }
            except Exception:
                plugin_health[cap] = {
                    "name": plugin.manifest.name,
                    "version": plugin.manifest.version,
                    "loaded": False,
                    "healthy": False,
                }
        return {
            "harness": "running" if self._started else "stopped",
            "plugins": plugin_health,
            "token_zone": self.context_optimizer.zone.value,
            "circuit_breakers": {
                name: cb.state
                for name, cb in self.error_handler._breakers.items()
            },
        }
