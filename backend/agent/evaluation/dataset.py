"""评估数据集数据结构 — EvalExample和EvalDataset

评估用例分为5种类型:
- prompt: Worker系统提示词质量评估
- tool_call: 工具调用正确性评估
- reasoning: 推理和规划质量评估
- rag: 检索质量评估
- trajectory: 端到端轨迹评估
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvalExample:
    """单个评估用例

    每个用例定义了:
    - 评估什么 (worker + eval_type)
    - 如何评估 (rubric + assertions)
    - 预期行为 (expected_output + assertions)

    Attributes:
        id: 唯一标识符, 如 "searcher-prompt-1"
        name: 人类可读的名称
        description: 此用例测试什么
        worker: 目标Worker名称, 对应WORKER_REGISTRY的key
        eval_type: 评估类型: "prompt"/"tool_call"/"reasoning"/"rag"/"trajectory"
        input: Worker输入(TaskBrief或dict), 或None用于prompt评估
        expected_output: 预期输出(用于code-based eval), None则仅用LLMJudge
        rubric: 使用的Rubric名称, None则仅用code assertions
        assertions: code-based断言列表
        tags: 标签用于过滤, 如 ["smoke", "critical"]
    """

    id: str
    name: str
    description: str
    worker: str
    eval_type: str
    input: Any = None
    expected_output: Any = None
    rubric: str | None = None
    assertions: list[dict] | None = None
    tags: list[str] = field(default_factory=list)

    def __post_init__(self):
        valid_types = {"prompt", "tool_call", "reasoning", "rag", "trajectory"}
        if self.eval_type not in valid_types:
            raise ValueError(f"eval_type must be one of {valid_types}, got '{self.eval_type}'")


@dataclass
class EvalDataset:
    """评估数据集 — 一组EvalExample的集合

    Usage:
        ds = EvalDataset(name="searcher-eval", description="Searcher评估", examples=[...])
        filtered = ds.filter_by_type("prompt")
        filtered = ds.filter_by_tags(["smoke"])
    """

    name: str
    description: str
    examples: list[EvalExample]

    def filter_by_worker(self, worker: str) -> "EvalDataset":
        """按Worker名称过滤"""
        return EvalDataset(
            name=f"{self.name} (filtered by {worker})",
            description=self.description,
            examples=[e for e in self.examples if e.worker == worker],
        )

    def filter_by_type(self, eval_type: str) -> "EvalDataset":
        """按评估类型过滤"""
        return EvalDataset(
            name=f"{self.name} (filtered by {eval_type})",
            description=self.description,
            examples=[e for e in self.examples if e.eval_type == eval_type],
        )

    def filter_by_tags(self, tags: list[str]) -> "EvalDataset":
        """按标签过滤(包含任一标签)"""
        tag_set = set(tags)
        return EvalDataset(
            name=f"{self.name} (filtered by tags)",
            description=self.description,
            examples=[e for e in self.examples if tag_set & set(e.tags)],
        )

    def get_workers(self) -> list[str]:
        """返回数据集中涉及的Worker名称"""
        return sorted(set(e.worker for e in self.examples))

    def get_types(self) -> list[str]:
        """返回数据集中涉及的评估类型"""
        return sorted(set(e.eval_type for e in self.examples))

    def __len__(self) -> int:
        return len(self.examples)
