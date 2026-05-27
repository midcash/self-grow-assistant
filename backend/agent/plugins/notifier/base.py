"""通知推送接口"""

from abc import abstractmethod
from dataclasses import dataclass

from backend.agent.plugin_base import PluginBase, PluginManifest


@dataclass
class Alert:
    """提醒消息"""
    title: str
    message: str
    level: str = "normal"     # normal / urgent / critical
    task_id: int | None = None
    action_url: str = ""       # 点击跳转链接


class NotifierBase(PluginBase):
    """通知推送基类

    能力: 'notify'
    """

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name=self.__class__.__name__,
            version="1.0.0",
            capabilities=["notify"],
        )

    @abstractmethod
    async def notify(self, alert: Alert) -> bool:
        """发送通知

        Returns:
            是否发送成功
        """
        ...
