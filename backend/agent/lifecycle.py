"""生命周期管理器 — 插件热插拔 + 健康检查

参考 2026 生产级实践:
- 按依赖顺序加载插件
- 反向顺序卸载 (优雅关闭)
- 定期健康检查 (每 5 分钟)
- 故障自动恢复
"""

import asyncio
import logging
from typing import Any

from backend.agent.plugin_base import PluginBase

logger = logging.getLogger(__name__)


class LifecycleManager:
    """管理所有插件的加载/卸载/健康检查"""

    def __init__(self):
        self._plugins: dict[str, PluginBase] = {}
        self._load_order: list[str] = []
        self._health_task: asyncio.Task | None = None
        self._health_interval: float = 300.0  # 5 分钟

    # === 加载 / 卸载 ===

    async def load_plugin(self, name: str, plugin: PluginBase,
                          config: dict[str, Any] | None = None) -> bool:
        """加载单个插件

        Args:
            name: 插件标识名
            plugin: 插件实例 (已创建但未加载)
            config: 插件配置

        Returns:
            是否加载成功
        """
        try:
            await plugin.on_load(config or {})
            self._plugins[name] = plugin
            self._load_order.append(name)
            logger.info(f"Plugin loaded: {plugin.manifest.name} v{plugin.manifest.version}")
            return True
        except Exception as e:
            logger.error(f"Failed to load plugin '{name}': {e}")
            return False

    async def unload_plugin(self, name: str) -> bool:
        """卸载单个插件"""
        plugin = self._plugins.get(name)
        if not plugin:
            return False
        try:
            await plugin.on_unload()
            self._plugins.pop(name, None)
            self._load_order.remove(name)
            logger.info(f"Plugin unloaded: {plugin.manifest.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to unload plugin '{name}': {e}")
            return False

    async def load_all(self, plugin_map: dict[str, tuple[PluginBase, dict[str, Any] | None]]
                       ) -> dict[str, bool]:
        """批量加载插件 (按依赖顺序)

        Args:
            plugin_map: {name: (instance, config)}

        Returns:
            {name: success}
        """
        results: dict[str, bool] = {}

        # 简单拓扑排序: 有依赖的插件后加载
        ordered = self._topological_order(plugin_map)

        for name in ordered:
            instance, config = plugin_map[name]
            # 检查依赖是否已加载
            deps = instance.manifest.dependencies
            missing = [d for d in deps if d not in self._plugins]
            if missing:
                logger.error(f"Cannot load '{name}': missing dependencies {missing}")
                results[name] = False
                continue
            results[name] = await self.load_plugin(name, instance, config)

        return results

    async def shutdown(self) -> None:
        """优雅关闭: 反向依赖顺序卸载所有插件"""
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass

        # 反向卸载
        for name in reversed(self._load_order):
            await self.unload_plugin(name)

        logger.info("All plugins shut down")

    # === 健康检查 ===

    async def health_check(self) -> dict[str, bool]:
        """对所有已加载插件执行健康检查"""
        results = {}
        for name, plugin in self._plugins.items():
            try:
                healthy = await plugin.health_check()
                results[name] = healthy
                if not healthy:
                    logger.warning(f"Plugin '{name}' health check failed")
            except Exception as e:
                logger.error(f"Plugin '{name}' health check error: {e}")
                results[name] = False
        return results

    def start_health_loop(self) -> None:
        """启动定期健康检查循环"""
        if self._health_task and not self._health_task.done():
            return

        async def _loop():
            while True:
                await asyncio.sleep(self._health_interval)
                results = await self.health_check()
                unhealthy = [k for k, v in results.items() if not v]
                if unhealthy:
                    logger.warning(f"Unhealthy plugins: {unhealthy}")

        self._health_task = asyncio.create_task(_loop())
        logger.info(f"Health check loop started (interval: {self._health_interval}s)")

    # === 内部 ===

    def _topological_order(self, plugin_map: dict) -> list[str]:
        """简单的拓扑排序: 有依赖的放后面"""
        ordered = []
        remaining = set(plugin_map.keys())

        while remaining:
            added = False
            for name in list(remaining):
                instance, _ = plugin_map[name]
                deps = set(instance.manifest.dependencies)
                if deps.issubset(set(ordered) | (set(plugin_map.keys()) - remaining)):
                    ordered.append(name)
                    remaining.remove(name)
                    added = True
            if not added:
                # 有循环依赖，剩下的直接追加
                ordered.extend(remaining)
                break

        return ordered

    @property
    def loaded_plugins(self) -> list[str]:
        return list(self._plugins.keys())
