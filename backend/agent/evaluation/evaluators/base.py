"""BaseEvaluator — 所有组件评估器的抽象基类"""

from abc import ABC, abstractmethod
from backend.agent.evaluation.dataset import EvalExample
from backend.agent.evaluation.judge import EvalScore, LLMJudge


class BaseEvaluator(ABC):
    """评估器抽象基类

    每个评估维度(Prompt/ToolCall/Reasoning/RAG/Trajectory)实现一个子类。

    Usage:
        evaluator = PromptEvaluator()
        scores = await evaluator.evaluate_batch(examples, judge)
    """

    @abstractmethod
    async def evaluate(self, example: EvalExample, judge: LLMJudge) -> EvalScore:
        """评估单个用例, 返回评分结果"""
        ...

    async def evaluate_batch(
        self, examples: list[EvalExample], judge: LLMJudge
    ) -> list[EvalScore]:
        """批量评估多个用例, 逐个评估并收集结果

        默认实现逐条调用evaluate(), 子类可重写以支持并行。
        """
        scores = []
        for example in examples:
            try:
                score = await self.evaluate(example, judge)
            except Exception as e:
                score = EvalScore(
                    rubric_name=example.rubric or "unknown",
                    dimension_scores={},
                    overall_score=0.0,
                    reasoning=f"评估异常: {e}",
                    confidence=0.0,
                )
            scores.append(score)
        return scores

    @staticmethod
    def _run_assertions(subject: str, assertions: list[dict] | None) -> tuple[bool, str]:
        """执行code-based断言

        支持的断言类型:
        - contains: 检查subject是否包含指定文本
        - not_contains: 检查subject是否不包含指定文本
        - min_length: 检查subject长度是否>=指定值
        - equals: 检查值是否等于指定值
        - json_path + not_empty: 检查JSON路径是否存在且非空

        Returns:
            (passed, failure_reason)
        """
        if not assertions:
            return True, ""

        for i, assertion in enumerate(assertions):
            atype = assertion.get("type", "")
            value = assertion.get("value", "")

            if atype == "contains":
                if value not in subject:
                    return False, f"断言#{i}失败: 不包含 '{value}'"

            elif atype == "not_contains":
                if value in subject:
                    return False, f"断言#{i}失败: 不应包含 '{value}'"

            elif atype == "min_length":
                if len(subject) < value:
                    return False, f"断言#{i}失败: 长度{len(subject)} < {value}"

            elif atype == "equals":
                path = assertion.get("path", "")
                if path:
                    actual = BaseEvaluator._resolve_path(subject, path)
                    if actual is not None and actual != value:
                        return False, f"断言#{i}失败: {path}={actual} != {value}"
                else:
                    if subject != value:
                        return False, f"断言#{i}失败: '{subject}' != '{value}'"

            elif atype == "json_path":
                import json
                path = assertion.get("path", "")
                data = json.loads(subject) if isinstance(subject, str) else subject
                val = BaseEvaluator._resolve_json_path(data, path)
                not_empty = assertion.get("not_empty", False)
                if not_empty and (val is None or val == [] or val == {} or val == ""):
                    return False, f"断言#{i}失败: {path}为空"
                if not not_empty and val is None:
                    return False, f"断言#{i}失败: {path}不存在"

        return True, ""

    @staticmethod
    def _resolve_path(data: str | dict, path: str) -> object:
        """解析点分隔路径, 如 'success' 或 '$.data.findings'"""
        if isinstance(data, str):
            return getattr(data, path, None)

        parts = path.replace("$.", "").split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None
        return current

    @staticmethod
    def _resolve_json_path(data: dict | list, path: str) -> object:
        """解析JSON路径, 如 '$.data.findings'"""
        parts = path.replace("$.", "").split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    idx = int(part)
                    current = current[idx] if idx < len(current) else None
                except (ValueError, IndexError):
                    return None
            else:
                return None
        return current
