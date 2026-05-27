"""LLM 适配器接口 — 所有大模型插件必须实现"""

from abc import abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator

from backend.agent.plugin_base import PluginBase, PluginManifest


@dataclass
class LLMResponse:
    """LLM 统一响应"""
    content: str
    model: str = ""
    tokens_used: int = 0
    finish_reason: str = "stop"
    emotion_tag: str = ""  # [HAPPY] [URGENT] [CALM] etc.


@dataclass
class UrgencyAssessment:
    """紧急度评估结果"""
    task_content: str
    urgency_score: float    # 0-1
    importance_score: float  # 0-1
    reasoning: str
    suggested_action: str


class LLMAdapterBase(PluginBase):
    """LLM 适配器基类

    能力: 'llm'
    """

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name=self.__class__.__name__,
            version="1.0.0",
            capabilities=["llm"],
        )

    @abstractmethod
    async def chat(self, messages: list[dict[str, str]],
                   temperature: float = 0.7,
                   max_tokens: int = 2048) -> LLMResponse:
        """发送对话请求"""
        ...

    @abstractmethod
    async def chat_stream(self, messages: list[dict[str, str]],
                          temperature: float = 0.7,
                          max_tokens: int = 2048) -> AsyncGenerator[str, None]:
        """流式对话"""
        ...

    @abstractmethod
    async def evaluate_urgency(self, tasks: list[dict],
                               context: str = "") -> list[UrgencyAssessment]:
        """评估任务紧急度"""
        ...

    async def health_check(self) -> bool:
        """健康检查：发送最小化请求验证连通性"""
        try:
            resp = await self.chat(
                [{"role": "user", "content": "ping"}],
                max_tokens=10,
            )
            return bool(resp.content)
        except Exception:
            return False
