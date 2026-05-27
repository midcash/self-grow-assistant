"""TTS 语音引擎接口"""

from abc import abstractmethod
from dataclasses import dataclass

from backend.agent.plugin_base import PluginBase, PluginManifest


@dataclass
class TTSResult:
    """TTS 合成结果"""
    audio_data: bytes
    format: str = "mp3"
    duration_ms: int = 0
    voice: str = ""


class TTSEngineBase(PluginBase):
    """TTS 语音引擎基类

    能力: 'tts'
    """

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name=self.__class__.__name__,
            version="1.0.0",
            capabilities=["tts"],
        )

    @abstractmethod
    async def synthesize(self, text: str, voice: str | None = None,
                         speed: float = 1.0) -> TTSResult:
        """将文字合成为语音

        Args:
            text: 要合成的文字
            voice: 音色 (None 使用默认)
            speed: 语速 (0.5-2.0)

        Returns:
            TTSResult 包含音频数据
        """
        ...

    @abstractmethod
    async def available_voices(self) -> list[str]:
        """获取可用音色列表"""
        ...

    async def health_check(self) -> bool:
        try:
            result = await self.synthesize("测试")
            return len(result.audio_data) > 0
        except Exception:
            return False
