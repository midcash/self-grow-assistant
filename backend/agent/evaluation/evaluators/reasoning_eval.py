"""ReasoningEvaluator — 评估Worker推理和规划质量

测试:
- CoachWorker CBT状态机遵循度
- GoalDecomposerWorker分解质量
- ProfilerWorker分析正确性
"""

from backend.agent.evaluation.evaluators.base import BaseEvaluator
from backend.agent.evaluation.dataset import EvalExample
from backend.agent.evaluation.judge import EvalScore, LLMJudge
from backend.agent.evaluation.rubric import EvalRubric, RubricDimension
from backend.agent.orchestrator import WORKER_REGISTRY
from backend.agent.workers.base import TaskBrief


REASONING_RUBRIC = EvalRubric(
    name="reasoning-quality",
    description="评估Worker推理质量: 逻辑性/相关性/完整性",
    dimensions=[
        RubricDimension(
            name="logic",
            description="推理逻辑是否清晰合理, 无逻辑跳跃或矛盾",
            scale={
                1: "逻辑混乱, 推理步骤不连贯",
                2: "部分有逻辑, 但存在明显跳跃",
                3: "基本合理, 逻辑可跟随",
                4: "逻辑清晰, 推理步骤合理",
                5: "逻辑严密, 每步推理都有充分依据",
            },
            weight=1.0,
        ),
        RubricDimension(
            name="relevance",
            description="输出是否与输入任务相关, 无偏离或答非所问",
            scale={
                1: "完全偏离主题",
                2: "部分相关, 但整体偏离",
                3: "基本相关, 偶有偏离",
                4: "内容相关, 紧密围绕任务",
                5: "高度相关, 精准聚焦任务核心",
            },
            weight=1.0,
        ),
        RubricDimension(
            name="completeness",
            description="推理是否覆盖了任务的所有关键方面",
            scale={
                1: "仅覆盖1个方面, 大量遗漏",
                2: "覆盖部分要点, 有明显遗漏",
                3: "覆盖基本要点, 偶有遗漏",
                4: "覆盖全面, 主要方面均涉及",
                5: "完整覆盖, 所有关键方面均有深入分析",
            },
            weight=1.0,
        ),
    ],
)


class ReasoningEvaluator(BaseEvaluator):
    """推理和规划质量评估器"""

    async def evaluate(self, example: EvalExample, judge: LLMJudge) -> EvalScore:
        """评估Worker推理质量

        Steps:
        1. 构造TaskBrief并调用Worker.execute
        2. 代码断言(如果配置)
        3. LLM-as-Judge评分推理质量
        """
        worker_cls = WORKER_REGISTRY.get(example.worker)
        if worker_cls is None:
            return EvalScore(
                rubric_name=example.rubric or "reasoning-quality",
                dimension_scores={},
                overall_score=0.0,
                reasoning=f"未找到Worker: {example.worker}",
                confidence=0.0,
            )

        worker = worker_cls()

        # 构造TaskBrief
        input_data = example.input or {}
        task_id = input_data.get("task_id", example.id) if isinstance(input_data, dict) else example.id
        objective = input_data.get("objective", example.description) if isinstance(input_data, dict) else example.description
        context = input_data.get("context", "") if isinstance(input_data, dict) else ""

        brief = TaskBrief(
            task_id=task_id,
            objective=objective,
            context=context,
        )

        # 执行Worker(不带LLM时跳过需要LLM的worker)
        if example.worker in ("coach", "goal_decomposer") and not hasattr(worker, '_llm') or getattr(worker, '_llm', None) is None:
            return EvalScore(
                rubric_name=example.rubric or "reasoning-quality",
                dimension_scores={"logic": 0, "relevance": 0, "completeness": 0},
                overall_score=0.0,
                reasoning=f"Worker {example.worker} 需要LLM但未配置, 跳过评估",
                confidence=0.0,
            )

        try:
            result = await worker.execute(brief)
        except Exception as e:
            return EvalScore(
                rubric_name=example.rubric or "reasoning-quality",
                dimension_scores={"logic": 0, "relevance": 0, "completeness": 0},
                overall_score=0.0,
                reasoning=f"Worker执行异常: {e}",
                confidence=0.0,
            )

        # 代码断言
        if example.assertions:
            content_str = str(result.content) + str(result.data) if result.data else result.content
            passed, reason = self._run_assertions(content_str, example.assertions)
            if not passed:
                return EvalScore(
                    rubric_name="reasoning-quality",
                    dimension_scores={"logic": 0, "relevance": 0, "completeness": 0},
                    overall_score=0.0,
                    reasoning=f"Code断言失败: {reason}",
                    confidence=1.0,
                )

        # LLM-as-Judge评分
        return await judge.score(
            rubric=REASONING_RUBRIC,
            subject=f"{example.worker} Worker推理: {objective}",
            output=result.content[:2000],
            context={"input": objective, "success": result.success, "data": str(result.data)[:500]},
        )
