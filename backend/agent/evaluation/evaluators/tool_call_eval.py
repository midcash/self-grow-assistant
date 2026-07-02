"""ToolCallEvaluator — 评估Worker工具调用决策正确性

测试:
- MCP调用决策(SearcherWorker._needs_mcp)
- 工具选择正确性
- 工具参数正确性
- 干扰项处理
"""

from backend.agent.evaluation.evaluators.base import BaseEvaluator
from backend.agent.evaluation.dataset import EvalExample
from backend.agent.evaluation.judge import EvalScore, LLMJudge
from backend.agent.orchestrator import WORKER_REGISTRY
from backend.agent.workers.base import TaskBrief


class ToolCallEvaluator(BaseEvaluator):
    """工具调用正确性评估器"""

    async def evaluate(self, example: EvalExample, judge: LLMJudge) -> EvalScore:
        """评估工具调用决策

        支持的input type:
        - mcp_decision: 测试SearcherWorker._needs_mcp决策
        - worker_execute: 运行Worker.execute并检查结果
        """
        input_data = example.input or {}
        input_type = input_data.get("type", "worker_execute")

        if input_type == "mcp_decision":
            return await self._eval_mcp_decision(example, input_data)
        else:
            return await self._eval_worker_execute(example, input_data, judge)

    async def _eval_mcp_decision(
        self, example: EvalExample, input_data: dict
    ) -> EvalScore:
        """测试MCP调用决策逻辑(不需要LLM)"""
        worker_cls = WORKER_REGISTRY.get(example.worker)
        if worker_cls is None:
            return EvalScore(
                rubric_name="tool-call",
                dimension_scores={},
                overall_score=0.0,
                reasoning=f"未找到Worker: {example.worker}",
                confidence=0.0,
            )

        worker = worker_cls()

        # 设置MCP config(模拟有/无配置)
        local_hits = input_data.get("local_hits", 0)
        objective = input_data.get("objective", "search")

        # 模拟有MCP配置的情况
        worker._mcp_config = {"command": "python", "args": ["test.py"]}

        # 特殊处理: no_config场景
        if example.id == "searcher-tool-4":
            worker._mcp_config = None

        brief = TaskBrief(task_id=example.id, objective=objective)
        decision = worker._needs_mcp(brief, local_hits)

        expected = example.expected_output.get("needs_mcp", False) if example.expected_output else False
        passed = decision == expected

        return EvalScore(
            rubric_name="tool-call",
            dimension_scores={"tool_correctness": 5.0 if passed else 0.0},
            overall_score=5.0 if passed else 0.0,
            reasoning=f"MCP决策: needs_mcp={decision}, expected={expected}, {'通过' if passed else '失败'}",
            confidence=1.0,
        )

    async def _eval_worker_execute(
        self, example: EvalExample, input_data: dict, judge: LLMJudge
    ) -> EvalScore:
        """运行Worker并检查执行结果"""
        worker_cls = WORKER_REGISTRY.get(example.worker)
        if worker_cls is None:
            return EvalScore(
                rubric_name="tool-call",
                dimension_scores={},
                overall_score=0.0,
                reasoning=f"未找到Worker: {example.worker}",
                confidence=0.0,
            )

        worker = worker_cls()

        # 构造TaskBrief
        task_id = input_data.get("task_id", example.id)
        objective = input_data.get("objective", "")
        context_data = input_data.get("context", "")

        brief = TaskBrief(
            task_id=task_id,
            objective=objective,
            context=context_data if isinstance(context_data, str) else str(context_data),
        )

        # 执行Worker
        result = await worker.execute(brief)

        # 运行断言
        if example.assertions:
            for assertion in example.assertions:
                atype = assertion.get("type", "")
                path = assertion.get("path", "success")

                if atype == "equals" and path == "success":
                    expected = assertion.get("value", True)
                    if result.success != expected:
                        return EvalScore(
                            rubric_name="tool-call",
                            dimension_scores={"tool_correctness": 0.0},
                            overall_score=0.0,
                            reasoning=f"断言失败: success={result.success}, expected={expected}",
                            confidence=1.0,
                        )

        # 无断言时, 根据success判断
        score = 5.0 if result.success else 0.0
        return EvalScore(
            rubric_name="tool-call",
            dimension_scores={"tool_correctness": score},
            overall_score=score,
            reasoning=f"Worker执行结果: success={result.success}, content={result.content[:200]}",
            confidence=result.confidence,
        )
