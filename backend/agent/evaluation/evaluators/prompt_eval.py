"""PromptEvaluator — 评估Worker系统提示词质量

使用code-based断言(contains/min_length) + LLM-as-Judge评分。
"""

from backend.agent.evaluation.evaluators.base import BaseEvaluator
from backend.agent.evaluation.dataset import EvalExample
from backend.agent.evaluation.judge import EvalScore, LLMJudge
from backend.agent.evaluation.rubric import EvalRubric, RubricDimension
from backend.agent.orchestrator import WORKER_REGISTRY


# 默认Prompt评估Rubric
PROMPT_RUBRIC = EvalRubric(
    name="prompt-clarity",
    description="评估Worker系统提示词的质量: 清晰性/完整性/可操作性",
    dimensions=[
        RubricDimension(
            name="clarity",
            description="提示词是否清晰定义了工作步骤和输出格式",
            scale={
                1: "完全模糊,无法理解要做什么",
                2: "部分清晰,但关键步骤缺失或混乱",
                3: "基本清晰,步骤可理解但不够精确",
                4: "清晰,步骤明确且有逻辑顺序",
                5: "非常清晰,每一步都有具体的、可操作的描述",
            },
            weight=1.0,
        ),
        RubricDimension(
            name="completeness",
            description="提示词是否包含所有必要的约束和边界条件",
            scale={
                1: "严重缺失:无输出格式/无角色定义/无约束",
                2: "缺失关键要素:缺少输出格式或角色定义",
                3: "基本完整:有角色和输出格式,但约束不够",
                4: "完整:角色/步骤/输出格式/约束均已定义",
                5: "非常完整:涵盖所有边界条件和异常处理",
            },
            weight=1.0,
        ),
        RubricDimension(
            name="actionability",
            description="提示词是否能让Worker实际执行任务(而非模糊期望)",
            scale={
                1: "完全不可执行:只有模糊的目标描述",
                2: "难以执行:有方向但无具体步骤",
                3: "基本可执行:能理解要做什么",
                4: "可执行:有具体步骤和判断标准",
                5: "高可执行:每一步都有明确的输入输出和判断依据",
            },
            weight=1.0,
        ),
    ],
)


class PromptEvaluator(BaseEvaluator):
    """Worker系统提示词质量评估器"""

    async def evaluate(self, example: EvalExample, judge: LLMJudge) -> EvalScore:
        """评估Worker的system_prompt

        Steps:
        1. 获取Worker的system_prompt
        2. 运行code-based断言(contains/min_length)
        3. LLM-as-Judge多维度评分
        """
        # 获取Worker system prompt
        worker_cls = WORKER_REGISTRY.get(example.worker)
        if worker_cls is None:
            return EvalScore(
                rubric_name="prompt-clarity",
                dimension_scores={"clarity": 0, "completeness": 0, "actionability": 0},
                overall_score=0.0,
                reasoning=f"未找到Worker: {example.worker}",
                confidence=0.0,
            )

        worker = worker_cls()
        prompt = worker.system_prompt

        # Code-based断言
        if example.assertions:
            passed, reason = self._run_assertions(prompt, example.assertions)
            if not passed:
                return EvalScore(
                    rubric_name="prompt-clarity",
                    dimension_scores={"clarity": 0, "completeness": 0, "actionability": 0},
                    overall_score=0.0,
                    reasoning=f"Code断言失败: {reason}",
                    confidence=1.0,
                )

        # LLM-as-Judge评分
        rubric = PROMPT_RUBRIC
        return await judge.score(
            rubric=rubric,
            subject=f"{example.worker} Worker system prompt",
            output=prompt,
        )
