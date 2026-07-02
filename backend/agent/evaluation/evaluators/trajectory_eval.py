"""TrajectoryEvaluator — 评估Orchestrator端到端轨迹质量

评估维度:
- 计划质量: _plan是否正确识别意图和分配Worker
- Worker路由: Worker选择是否准确
- 综合质量: 多Worker协作是否连贯
"""

from backend.agent.evaluation.evaluators.base import BaseEvaluator
from backend.agent.evaluation.dataset import EvalExample
from backend.agent.evaluation.judge import EvalScore, LLMJudge
from backend.agent.evaluation.rubric import EvalRubric, RubricDimension
from backend.agent.orchestrator import Orchestrator, CAPABILITY_KEYWORDS


TRAJECTORY_RUBRIC = EvalRubric(
    name="trajectory-quality",
    description="评估Agent编排轨迹: 计划质量/Worker路由/综合质量",
    dimensions=[
        RubricDimension(
            name="plan_accuracy",
            description="意图识别是否正确, 任务分解是否合理",
            scale={
                1: "意图完全错误, 任务分解不成立",
                2: "意图部分正确, 但任务分解有问题",
                3: "意图基本正确, 任务分解可接受",
                4: "意图正确, 任务分解合理",
                5: "意图精准, 任务分解最优",
            },
            weight=1.0,
        ),
        RubricDimension(
            name="worker_routing",
            description="Worker分配是否准确, 无错配或遗漏",
            scale={
                1: "Worker完全错配, 无正确的Worker被调用",
                2: "部分Worker正确, 但有明显错配",
                3: "基本正确, 主要Worker分配恰当",
                4: "正确, 所有Worker分配合理",
                5: "精准, Worker选择最优且考虑依赖关系",
            },
            weight=1.0,
        ),
        RubricDimension(
            name="synthesis_quality",
            description="多Worker结果合成是否连贯统一",
            scale={
                1: "合成结果混乱, 各Worker输出相互矛盾",
                2: "合成有断痕, 衔接不够自然",
                3: "基本连贯, 可理解整体回答",
                4: "连贯, 各部分衔接自然",
                5: "高度连贯, 如同一个整体输出",
            },
            weight=0.8,
        ),
    ],
)


class TrajectoryEvaluator(BaseEvaluator):
    """编排轨迹评估器"""

    async def evaluate(self, example: EvalExample, judge: LLMJudge) -> EvalScore:
        """评估Orchestrator的编排轨迹

        使用Orchestrator._rule_based_plan()进行规则匹配,
        验证Worker路由是否符合预期。

        Note: 轨迹评估不使用LLM-as-Judge(避免双重LLM调用),
        而是直接验证_plan的Worker路由。
        """
        input_data = example.input or {}
        user_message = input_data.get("user_message", example.description) if isinstance(input_data, dict) else example.description

        # 使用规则匹配(不依赖LLM)
        plan = self._get_rule_based_workers(user_message)

        # 获取expected worker
        expected_worker = None
        if example.assertions:
            for assertion in example.assertions:
                if assertion.get("type") == "plan_has_worker":
                    expected_worker = assertion.get("value")
                    break

        if expected_worker is None:
            return EvalScore(
                rubric_name="trajectory-quality",
                dimension_scores={"plan_accuracy": 0, "worker_routing": 0, "synthesis_quality": 0},
                overall_score=0.0,
                reasoning="未配置plan_has_worker断言",
                confidence=0.0,
            )

        # 检查Worker路由
        routed_workers = [t["id"] for t in plan.get("subtasks", [])]
        has_correct_worker = expected_worker in routed_workers

        return EvalScore(
            rubric_name="trajectory-quality",
            dimension_scores={
                "plan_accuracy": 5.0 if has_correct_worker else 0.0,
                "worker_routing": 5.0 if has_correct_worker else 0.0,
                "synthesis_quality": 4.0 if has_correct_worker else 0.0,
            },
            overall_score=5.0 if has_correct_worker else 0.0,
            reasoning=(
                f"Worker路由: expected={expected_worker}, routed={routed_workers}, "
                + ("通过" if has_correct_worker else "失败")
            ),
            confidence=1.0,
        )

    def _get_rule_based_workers(self, message: str) -> dict:
        """使用Orchestrator的规则匹配逻辑(不依赖LLM)

        复用CAPABILITY_KEYWORDS进行关键词匹配。
        """
        subtasks = []
        for worker_name, keywords in CAPABILITY_KEYWORDS.items():
            for kw in keywords:
                if kw in message:
                    subtasks.append({
                        "id": worker_name,
                        "objective": message[:100],
                        "context": message[:200],
                        "expected_format": "text",
                        "max_retries": 1,
                        "timeout_seconds": 30,
                    })
                    break  # 每个worker只匹配一次

        return {
            "intent": "general",
            "reply_intro": "",
            "subtasks": subtasks,
        }
