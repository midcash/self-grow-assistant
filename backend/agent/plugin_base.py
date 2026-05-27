"""插件抽象契约 — 所有插件必须实现的统一接口"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class RecoveryAction(Enum):
    RETRY = auto()
    FALLBACK = auto()
    SKIP = auto()
    ABORT = auto()


@dataclass
class PluginManifest:
    """插件元数据"""
    name: str
    version: str
    author: str = ""
    description: str = ""
    capabilities: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    config_schema: dict[str, Any] = field(default_factory=dict)


class PluginBase(ABC):
    """插件基类 — 所有插件必须实现此接口

    参考 2026 主流设计:
    - Factory + Abstract Interface 模式
    - 生命周期: on_load -> (运行) -> on_unload
    - 健康检查 + 错误恢复
    """

    def __init__(self):
        self._loaded = False
        self._config: dict[str, Any] = {}

    # === 元数据 (子类必须覆写) ===

    @property
    @abstractmethod
    def manifest(self) -> PluginManifest:
        """返回插件元数据"""
        ...

    # === 生命周期 ===

    async def on_load(self, config: dict[str, Any]) -> None:
        """加载插件，传入配置"""
        self._config = config
        self._loaded = True

    async def on_unload(self) -> None:
        """卸载插件，清理资源"""
        self._loaded = False
        self._config = {}

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def config(self) -> dict[str, Any]:
        return self._config

    # === 健康检查 ===

    async def health_check(self) -> bool:
        """健康检查，默认返回加载状态"""
        return self._loaded

    # === 能力声明 ===

    def capabilities(self) -> list[str]:
        """声明插件提供的能力"""
        return self.manifest.capabilities

    # === 错误恢复 ===

    async def on_error(self, error: Exception) -> RecoveryAction:
        """错误恢复策略，默认跳过"""
        return RecoveryAction.SKIP
