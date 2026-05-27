"""TTS 引擎工厂"""

from backend.agent.plugins.tts_engine.base import TTSEngineBase
from backend.agent.plugins.tts_engine.qwen_tts import QwenTTSEngine
from backend.agent.plugins.tts_engine.edge_tts import EdgeTTSEngine


class TTSFactory:
    """TTS 引擎工厂"""

    _engines = {
        "qwen": QwenTTSEngine,
        "edge": EdgeTTSEngine,
    }

    @classmethod
    def create(cls, provider: str) -> TTSEngineBase:
        engine_class = cls._engines.get(provider)
        if engine_class is None:
            raise ValueError(
                f"Unknown TTS provider '{provider}'. "
                f"Available: {list(cls._engines.keys())}"
            )
        return engine_class()

    @classmethod
    def register(cls, name: str, engine_class: type[TTSEngineBase]) -> None:
        if not issubclass(engine_class, TTSEngineBase):
            raise TypeError(f"{engine_class} must be a subclass of TTSEngineBase")
        cls._engines[name] = engine_class

    @classmethod
    def available_providers(cls) -> list[str]:
        return list(cls._engines.keys())
