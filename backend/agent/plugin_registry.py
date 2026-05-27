"""插件注册中心 — Factory 模式

参考: Open-LLM-VTuber 的 Factory 模式 + 2026 生产级实践
- 工厂注册: register_factory(capability, factory_class)
- 实例创建: create(capability, config)
- 热替换: hot_swap(capability, new_plugin)
- 能力查询: get(capability)
"""

import logging
from typing import Any

from backend.agent.plugin_base import PluginBase, PluginManifest

logger = logging.getLogger(__name__)


class PluginRegistry:
    """插件注册中心

    Factory 模式: 注册工厂类 → 按需创建实例
    支持热替换: 先加载新插件，验证成功后卸载旧插件
    """

    def __init__(self):
        self._plugins: dict[str, PluginBase] = {}          # capability -> instance
        self._factories: dict[str, type[PluginBase]] = {}  # capability -> factory class
        self._manifests: dict[str, PluginManifest] = {}    # capability -> manifest

    # === 工厂注册 ===

    def register_factory(self, capability: str, factory: type[PluginBase]) -> None:
        """注册插件工厂类

        Args:
            capability: 能力标识 (如 'llm', 'tts', 'priority', 'notify')
            factory: 插件工厂类 (非实例)
        """
        if not issubclass(factory, PluginBase):
            raise TypeError(
                f"Factory {factory.__name__} must be a subclass of PluginBase"
            )
        self._factories[capability] = factory
        logger.info(f"Registered factory for '{capability}': {factory.__name__}")

    def unregister_factory(self, capability: str) -> None:
        """注销工厂"""
        self._factories.pop(capability, None)
        self._manifests.pop(capability, None)
        # 同时卸载已创建的实例
        old = self._plugins.pop(capability, None)
        if old and old.is_loaded:
            logger.info(f"Unregistered plugin: {old.manifest.name}")

    # === 实例管理 ===

    async def create(self, capability: str, config: dict[str, Any] | None = None) -> PluginBase:
        """工厂方法: 创建并加载插件实例

        Args:
            capability: 能力标识
            config: 插件配置

        Returns:
            已加载的插件实例

        Raises:
            ValueError: 未注册对应的工厂
        """
        if capability not in self._factories:
            raise ValueError(f"No factory registered for capability '{capability}'")

        config = config or {}
        factory = self._factories[capability]
        instance = factory()
        await instance.on_load(config)
        self._plugins[capability] = instance
        self._manifests[capability] = instance.manifest
        logger.info(f"Created and loaded plugin: {instance.manifest.name} v{instance.manifest.version}")
        return instance

    def get(self, capability: str) -> PluginBase | None:
        """获取已加载的插件实例"""
        return self._plugins.get(capability)

    def get_manifest(self, capability: str) -> PluginManifest | None:
        """获取插件元数据"""
        return self._manifests.get(capability)

    # === 热替换 ===

    async def hot_swap(self, capability: str, new_factory: type[PluginBase],
                       config: dict[str, Any] | None = None) -> PluginBase:
        """热替换插件: 先加载新插件，成功后再卸载旧插件

        参考 2026 最佳实践: 故障隔离 — 新插件失败不影响旧插件继续运行
        """
        config = config or {}
        old_instance = self._plugins.get(capability)

        # 1. 注册新工厂
        self._factories[capability] = new_factory

        # 2. 创建并加载新实例
        new_instance = new_factory()
        await new_instance.on_load(config)

        # 3. 替换
        self._plugins[capability] = new_instance
        self._manifests[capability] = new_instance.manifest

        # 4. 卸载旧实例
        if old_instance and old_instance.is_loaded:
            await old_instance.on_unload()

        logger.info(
            f"Hot-swapped '{capability}': "
            f"{old_instance.manifest.name if old_instance else 'None'} -> {new_instance.manifest.name}"
        )
        return new_instance

    # === 查询 ===

    @property
    def loaded_capabilities(self) -> list[str]:
        """已加载的能力列表"""
        return list(self._plugins.keys())

    @property
    def registered_factories(self) -> list[str]:
        """已注册的工厂列表"""
        return list(self._factories.keys())

    def list_plugins(self) -> dict[str, dict]:
        """列出所有已加载插件的信息"""
        return {
            cap: {
                "name": inst.manifest.name,
                "version": inst.manifest.version,
                "loaded": inst.is_loaded,
                "healthy": True,  # 由 health_check 更新
            }
            for cap, inst in self._plugins.items()
        }
