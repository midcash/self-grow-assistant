"""Edge TTS 语音合成 — 免费备份引擎

Microsoft Edge TTS: 完全免费, 20+ 中文音色
通过 HTTP 调用 edge-tts 或直接使用 Microsoft API
"""

import logging
import httpx

from backend.agent.plugins.tts_engine.base import TTSEngineBase, TTSResult, PluginManifest

logger = logging.getLogger(__name__)


class EdgeTTSEngine(TTSEngineBase):
    """Edge TTS 引擎 (Microsoft, 免费备份)"""

    _DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="Edge TTS",
            version="1.0.0",
            author="Microsoft",
            description="Microsoft Edge TTS — 免费备份引擎",
            capabilities=["tts"],
        )

    async def synthesize(self, text: str, voice: str | None = None,
                         speed: float = 1.0) -> TTSResult:
        voice = voice or self.config.get("voice", self._DEFAULT_VOICE)
        rate = f"{int(speed * 100 - 100):+d}%"

        # 使用 Microsoft Edge TTS API
        ssml = f"""<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='zh-CN'>
  <voice name='{voice}'>
    <prosody rate='{rate}'>
      {text}
    </prosody>
  </voice>
</speak>"""

        headers = {
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://southeastasia.tts.speech.microsoft.com/cognitiveservices/v1",
                headers=headers,
                content=ssml,
            )
            resp.raise_for_status()
            audio_data = resp.content

        return TTSResult(
            audio_data=audio_data,
            format="mp3",
            voice=voice,
        )

    async def available_voices(self) -> list[str]:
        return [
            "zh-CN-XiaoxiaoNeural",   # 晓晓 (女)
            "zh-CN-YunxiNeural",       # 云希 (男)
            "zh-CN-XiaoyiNeural",      # 晓伊 (女)
            "zh-CN-YunyangNeural",     # 云扬 (男)
            "zh-CN-XiaochenNeural",    # 晓辰 (女)
        ]
