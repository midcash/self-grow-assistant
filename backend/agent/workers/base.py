"""Worker 基类 — 所有子 Agent 的统��接口

参考 2026 行业标准:
- 每个 Worker 有专属 system prompt + 工具集
- Worker 间不直接通信，由 Orchestrator 汇总
- 输入: TaskBrief (结构化任务描述)
- 输出: WorkerResult (结构化结果)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class TaskBrief:
    """Orchestrator 分发给 Worker 的任务（符合 2026 行业标准 8 字段）"""
    task_id: str
    objective: str          # 任务目标 (一句话)
    context: str = ""       # 相关上下文
    constraints: list[str] = field(default_factory=list)  # 约束条件
    expected_format: str = "text"  # 输出格式: text / json / list
    output_schema: dict | None = None   # 期望的 JSON Schema（expected_format=json 时）
    max_retries: int = 2    # 失败最大重试次数
    timeout_seconds: int = 30  # 单次执行超时


@dataclass
class WorkerResult:
    """Worker 返回的结构化结果"""
    task_id: str
    success: bool
    content: str            # 结果内容
    data: dict | list | None = None  # 结构化数据 (选项)
    sources: list[str] = field(default_factory=list)  # 信息来源
    confidence: float = 1.0  # 置信度 0-1


class WorkerBase(ABC):
    """Worker 基类

    每个 Worker Agent 必须实现:
    - role: 角色标识
    - system_prompt: 专属系统提示词
    - execute(task_brief) -> WorkerResult: 执行任务
    - capabilities(): 声明能处理的任务类型
    """

    def __init__(self):
        self._llm = None  # 由 Orchestrator 注入

    @property
    @abstractmethod
    def role(self) -> str:
        """角色标识: searcher / profiler / executor"""
        ...

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """专属系统提示词"""
        ...

    def capabilities(self) -> list[str]:
        """声明能处理的任务类型"""
        return []

    def set_llm(self, llm) -> None:
        """注入 LLM 适配器"""
        self._llm = llm

    @abstractmethod
    async def execute(self, brief: TaskBrief) -> WorkerResult:
        """执行任务并返回结果（子类实现核心逻辑）"""
        ...

    async def execute_with_retry(self, brief: TaskBrief) -> WorkerResult:
        """带超时+重试的执行包装（编排器调用此方法，不直接调 execute）"""
        import asyncio

        last_error = None
        for attempt in range(brief.max_retries + 1):
            try:
                result = await asyncio.wait_for(
                    self.execute(brief),
                    timeout=brief.timeout_seconds,
                )
                if result.success:
                    return result
                last_error = Exception(result.content)
            except asyncio.TimeoutError:
                last_error = TimeoutError(
                    f"{self.role} 超时 ({brief.timeout_seconds}s)"
                )
            except Exception as e:
                last_error = e

        return WorkerResult(
            task_id=brief.task_id,
            success=False,
            content=f"重试 {brief.max_retries} 次后仍失败: {last_error}",
            confidence=0.0,
        )

    async def _call_llm(self, messages: list[dict], **kwargs) -> str:
        """便捷方法: 调用 LLM"""
        if not self._llm:
            raise RuntimeError(f"Worker '{self.role}' has no LLM injected")
        resp = await self._llm.chat(messages, **kwargs)
        return resp.content
