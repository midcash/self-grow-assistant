"""通知插件工厂"""

from backend.agent.plugins.notifier.base import NotifierBase
from backend.agent.plugins.notifier.voice_alert import VoiceAlert
from backend.agent.plugins.notifier.desktop_toast import DesktopToast


class NotifierFactory:
    """通知插件工厂"""

    _notifiers = {
        "voice": VoiceAlert,
        "toast": DesktopToast,
    }

    @classmethod
    def create(cls, provider: str) -> NotifierBase:
        notifier_class = cls._notifiers.get(provider)
        if notifier_class is None:
            raise ValueError(
                f"Unknown notifier '{provider}'. "
                f"Available: {list(cls._notifiers.keys())}"
            )
        return notifier_class()

    @classmethod
    def register(cls, name: str, notifier_class: type[NotifierBase]) -> None:
        if not issubclass(notifier_class, NotifierBase):
            raise TypeError(f"{notifier_class} must be a subclass of NotifierBase")
        cls._notifiers[name] = notifier_class
