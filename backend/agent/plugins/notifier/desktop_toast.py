"""Windows Toast 通知"""

import logging

from backend.agent.plugins.notifier.base import NotifierBase, Alert, PluginManifest

logger = logging.getLogger(__name__)


class DesktopToast(NotifierBase):
    """Windows Toast 桌面通知"""

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="Desktop Toast",
            version="1.0.0",
            description="Windows Toast 桌面通知",
            capabilities=["notify"],
        )

    async def notify(self, alert: Alert) -> bool:
        """发送 Windows Toast 通知"""
        try:
            # 通过 pywebview 的窗口 API 发送通知
            # 或者通过 win10toast 库
            title = f"[{alert.level.upper()}] {alert.title}"
            message = alert.message

            # 尝试使用 Windows Toast
            self._windows_toast(title, message)
            logger.info(f"Toast sent: {title}")
            return True
        except Exception as e:
            logger.error(f"Desktop toast failed: {e}")
            return False

    def _windows_toast(self, title: str, message: str) -> None:
        """Windows 原生通知"""
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(title, message, duration=5, threaded=True)
        except ImportError:
            # fallback: 使用 pywebview 的 JS 评估
            logger.debug("win10toast not available, using console output")
            print(f"\n[NOTIFICATION] {title}: {message}\n")
