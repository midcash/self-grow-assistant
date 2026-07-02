"""EvalRunner — 评估流水线编排器

将数据集加载、组件评估、LLMJudge评分、闸门检查串联为完整的评估流水线。

Usage:
    runner = EvalRunner(llm, config=EvalConfig())
    report = await runner.run_all()
    print(f"Passed: {report.passed}, Score: {report.dimension_scores}")
"""

import json
import time
import uuid
import logging
from dataclasses import dataclass, field

from backend.agent.evaluation.dataset import EvalDataset, EvalExample
from backend.agent.evaluation.judge import LLMJudge, EvalScore
from backend.agent.evaluation.evaluators.base import BaseEvaluator
from backend.agent.evaluation.evaluators.prompt_eval import PromptEvaluator
from backend.agent.evaluation.evaluators.tool_call_eval import ToolCallEvaluator
from backend.agent.evaluation.evaluators.reasoning_eval import ReasoningEvaluator
from backend.agent.evaluation.evaluators.rag_eval import RAGEvaluator
from backend.agent.evaluation.evaluators.trajectory_eval import TrajectoryEvaluator

logger = logging.getLogger(__name__)


# ── 配置和报告数据结构 ──

@dataclass
class EvalConfig:
    """评估运行配置

    Attributes:
        name: 运行名称
        components: 要运行的评估组件列表
        workers: 要评估的Worker列表, 空=全部
        tags: 过滤标签, 空=全部
        fail_fast: 第一个失败后停止
    """

    name: str = "manual"
    components: list[str] = field(default_factory=lambda: ["prompt", "tool_call", "reasoning", "rag", "trajectory"])
    workers: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    fail_fast: bool = False


@dataclass
class ComponentSummary:
    """单个评估组件的汇总统计"""

    total: int = 0
    passed: int = 0
    failed: int = 0
    avg_score: float = 0.0
    min_score: float = 0.0
    max_score: float = 0.0


@dataclass
class EvalReport:
    """完整评估报告

    Attributes:
        run_id: 唯一运行标识
        config: 运行配置
        summary: 按组件的汇总统计 {component_name: ComponentSummary}
        dimension_scores: 全局维度分数 {"prompt": 4.2, "rag": 3.9, ...}
        results: 所有individual EvalScore
        gates_results: 闸门检查结果(由ReleaseGate.evaluate填充)
        passed: 整体是否通过
        total_duration_ms: 总耗时
    """

    run_id: str
    config: EvalConfig
    summary: dict[str, ComponentSummary] = field(default_factory=dict)
    dimension_scores: dict[str, float] = field(default_factory=dict)
    results: list[EvalScore] = field(default_factory=list)
    gates_results: list["GateResult"] = field(default_factory=list)
    passed: bool = False
    total_duration_ms: int = 0

    def to_dict(self) -> dict:
        """转换为可序列化的dict"""
        return {
            "run_id": self.run_id,
            "config": {
                "name": self.config.name,
                "components": self.config.components,
                "workers": self.config.workers,
                "tags": self.config.tags,
            },
            "summary": {
                k: {
                    "total": v.total,
                    "passed": v.passed,
                    "failed": v.failed,
                    "avg_score": v.avg_score,
                    "min_score": v.min_score,
                    "max_score": v.max_score,
                }
                for k, v in self.summary.items()
            },
            "dimension_scores": self.dimension_scores,
            "results": [
                {
                    "rubric_name": s.rubric_name,
                    "overall_score": s.overall_score,
                    "dimension_scores": s.dimension_scores,
                    "reasoning": s.reasoning[:300],
                    "confidence": s.confidence,
                    "bias_corrections": s.bias_corrections,
                }
                for s in self.results
            ],
            "passed": self.passed,
            "total_duration_ms": self.total_duration_ms,
        }


# ── EvalRunner ──

class EvalRunner:
    """评估流水线编排器

    将评估数据集加载 → 组件Evaluator调度 → LLMJudge评分 →
    结果聚合 → 生成EvalReport的完整流程。
    """

    # 组件到Evaluator的映射
    EVALUATORS: dict[str, type[BaseEvaluator]] = {
        "prompt": PromptEvaluator,
        "tool_call": ToolCallEvaluator,
        "reasoning": ReasoningEvaluator,
        "rag": RAGEvaluator,
        "trajectory": TrajectoryEvaluator,
    }

    def __init__(self, llm, config: EvalConfig | None = None):
        self._llm = llm
        self._judge = LLMJudge(llm)
        self._config = config or EvalConfig()
        self._datasets: list[EvalDataset] = []

    def _load_datasets(self):
        """加载数据集"""
        from backend.agent.evaluation.datasets import ALL_DATASETS
        self._datasets = list(ALL_DATASETS)

    def _get_examples(self, component: str) -> list[EvalExample]:
        """按component过滤数据集中的examples

        Args:
            component: 评估类型("prompt"/"tool_call"/"reasoning"/"rag"/"trajectory")
        """
        all_examples = []
        for ds in self._datasets:
            examples = ds.filter_by_type(component).examples

            # 按worker过滤
            if self._config.workers:
                worker_set = set(self._config.workers)
                examples = [e for e in examples if e.worker in worker_set]

            # 按tags过滤
            if self._config.tags:
                tag_set = set(self._config.tags)
                examples = [e for e in examples if tag_set & set(e.tags)]

            all_examples.extend(examples)

        return all_examples

    async def run_all(self) -> EvalReport:
        """运行所有配置的评估组件

        Flow:
        1. 加载数据集
        2. 逐component评估
        3. 聚合结果
        4. 生成EvalReport

        Returns:
            EvalReport含所有维度的得分和通过/失败判断
        """
        t_start = time.time()
        run_id = str(uuid.uuid4())[:12]

        # 加载数据集
        self._load_datasets()

        all_scores: list[EvalScore] = []
        summary: dict[str, ComponentSummary] = {}
        dimension_scores: dict[str, float] = {}

        for component in self._config.components:
            if component not in self.EVALUATORS:
                logger.warning(f"未知评估组件: {component}, 跳过")
                continue

            examples = self._get_examples(component)
            if not examples:
                logger.info(f"组件 {component}: 无匹配的评估用例, 跳过")
                continue

            evaluator = self.EVALUATORS[component]()
            logger.info(f"组件 {component}: 运行{len(examples)}个用例...")

            # 执行评估
            scores = await evaluator.evaluate_batch(examples, self._judge)

            # 统计
            comp_summary = self._compute_summary(scores)
            summary[component] = comp_summary

            # 记录到TraceCollector
            self._record_to_tracer(run_id, component, comp_summary)

            all_scores.extend(scores)

            if self._config.fail_fast and comp_summary.failed > 0:
                logger.warning(f"组件 {component}: fail_fast触发, 停止后续评估")
                break

        # 全局维度分
        for component, comp_summary in summary.items():
            dimension_scores[component] = comp_summary.avg_score

        # 判定通过(所有组件avg_score >= 3.0)
        all_pass = all(s.avg_score >= 3.0 for s in summary.values()) if summary else False

        duration = int((time.time() - t_start) * 1000)

        report = EvalReport(
            run_id=run_id,
            config=self._config,
            summary=summary,
            dimension_scores=dimension_scores,
            results=all_scores,
            passed=all_pass,
            total_duration_ms=duration,
        )

        logger.info(f"评估完成: {run_id} | 通过={report.passed} | 耗时={duration}ms")
        return report

    async def run_component(self, component: str) -> list[EvalScore]:
        """运行单个评估组件

        Returns:
            该组件的所有EvalScore列表
        """
        if component not in self.EVALUATORS:
            return []

        self._load_datasets()
        examples = self._get_examples(component)
        if not examples:
            return []

        evaluator = self.EVALUATORS[component]()
        return await evaluator.evaluate_batch(examples, self._judge)

    def _compute_summary(self, scores: list[EvalScore]) -> ComponentSummary:
        """从分数列表计算汇总统计"""
        if not scores:
            return ComponentSummary()

        values = [s.overall_score for s in scores]
        passed_count = sum(1 for v in values if v >= 3.0)

        return ComponentSummary(
            total=len(scores),
            passed=passed_count,
            failed=len(scores) - passed_count,
            avg_score=round(sum(values) / len(values), 1),
            min_score=min(values),
            max_score=max(values),
        )

    def _record_to_tracer(self, run_id: str, component: str, summary: ComponentSummary):
        """将评估摘要写入TraceCollector"""
        try:
            from backend.agent.observability.tracer import get_tracer
            tracer = get_tracer()
            tracer.record_span(
                orchestration_id=run_id,
                span_type="eval_component",
                agent_name=component,
                objective=f"eval:{component}",
                output_summary=f"passed={summary.passed}/{summary.total} avg={summary.avg_score}",
                latency_ms=0,
                success=summary.failed == 0,
                metadata=json.dumps({
                    "total": summary.total,
                    "passed": summary.passed,
                    "failed": summary.failed,
                    "avg_score": summary.avg_score,
                }),
            )
            tracer.flush()
        except Exception as e:
            logger.debug(f"TraceCollector写入失败: {e}")
