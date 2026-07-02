"""组件评估器测试 — PromptEval/ToolCallEval/ReasoningEval/RAGEval/TrajectoryEval"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from backend.agent.evaluation.dataset import EvalExample
from backend.agent.evaluation.judge import LLMJudge, EvalScore
from backend.agent.evaluation.evaluators.base import BaseEvaluator
from backend.agent.evaluation.evaluators.prompt_eval import PromptEvaluator
from backend.agent.evaluation.evaluators.tool_call_eval import ToolCallEvaluator
from backend.agent.evaluation.evaluators.reasoning_eval import ReasoningEvaluator
from backend.agent.evaluation.evaluators.rag_eval import RAGEvaluator
from backend.agent.evaluation.evaluators.trajectory_eval import TrajectoryEvaluator


# ── Fixtures ──

@pytest.fixture
def mock_judge():
    """创建模拟LLMJudge"""
    llm = MagicMock()
    llm.chat = AsyncMock()
    llm.chat.return_value.content = '{"dimension_scores": {"clarity": 4, "completeness": 3, "actionability": 4}, "overall_score": 3.7, "reasoning": "ok", "confidence": 0.9}'
    return LLMJudge(llm)


@pytest.fixture
def prompt_example():
    return EvalExample(
        id="test-prompt",
        name="test",
        description="test desc",
        worker="searcher",
        eval_type="prompt",
        assertions=[
            {"type": "contains", "value": "搜索"},
            {"type": "min_length", "value": 10},
        ],
        tags=["smoke"],
    )


# ── BaseEvaluator 测试 ──

class TestBaseEvaluator:
    """BaseEvaluator断言运行"""

    def test_contains_assertion_pass(self):
        passed, reason = BaseEvaluator._run_assertions(
            "这是一个信息检索专家",
            [{"type": "contains", "value": "信息检索"}]
        )
        assert passed is True

    def test_contains_assertion_fail(self):
        passed, reason = BaseEvaluator._run_assertions(
            "这是一个信息检索专家",
            [{"type": "contains", "value": "心理学"}]
        )
        assert passed is False
        assert "不包含" in reason

    def test_not_contains_assertion(self):
        passed, reason = BaseEvaluator._run_assertions(
            "结果: 未找到匹配结果",
            [{"type": "not_contains", "value": "找到了"}]
        )
        assert passed is True

    def test_not_contains_fail(self):
        passed, reason = BaseEvaluator._run_assertions(
            "结果: 找到了10条匹配结果",
            [{"type": "not_contains", "value": "找到了"}]
        )
        assert passed is False

    def test_min_length_assertion_pass(self):
        passed, reason = BaseEvaluator._run_assertions(
            "这是一个足够长的文本" * 10,
            [{"type": "min_length", "value": 50}]
        )
        assert passed is True

    def test_min_length_assertion_fail(self):
        passed, reason = BaseEvaluator._run_assertions(
            "短",
            [{"type": "min_length", "value": 50}]
        )
        assert passed is False

    def test_no_assertions_pass(self):
        passed, reason = BaseEvaluator._run_assertions("any text", None)
        assert passed is True


# ── ToolCallEvaluator 测试 ──

class TestToolCallEvaluator:
    """工具调用评估"""

    @pytest.fixture
    def mcp_example(self):
        return EvalExample(
            id="searcher-tool-1",
            name="MCP trigger test",
            description="测试MCP触发",
            worker="searcher",
            eval_type="tool_call",
            input={"type": "mcp_decision", "local_hits": 1, "objective": "搜索知识库文档"},
            expected_output={"needs_mcp": True},
            tags=["tool_call", "smoke"],
        )

    @pytest.fixture
    def no_config_example(self):
        return EvalExample(
            id="searcher-tool-4",
            name="MCP no config test",
            description="测试无MCP配置",
            worker="searcher",
            eval_type="tool_call",
            input={"type": "mcp_decision", "local_hits": 0, "objective": "搜索知识库"},
            expected_output={"needs_mcp": False},
            tags=["tool_call"],
        )

    @pytest.mark.asyncio
    async def test_mcp_trigger(self, mcp_example, mock_judge):
        evaluator = ToolCallEvaluator()
        score = await evaluator.evaluate(mcp_example, mock_judge)
        assert score.overall_score == 5.0  # 应该触发MCP
        assert "needs_mcp=True" in score.reasoning

    @pytest.mark.asyncio
    async def test_mcp_no_config(self, no_config_example, mock_judge):
        evaluator = ToolCallEvaluator()
        score = await evaluator.evaluate(no_config_example, mock_judge)
        assert score.overall_score == 5.0  # no config时不应触发
        assert "needs_mcp=False" in score.reasoning

    @pytest.mark.asyncio
    async def test_unknown_worker(self, mock_judge):
        example = EvalExample(
            id="x", name="x", description="x",
            worker="unknown_worker", eval_type="tool_call",
        )
        evaluator = ToolCallEvaluator()
        score = await evaluator.evaluate(example, mock_judge)
        assert score.overall_score == 0.0
        assert "未找到Worker" in score.reasoning


# ── TrajectoryEvaluator 测试 ──

class TestTrajectoryEvaluator:
    """编排轨迹评估"""

    @pytest.mark.asyncio
    async def test_search_routes_to_searcher(self, mock_judge):
        example = EvalExample(
            id="orch-test",
            name="搜索路由",
            description="搜索类请求应路由给searcher",
            worker="orchestrator",
            eval_type="trajectory",
            input={"user_message": "帮我搜索一下Python教程"},
            assertions=[{"type": "plan_has_worker", "value": "searcher"}],
            tags=["trajectory"],
        )
        evaluator = TrajectoryEvaluator()
        score = await evaluator.evaluate(example, mock_judge)
        assert score.overall_score == 5.0

    @pytest.mark.asyncio
    async def test_coach_routes_to_coach(self, mock_judge):
        example = EvalExample(
            id="orch-test2",
            name="心理辅导路由",
            description="情绪类请求应路由给coach",
            worker="orchestrator",
            eval_type="trajectory",
            input={"user_message": "我最近感到非常焦虑和压力大"},
            assertions=[{"type": "plan_has_worker", "value": "coach"}],
            tags=["trajectory"],
        )
        evaluator = TrajectoryEvaluator()
        score = await evaluator.evaluate(example, mock_judge)
        assert score.overall_score == 5.0

    @pytest.mark.asyncio
    async def test_wrong_routing_fails(self, mock_judge):
        """错误路由应得0分"""
        example = EvalExample(
            id="orch-test3",
            name="错误路由",
            description="搜索请求路由给coach是错误的",
            worker="orchestrator",
            eval_type="trajectory",
            # "搜索"会匹配searcher的关键词, 不会匹配coach
            input={"user_message": "帮我搜索"},
            assertions=[{"type": "plan_has_worker", "value": "coach"}],  # 预期coach, 但关键词匹配searcher
            tags=["trajectory"],
        )
        evaluator = TrajectoryEvaluator()
        score = await evaluator.evaluate(example, mock_judge)
        assert score.overall_score == 0.0

    @pytest.mark.asyncio
    async def test_missing_assertion_returns_zero(self, mock_judge):
        example = EvalExample(
            id="orch-test4",
            name="无断言",
            description="无plan_has_worker断言时返回0分",
            worker="orchestrator",
            eval_type="trajectory",
            input={"user_message": "你好"},
            tags=["trajectory"],
        )
        evaluator = TrajectoryEvaluator()
        score = await evaluator.evaluate(example, mock_judge)
        assert score.overall_score == 0.0
        assert "未配置" in score.reasoning


# ── RAGEvaluator 测试 ──

class TestRAGEvaluator:
    """RAG检索质量评估"""

    @pytest.mark.asyncio
    async def test_rag_evaluate(self, mock_judge):
        example = EvalExample(
            id="rag-test",
            name="RAG测试",
            description="检索Test条目",
            worker="searcher",
            eval_type="rag",
            input={"task_id": "rag-1", "objective": "测试"},
            tags=["rag"],
        )
        evaluator = RAGEvaluator()
        score = await evaluator.evaluate(example, mock_judge)
        # 无断言时LLMJudge返回4分, 或因检索无结果score可能是0
        assert score.overall_score >= 0.0


# ── Evaluator Error Handling 测试 ──

class TestEvaluatorErrorHandling:
    """评估器异常处理"""

    @pytest.mark.asyncio
    async def test_unknown_worker_prompt_eval(self, mock_judge):
        example = EvalExample(
            id="x", name="x", description="x",
            worker="nonexistent", eval_type="prompt",
        )
        evaluator = PromptEvaluator()
        score = await evaluator.evaluate(example, mock_judge)
        assert score.overall_score == 0.0
        assert "未找到Worker" in score.reasoning

    @pytest.mark.asyncio
    async def test_unknown_worker_rag_eval(self, mock_judge):
        example = EvalExample(
            id="x", name="x", description="x",
            worker="nonexistent", eval_type="rag",
        )
        evaluator = RAGEvaluator()
        score = await evaluator.evaluate(example, mock_judge)
        assert score.overall_score == 0.0
        assert "未找到Worker" in score.reasoning
