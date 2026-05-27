"""LLM 适配器工厂"""

from backend.agent.plugins.llm_adapter.base import LLMAdapterBase
from backend.agent.plugins.llm_adapter.deepseek_v4 import DeepSeekV4Adapter
from backend.agent.plugins.llm_adapter.qwen import QwenAdapter


class LLMFactory:
    """LLM 适配器工厂"""

    _adapters = {
        "deepseek": DeepSeekV4Adapter,
        "qwen": QwenAdapter,
    }

    @classmethod
    def create(cls, provider: str) -> LLMAdapterBase:
        """创建 LLM 适配器实例"""
        adapter_class = cls._adapters.get(provider)
        if adapter_class is None:
            raise ValueError(
                f"Unknown LLM provider '{provider}'. "
                f"Available: {list(cls._adapters.keys())}"
            )
        return adapter_class()

    @classmethod
    def register(cls, name: str, adapter_class: type[LLMAdapterBase]) -> None:
        """注册新的适配器"""
        if not issubclass(adapter_class, LLMAdapterBase):
            raise TypeError(f"{adapter_class} must be a subclass of LLMAdapterBase")
        cls._adapters[name] = adapter_class

    @classmethod
    def available_providers(cls) -> list[str]:
        return list(cls._adapters.keys())
