"""DeepSeek V4 Pro 适配器"""

import json
import logging
from typing import AsyncGenerator

import httpx

from backend.agent.plugins.llm_adapter.base import (
    LLMAdapterBase, LLMResponse, UrgencyAssessment, PluginManifest,
)

logger = logging.getLogger(__name__)


class DeepSeekV4Adapter(LLMAdapterBase):
    """DeepSeek V4 Pro API 适配器"""

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="DeepSeek V4 Pro",
            version="1.0.0",
            author="DeepSeek",
            description="DeepSeek V4 Pro 大模型适配器",
            capabilities=["llm"],
        )

    @property
    def _api_base(self) -> str:
        return self.config.get("api_base", "https://api.deepseek.com/v1")

    @property
    def _api_key(self) -> str:
        return self.config.get("api_key", "")

    @property
    def _model(self) -> str:
        return self.config.get("model", "deepseek-chat")

    async def chat(self, messages: list[dict[str, str]],
                   temperature: float = 0.7,
                   max_tokens: int = 2048) -> LLMResponse:
        """发送对话请求到 DeepSeek"""
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self._api_base}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        choice = data["choices"][0]
        msg = choice["message"]
        content = msg.get("content") or msg.get("reasoning_content", "")
        emotion_tag = self._extract_emotion_tag(content)

        return LLMResponse(
            content=self._strip_emotion_tags(content),
            model=data.get("model", self._model),
            tokens_used=data.get("usage", {}).get("total_tokens", 0),
            finish_reason=choice.get("finish_reason", "stop"),
            emotion_tag=emotion_tag,
        )

    async def chat_stream(self, messages: list[dict[str, str]],
                          temperature: float = 0.7,
                          max_tokens: int = 2048) -> AsyncGenerator[str, None]:
        """流式对话"""
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
                f"{self._api_base}/chat/completions",
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
                            if "content" in delta and delta["content"]:
                                yield delta["content"]
                            elif "reasoning_content" in delta and delta["reasoning_content"]:
                                yield delta["reasoning_content"]
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

    async def evaluate_urgency(self, tasks: list[dict],
                               context: str = "") -> list[UrgencyAssessment]:
        """使用 DeepSeek 评估任务紧急度"""
        if not tasks:
            return []

        tasks_text = "\n".join(
            f"{i+1}. {t.get('content', '')} "
            f"(截止: {t.get('deadline', '无')}, "
            f"重要度: {t.get('importance', 5)}/10, "
            f"今日进度: {t.get('today_progress', 'N/A')})"
            for i, t in enumerate(tasks)
        )

        system_prompt = """你是一个任务紧急度评估专家。对每个任务输出 JSON：
{
  "assessments": [
    {
      "task_index": 1,
      "urgency_score": 0.0-1.0,
      "importance_score": 0.0-1.0,
      "reasoning": "判断理由(20字内)",
      "suggested_action": "建议立即做什么"
    }
  ]
}
评估标准：
- 紧急度：距截止时间越近越高
- 重要度：长期价值越大越高
- 同时考虑任务间的相对优先级"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"当前时间: {context}\n\n任务列表:\n{tasks_text}"},
        ]

        try:
            resp = await self.chat(messages, temperature=0.3, max_tokens=2048)
            data = json.loads(self._extract_json(resp.content))
            assessments = data.get("assessments", [])

            return [
                UrgencyAssessment(
                    task_content=tasks[a["task_index"] - 1].get("content", ""),
                    urgency_score=a["urgency_score"],
                    importance_score=a["importance_score"],
                    reasoning=a["reasoning"],
                    suggested_action=a["suggested_action"],
                )
                for a in assessments
                if 0 <= a["task_index"] - 1 < len(tasks)
            ]
        except Exception as e:
            logger.error(f"Urgency evaluation failed: {e}")
            return []

    # === Emotion Tag 解析 ===

    _EMOTION_TAGS = ["HAPPY", "WORRIED", "URGENT", "CALM", "THINKING", "ENCOURAGE"]

    def _extract_emotion_tag(self, text: str) -> str:
        """从回复中提取情感标签 [EMOTION]"""
        for tag in self._EMOTION_TAGS:
            if f"[{tag}]" in text.upper():
                return tag
        return ""

    def _strip_emotion_tags(self, text: str) -> str:
        """移除情感标签"""
        import re
        pattern = r'\[(' + '|'.join(self._EMOTION_TAGS) + r')\]'
        return re.sub(pattern, '', text, flags=re.IGNORECASE).strip()

    # === JSON 提取 ===

    def _extract_json(self, text: str) -> str:
        """从 LLM 输出中提取 JSON"""
        # 尝试定位 { ... } 块
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return text[start:end + 1]
        return text
