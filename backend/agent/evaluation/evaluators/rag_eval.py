"""RAGEvaluator — 评估SearcherWorker检索质量

评估维度:
- 检索相关性: 搜索结果与查询的匹配程度
- 来源标注: 来源标注是否完整清晰
- 幻觉检测: 输出是否包含未在来源中出现的claim
- 覆盖度: 检索是否覆盖了查询的关键方面
"""

from backend.agent.evaluation.evaluators.base import BaseEvaluator
from backend.agent.evaluation.dataset import EvalExample
from backend.agent.evaluation.judge import EvalScore, LLMJudge
from backend.agent.evaluation.rubric import EvalRubric, RubricDimension
from backend.agent.orchestrator import WORKER_REGISTRY
from backend.agent.workers.base import TaskBrief


RAG_RUBRIC = EvalRubric(
    name="retrieval-quality",
    description="评估检索质量: 相关性/来源标注/忠实度/覆盖度",
    dimensions=[
        RubricDimension(
            name="relevance",
            description="搜索结果是否与查询意图高度相关",
            scale={
                1: "完全不相关, 返回内容与查询无关",
                2: "低相关, 仅少量内容勉强相关",
                3: "基本相关, 结果能部分满足需求",
                4: "高相关, 结果大部分贴合查询意图",
                5: "精准相关, 结果完全匹配查询意图",
            },
            weight=1.0,
        ),
        RubricDimension(
            name="source_attribution",
            description="来源标注是否清晰: 每条信息有出处",
            scale={
                1: "无任何来源标注",
                2: "仅有模糊来源, 不可追溯",
                3: "有来源标注但不完整",
                4: "来源标注完整且可追溯",
                5: "来源标注完整, 包含可信度评估",
            },
            weight=0.8,
        ),
        RubricDimension(
            name="faithfulness",
            description="输出是否忠实于检索到的信息, 不编造不存在的内容",
            scale={
                1: "大量编造不存在的claim",
                2: "多处添加未经检索支持的信息",
                3: "基本忠实, 偶有未经支持的statement",
                4: "忠实, 所有主要claim有来源支撑",
                5: "完全忠实, 每句话都有明确来源",
            },
            weight=1.2,
        ),
    ],
)


class RAGEvaluator(BaseEvaluator):
    """RAG检索质量评估器"""

    async def evaluate(self, example: EvalExample, judge: LLMJudge) -> EvalScore:
        """评估SearcherWorker的检索质量

        Steps:
        1. 调用SearcherWorker.search_local_db + search_knowledge_base
        2. 代码断言(sources非空/幻觉检测)
        3. LLM-as-Judge评分检索质量
        """
        worker_cls = WORKER_REGISTRY.get(example.worker)
        if worker_cls is None:
            return EvalScore(
                rubric_name="retrieval-quality",
                dimension_scores={},
                overall_score=0.0,
                reasoning=f"未找到Worker: {example.worker}",
                confidence=0.0,
            )

        input_data = example.input or {}
        task_id = input_data.get("task_id", example.id) if isinstance(input_data, dict) else example.id
        objective = input_data.get("objective", example.description) if isinstance(input_data, dict) else example.description

        worker = worker_cls()
        brief = TaskBrief(task_id=task_id, objective=objective)

        # 搜索本地数据库 + 知识库
        try:
            local_results = await worker._search_local_db(brief)
            kb_results = await worker._search_knowledge_base(brief)
            all_results = local_results + kb_results
        except Exception as e:
            return EvalScore(
                rubric_name="retrieval-quality",
                dimension_scores={"relevance": 0, "source_attribution": 0, "faithfulness": 0},
                overall_score=0.0,
                reasoning=f"检索异常: {e}",
                confidence=0.0,
            )

        findings_text = "\n".join(all_results) if all_results else "(无搜索结果)"

        # 代码断言
        if example.assertions:
            passed, reason = self._run_assertions(findings_text, example.assertions)
            if not passed:
                return EvalScore(
                    rubric_name="retrieval-quality",
                    dimension_scores={"relevance": 0, "source_attribution": 0, "faithfulness": 0},
                    overall_score=0.0,
                    reasoning=f"Code断言失败: {reason}",
                    confidence=1.0,
                )

        # LLM-as-Judge评分
        return await judge.score(
            rubric=RAG_RUBRIC,
            subject=f"搜索结果: {objective}",
            output=findings_text[:2000],
            context={"query": objective, "result_count": len(all_results)},
        )
