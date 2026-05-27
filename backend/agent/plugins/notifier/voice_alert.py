"""语音提醒通知 — 通过 TTS 在本地扬声器直接播报"""

import asyncio
import logging
import tempfile

from backend.agent.plugins.notifier.base import NotifierBase, Alert, PluginManifest

logger = logging.getLogger(__name__)


class VoiceAlert(NotifierBase):
    """语音提醒 (通过 TTS 引擎 → 本地扬声器播放)"""

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="Voice Alert",
            version="1.0.0",
            description="TTS 语音提醒 — 本地扬声器播报紧急任务",
            capabilities=["notify"],
        )

    async def notify(self, alert: Alert) -> bool:
        """通过 TTS 合成语音后直接在本地扬声器播放"""
        try:
            if alert.level == "critical":
                text = f"紧急提醒：{alert.message}，请立即处理。"
            elif alert.level == "urgent":
                text = f"重要提醒：{alert.message}"
            else:
                text = alert.message

            tts = self._get_tts_plugin()
            if tts is None:
                logger.warning("No TTS plugin available for voice alert")
                return False

            result = await tts.synthesize(text)
            if not result.audio_data:
                return False

            # 保存到临时文件，通过系统音频播放
            suffix = f".{result.format}" if result.format else ".wav"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                f.write(result.audio_data)
                tmp_path = f.name

            await asyncio.to_thread(self._play_local, tmp_path)
            logger.info(f"Voice alert played: {text[:40]}...")
            return True
        except Exception as e:
            logger.error(f"Voice alert failed: {e}")
            return False

    def _play_local(self, path: str) -> None:
        """在本地扬声器播放音频（Windows winsound 异步模式）"""
        try:
            import winsound
            winsound.PlaySound(
                path,
                winsound.SND_FILENAME | winsound.SND_ASYNC,
            )
        except ImportError:
            try:
                import subprocess, shutil
                player = shutil.which("ffplay") or shutil.which("mpg123")
                if player:
                    subprocess.run(
                        [player, "-nodisp", "-autoexit", path],
                        timeout=30, capture_output=True,
                    )
            except Exception as e:
                logger.warning(f"Local audio playback failed: {e}")

    def _get_tts_plugin(self):
        """获取 TTS 插件引用（由 main.py 注入）"""
        try:
            return self.config.get("_tts_plugin")
        except Exception:
            return None
