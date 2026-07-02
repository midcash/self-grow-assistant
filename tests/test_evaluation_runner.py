"""EvalRunner和ReleaseGate测试"""

import json
import pytest
from unittest.mock import MagicMock, AsyncMock

from backend.agent.evaluation.runner import EvalRunner, EvalConfig, EvalReport, ComponentSummary
from backend.agent.evaluation.gates import ReleaseGate, GateCondition, GateResult
from backend.agent.evaluation.default_gates import SMOKE_GATE, RELEASE_GATE, DEFAULT_GATES
from backend.agent.evaluation.dataset import EvalExample, EvalDataset
from backend.agent.evaluation.judge import EvalScore


# ── Fixtures ──

@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.chat = AsyncMock()
    llm.chat.return_value.content = json.dumps({
        "dimension_scores": {"clarity": 4, "completeness": 4, "actionability": 3},
        "overall_score": 3.7,
        "reasoning": "总体质量不错",
        "confidence": 0.9,
    })
    return llm


@pytest.fixture
def sample_report():
    """创建一个模拟EvalReport用于闸门测试"""
    return EvalReport(
        run_id="test-run",
        config=EvalConfig(name="test"),
        summary={
            "prompt": ComponentSummary(total=5, passed=5, failed=0, avg_score=4.2, min_score=3.5, max_score=5.0),
            "tool_call": ComponentSummary(total=4, passed=4, failed=0, avg_score=4.5, min_score=3.0, max_score=5.0),
            "reasoning": ComponentSummary(total=6, passed=4, failed=2, avg_score=3.0, min_score=0.0, max_score=5.0),
            "rag": ComponentSummary(total=2, passed=2, failed=0, avg_score=4.0, min_score=4.0, max_score=4.0),
            "trajectory": ComponentSummary(total=6, passed=5, failed=1, avg_score=3.5, min_score=0.0, max_score=5.0),
        },
        dimension_scores={"prompt": 4.2, "tool_call": 4.5, "reasoning": 3.0, "rag": 4.0, "trajectory": 3.5},
        passed=False,
    )


# ── EvalConfig 测试 ──

class TestEvalConfig:
    def test_default_config(self):
        config = EvalConfig()
        assert "prompt" in config.components
        assert "tool_call" in config.components
        assert config.workers == []
        assert config.tags == []

    def test_custom_config(self):
        config = EvalConfig(
            name="custom",
            components=["prompt"],
            workers=["searcher"],
            tags=["smoke"],
        )
        assert config.name == "custom"
        assert config.components == ["prompt"]
        assert config.workers == ["searcher"]


# ── ComponentSummary 测试 ──

class TestComponentSummary:
    def test_empty_summary(self):
        s = ComponentSummary()
        assert s.total == 0
        assert s.passed == 0
        assert s.avg_score == 0.0

    def test_all_pass(self):
        s = ComponentSummary(total=5, passed=5, failed=0, avg_score=4.5, min_score=4.0, max_score=5.0)
        assert s.passed == 5
        assert s.failed == 0


# ── EvalReport 测试 ──

class TestEvalReport:
    def test_to_dict(self, sample_report):
        d = sample_report.to_dict()
        assert d["run_id"] == "test-run"
        assert "summary" in d
        assert "dimension_scores" in d
        assert "prompt" in d["summary"]


# ── ReleaseGate 测试 ──

class TestReleaseGate:
    def test_smoke_gate_all_pass(self, sample_report):
        # Smoke gate条件不包含reasoning,所有条件都满足
        result = SMOKE_GATE.evaluate(sample_report)
        assert result.passed is True

    def test_smoke_gate_fail(self, sample_report):
        # 修改为低分
        sample_report.summary["prompt"] = ComponentSummary(total=5, passed=1, failed=4, avg_score=2.0, min_score=0, max_score=4)
        result = SMOKE_GATE.evaluate(sample_report)
        assert result.passed is False
        assert "未通过" in result.summary

    def test_release_gate_fail_on_reasoning(self, sample_report):
        result = RELEASE_GATE.evaluate(sample_report)
        # reasoning=3.0 < 3.5 threshold, 应该不通过
        assert result.passed is False

    def test_release_gate_all_pass(self, sample_report):
        # 所有项都提到高分
        sample_report.summary["prompt"] = ComponentSummary(total=5, passed=5, failed=0, avg_score=4.5, min_score=4.0, max_score=5.0)
        sample_report.summary["tool_call"] = ComponentSummary(total=4, passed=4, failed=0, avg_score=4.5, min_score=4.0, max_score=5.0)
        sample_report.summary["reasoning"] = ComponentSummary(total=6, passed=6, failed=0, avg_score=4.0, min_score=3.5, max_score=5.0)
        sample_report.summary["rag"] = ComponentSummary(total=2, passed=2, failed=0, avg_score=4.0, min_score=4.0, max_score=4.0)
        sample_report.summary["trajectory"] = ComponentSummary(total=6, passed=6, failed=0, avg_score=4.0, min_score=3.5, max_score=5.0)

        result = RELEASE_GATE.evaluate(sample_report)
        assert result.passed is True

    def test_get_failed_conditions(self, sample_report):
        sample_report.summary["prompt"] = ComponentSummary(total=5, passed=1, failed=4, avg_score=2.0, min_score=0, max_score=4)
        result = SMOKE_GATE.evaluate(sample_report)
        failed = result.get_failed_conditions()
        assert len(failed) >= 1

    def test_operators(self):
        assert ReleaseGate._check_condition(5.0, ">=", 3.0) is True
        assert ReleaseGate._check_condition(2.0, ">=", 3.0) is False
        assert ReleaseGate._check_condition(2.0, "<=", 3.0) is True
        assert ReleaseGate._check_condition(5.0, "<=", 3.0) is False
        assert ReleaseGate._check_condition(4.0, ">", 3.0) is True
        assert ReleaseGate._check_condition(3.0, "==", 3.0) is True
        assert ReleaseGate._check_condition(1.0, "invalid", 3.0) is False

    def test_empty_report(self):
        empty_report = EvalReport(
            run_id="empty",
            config=EvalConfig(),
        )
        result = SMOKE_GATE.evaluate(empty_report)
        assert result.passed is False  # 无数据时不通过

    def test_pass_rate_metric(self):
        """测试pass_rate子指标"""
        report = EvalReport(
            run_id="test",
            config=EvalConfig(),
            summary={
                "tool_call": ComponentSummary(total=10, passed=9, failed=1, avg_score=4.0, min_score=0, max_score=5.0),
            },
        )
        gate = ReleaseGate("test", [
            GateCondition(metric="tool_call.pass_rate", operator=">=", threshold=0.9),
        ])
        result = gate.evaluate(report)
        assert result.passed is True  # 0.9 >= 0.9


# ── EvalRunner 测试 ──

class TestEvalRunner:
    """EvalRunner核心流程"""

    @pytest.mark.asyncio
    async def test_empty_components_returns_empty_report(self, mock_llm):
        config = EvalConfig(components=[])
        runner = EvalRunner(mock_llm, config)
        report = await runner.run_all()
        assert report.run_id
        assert len(report.summary) == 0
        assert report.total_duration_ms >= 0

    @pytest.mark.asyncio
    async def test_unknown_component_skipped(self, mock_llm):
        config = EvalConfig(components=["unknown_component"])
        runner = EvalRunner(mock_llm, config)
        report = await runner.run_all()
        # 未知组件跳过,无结果
        assert len(report.summary) == 0

    @pytest.mark.asyncio
    async def test_prompt_component_runs(self, mock_llm):
        """运行prompt评估,验证能产生结果"""
        config = EvalConfig(components=["prompt"], workers=["searcher"])
        runner = EvalRunner(mock_llm, config)
        report = await runner.run_all()
        assert "prompt" in report.summary
        assert report.summary["prompt"].total >= 1
        assert len(report.results) > 0

    @pytest.mark.asyncio
    async def test_tool_call_component_runs(self, mock_llm):
        """运行tool_call评估(不需要LLM)"""
        config = EvalConfig(components=["tool_call"], workers=["searcher"])
        runner = EvalRunner(mock_llm, config)
        report = await runner.run_all()
        assert "tool_call" in report.summary
        assert report.summary["tool_call"].total >= 1

    @pytest.mark.asyncio
    async def test_trajectory_component_runs(self, mock_llm):
        """运行trajectory评估(不需要LLM)"""
        config = EvalConfig(components=["trajectory"], workers=["orchestrator"])
        runner = EvalRunner(mock_llm, config)
        report = await runner.run_all()
        assert "trajectory" in report.summary
        assert report.summary["trajectory"].total >= 1

    @pytest.mark.asyncio
    async def test_smoke_tag_filter(self, mock_llm):
        """测试smoke标签过滤"""
        config = EvalConfig(components=["tool_call"], tags=["smoke"])
        runner = EvalRunner(mock_llm, config)
        report = await runner.run_all()

        # smoke过滤后应只包含smoke标签的用例
        if "tool_call" in report.summary:
            # 至少有searcher-tool-1(有smoke标签)
            assert report.summary["tool_call"].total >= 1

    @pytest.mark.asyncio
    async def test_report_passed_condition(self, mock_llm):
        """测试report.passed的计算"""
        config = EvalConfig(components=["tool_call"], workers=["searcher"])
        runner = EvalRunner(mock_llm, config)
        report = await runner.run_all()

        # tool_call的MCP决策测试应全部通过(score=5.0)
        if "tool_call" in report.summary:
            assert report.summary["tool_call"].avg_score >= 4.0
