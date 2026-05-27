"""Qwen3-TTS 语音合成 — 主力引擎

阿里云 DashScope Qwen3-TTS API
文档: https://www.alibabacloud.com/help/en/model-studio/qwen-tts-api
"""

import logging
import httpx

from backend.agent.plugins.tts_engine.base import TTSEngineBase, TTSResult, PluginManifest

logger = logging.getLogger(__name__)


class QwenTTSEngine(TTSEngineBase):
    """Qwen3-TTS 引擎 (DashScope)"""

    _API_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
    _DEFAULT_VOICE = "Cherry"
    _DEFAULT_MODEL = "qwen3-tts-flash"

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="Qwen3-TTS",
            version="1.0.0",
            author="Alibaba",
            description="Qwen3-TTS 语音合成 — 49音色 10语言",
            capabilities=["tts"],
        )

    async def synthesize(self, text: str, voice: str | None = None,
                         speed: float = 1.0) -> TTSResult:
        api_key = self.config.get("api_key", "")
        voice = voice or self.config.get("voice", self._DEFAULT_VOICE)
        model = self.config.get("model", self._DEFAULT_MODEL)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "input": {
                "text": text,
                "voice": voice,
                "language_type": "Chinese",
                "speech_rate": speed,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self._API_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        # 解析响应: output.audio.url (非流式)
        output = data.get("output", {})
        audio = output.get("audio", {})
        audio_url = audio.get("url", "")

        if audio_url:
            logger.debug(f"Downloading TTS audio from: {audio_url[:80]}...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                audio_resp = await client.get(audio_url)
                audio_resp.raise_for_status()
                audio_data = audio_resp.content
        else:
            # 流式响应 fallback: output.audio.data (Base64 PCM)
            import base64
            audio_b64 = audio.get("data", "")
            audio_data = base64.b64decode(audio_b64) if audio_b64 else b""

        format = audio.get("format", "wav")
        duration = int(audio.get("duration", 0))

        logger.info(f"TTS synthesized: {len(audio_data)} bytes, {len(text)} chars, voice={voice}")
        return TTSResult(
            audio_data=audio_data,
            format=format,
            duration_ms=duration,
            voice=voice,
        )

    async def available_voices(self) -> list[str]:
        return [
            "Cherry",    # 芊悦 - 阳光积极小姐姐
            "Ethan",     # 晨煦 - 温暖活力男声
            "Jennifer",  # 詹妮弗 - 品牌级美语女声
            "Chelsie",   # 国际化女声
            "Serena",    # 优雅女声
            "Dylan",     # 北京-晓东
            "Jada",      # 上海-阿珍
            "Sunny",     # 四川-晴儿
            "Rocky",     # 粤语-阿强
            "Roy",       # 闽南-阿杰
        ]

    async def health_check(self) -> bool:
        try:
            result = await self.synthesize("测试")
            return len(result.audio_data) > 0
        except Exception as e:
            logger.warning(f"Qwen TTS health check failed: {e}")
            return False
