"""通义千问适配器 — 备选 LLM"""

import json
import logging
from typing import AsyncGenerator

import httpx

from backend.agent.plugins.llm_adapter.base import (
    LLMAdapterBase, LLMResponse, UrgencyAssessment, PluginManifest,
)

logger = logging.getLogger(__name__)


class QwenAdapter(LLMAdapterBase):
    """通义千问 API 适配器 (阿里云百炼)"""

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="Qwen",
            version="1.0.0",
            author="Alibaba",
            description="通义千问大模型适配器 (备选)",
            capabilities=["llm"],
        )

    @property
    def _api_key(self) -> str:
        return self.config.get("api_key", "")

    @property
    def _model(self) -> str:
        return self.config.get("model", "qwen-plus")

    async def chat(self, messages: list[dict[str, str]],
                   temperature: float = 0.7,
                   max_tokens: int = 2048) -> LLMResponse:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]
        return LLMResponse(
            content=choice["message"]["content"],
            model=data.get("model", self._model),
            tokens_used=data.get("usage", {}).get("total_tokens", 0),
            finish_reason=choice.get("finish_reason", "stop"),
        )

    async def chat_stream(self, messages: list[dict[str, str]],
                          temperature: float = 0.7,
                          max_tokens: int = 2048) -> AsyncGenerator[str, None]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
                headers=headers,
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

    async def evaluate_urgency(self, tasks: list[dict],
                               context: str = "") -> list[UrgencyAssessment]:
        # Qwen 作为备选，简化实现
        return []
