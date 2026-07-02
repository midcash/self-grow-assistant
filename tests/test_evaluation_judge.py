"""LLM-as-Judge 单元测试

测试 rubric 生成、LLMJudge 评分、JSON 解析、偏差缓解。
LLM 调用使用模拟对象，不依赖外部 API。
"""

import json
import pytest
from unittest.mock import MagicMock, AsyncMock

from backend.agent.evaluation.rubric import EvalRubric, RubricDimension
from backend.agent.evaluation.judge import LLMJudge, EvalScore, ComparisonResult
from backend.agent.evaluation.bias import BiasMitigator


# ── 测试 Fixtures ──

@pytest.fixture
def clarity_dim():
    return RubricDimension(
        name="clarity",
        description="提示词是否清晰",
        scale={
            1: "完全模糊",
            2: "部分清晰",
            3: "基本清晰",
            4: "清晰",
            5: "非常清晰",
        },
        weight=1.0,
    )


@pytest.fixture
def accuracy_dim():
    return RubricDimension(
        name="accuracy",
        description="输出是否准确",
        scale={
            1: "完全错误",
            2: "大部分错误",
            3: "部分准确",
            4: "基本准确",
            5: "完全准确",
        },
        weight=1.0,
    )


@pytest.fixture
def sample_rubric(clarity_dim, accuracy_dim):
    return EvalRubric(
        name="test-rubric",
        description="测试评分rubric",
        dimensions=[clarity_dim, accuracy_dim],
    )


@pytest.fixture
def mock_llm():
    """创建模拟LLM,返回预定义的评分JSON"""
    llm = MagicMock()
    llm.chat = AsyncMock()
    return llm


def _make_score_json(dim_scores: dict, overall: float = 4.0, reasoning: str = "测试评分", confidence: float = 0.9) -> str:
    """快速构造LLM返回的评分JSON"""
    data = {
        "dimension_scores": dim_scores,
        "overall_score": overall,
        "reasoning": reasoning,
        "confidence": confidence,
    }
    return json.dumps(data)


# ── Rubric 测试 ──

class TestRubric:
    """EvalRubric 和 RubricDimension 数据结构"""

    def test_dimension_requires_scale(self):
        with pytest.raises(ValueError):
            RubricDimension(name="x", description="x", scale={})

    def test_dimension_scale_must_be_1_to_5(self):
        with pytest.raises(ValueError):
            RubricDimension(name="x", description="x", scale={0: "bad", 6: "good"})

    def test_to_scoring_prompt_contains_dimensions(self, sample_rubric):
        prompt = sample_rubric.to_scoring_prompt(
            subject="Test subject",
            output="Test output",
        )
        assert "clarity" in prompt
        assert "accuracy" in prompt
        assert "Test subject" in prompt
        assert "Test output" in prompt
        assert "clarity" in prompt  # 维度名称在prompt中出现

    def test_to_scoring_prompt_with_reference(self, clarity_dim):
        rubric = EvalRubric(
            name="ref-test",
            description="带参考的评估",
            dimensions=[clarity_dim],
            reference_answer="expected answer",
        )
        prompt = rubric.to_scoring_prompt(subject="s", output="o")
        assert "expected answer" in prompt

    def test_to_comparison_prompt(self, sample_rubric):
        prompt = sample_rubric.to_comparison_prompt(
            subject="Test",
            output_a="Output A",
            output_b="Output B",
        )
        assert "Output A" in prompt
        assert "Output B" in prompt
        assert "winner" in prompt.lower() or "Winner" in prompt

    def test_get_dimension_names(self, sample_rubric):
        names = sample_rubric.get_dimension_names()
        assert "clarity" in names
        assert "accuracy" in names


# ── EvalScore 测试 ──

class TestEvalScore:
    """EvalScore 数据结构"""

    def test_eval_score_defaults(self):
        score = EvalScore(
            rubric_name="test",
            dimension_scores={"clarity": 4.0},
            overall_score=4.0,
            reasoning="good",
            confidence=0.9,
        )
        assert score.overall_score == 4.0
        assert score.bias_corrections == []
        assert score.raw_response == ""


# ── LLMJudge 评分测试 ──

class TestLLMJudge:
    """LLMJudge 核心评分逻辑"""

    @pytest.mark.asyncio
    async def test_score_valid_json(self, sample_rubric, mock_llm):
        """LLM返回合法JSON时正确解析"""
        mock_llm.chat.return_value.content = _make_score_json(
            {"clarity": 4, "accuracy": 5}, overall=4.5, reasoning="清晰且准确"
        )

        judge = LLMJudge(mock_llm)
        score = await judge.score(sample_rubric, "test subject", "test output")

        assert score.rubric_name == "test-rubric"
        assert score.dimension_scores["clarity"] == 4
        assert score.dimension_scores["accuracy"] == 5
        assert score.overall_score == 4.5
        assert score.confidence == 0.9

    @pytest.mark.asyncio
    async def test_score_json_in_code_block(self, sample_rubric, mock_llm):
        """LLM返回```json...```包裹的JSON时正确解析"""
        json_str = _make_score_json({"clarity": 3, "accuracy": 3}, overall=3.0)
        mock_llm.chat.return_value.content = f"```json\n{json_str}\n```"

        judge = LLMJudge(mock_llm)
        score = await judge.score(sample_rubric, "test", "test")

        assert score.dimension_scores["clarity"] == 3
        assert score.overall_score == 3.0

    @pytest.mark.asyncio
    async def test_score_fallback_regex_extract(self, sample_rubric, mock_llm):
        """LLM返回非标准格式时尝试正则提取"""
        mock_llm.chat.return_value.content = 'score: {"overall_score": 4.2, "dimension_scores": {"clarity": 4.0, "accuracy": 4.5}, "reasoning": "good enough", "confidence": 0.85}'

        judge = LLMJudge(mock_llm)
        score = await judge.score(sample_rubric, "test", "test")

        assert score.overall_score == 4.2
        assert score.dimension_scores["clarity"] == 4.0
        assert score.dimension_scores["accuracy"] == 4.5

    @pytest.mark.asyncio
    async def test_score_unparseable_returns_zero(self, sample_rubric, mock_llm):
        """LLM返回完全无法解析的文本时返回0分"""
        mock_llm.chat.return_value.content = "这是一段完全无法解析的评分文本"

        judge = LLMJudge(mock_llm)
        score = await judge.score(sample_rubric, "test", "test")

        assert score.overall_score == 0.0
        assert score.confidence == 0.0
        # 无法解析的文本会进入regex fallback,也返回0分和0置信度

    @pytest.mark.asyncio
    async def test_score_llm_call_fails(self, sample_rubric, mock_llm):
        """LLM调用异常时返回0分"""
        mock_llm.chat.side_effect = Exception("LLM连接失败")

        judge = LLMJudge(mock_llm)
        score = await judge.score(sample_rubric, "test", "test")

        assert score.overall_score == 0.0
        assert score.confidence == 0.0
        assert "LLM评分失败" in score.reasoning

    @pytest.mark.asyncio
    async def test_score_with_reference(self, sample_rubric, mock_llm):
        """参照评分模式: reference_answer被注入"""
        mock_llm.chat.return_value.content = _make_score_json(
            {"clarity": 5, "accuracy": 5}, overall=5.0
        )

        judge = LLMJudge(mock_llm)
        score = await judge.score_with_reference(
            sample_rubric, "test", "test output", "expected reference"
        )

        assert score.overall_score == 5.0
        assert score.rubric_name == "test-rubric"

    @pytest.mark.asyncio
    async def test_score_uses_low_temperature(self, sample_rubric, mock_llm):
        """评分使用temperature=0.2确保一致性"""
        mock_llm.chat.return_value.content = _make_score_json({"clarity": 3, "accuracy": 3})

        judge = LLMJudge(mock_llm)
        await judge.score(sample_rubric, "test", "test")

        call_kwargs = mock_llm.chat.call_args[1]
        assert call_kwargs["temperature"] == 0.2


# ── 成对比较测试 ──

class TestPairwiseComparison:
    """LLMJudge.compare_pairwise"""

    @pytest.fixture
    def simple_rubric(self, clarity_dim):
        return EvalRubric(
            name="comparison-test",
            description="对比测试",
            dimensions=[clarity_dim],
        )

    def _make_comparison_json(self, winner: str, score_a: float, score_b: float, reasoning: str = "ok") -> str:
        return json.dumps({
            "winner": winner,
            "score_a": score_a,
            "score_b": score_b,
            "reasoning": reasoning,
        })

    @pytest.mark.asyncio
    async def test_compare_a_wins(self, simple_rubric, mock_llm):
        mock_llm.chat.return_value.content = self._make_comparison_json("A", 4.0, 2.0)
        simple_rubric.bias_mitigation["position"] = False  # 关闭位置偏差,避免双向调用

        judge = LLMJudge(mock_llm)
        result = await judge.compare_pairwise(simple_rubric, "test", "output A", "output B")

        assert result.winner == "A"
        assert result.score_a > result.score_b

    @pytest.mark.asyncio
    async def test_compare_b_wins(self, simple_rubric, mock_llm):
        mock_llm.chat.return_value.content = self._make_comparison_json("B", 2.0, 4.0)
        simple_rubric.bias_mitigation["position"] = False  # 关闭位置偏差

        judge = LLMJudge(mock_llm)
        result = await judge.compare_pairwise(simple_rubric, "test", "output A", "output B")

        assert result.winner == "B"

    @pytest.mark.asyncio
    async def test_compare_position_bias_mitigation(self, simple_rubric, mock_llm):
        """位置偏差缓解: 双向比较取平均"""
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            response = MagicMock()
            if call_count[0] == 1:
                response.content = self._make_comparison_json("A", 4.0, 2.0)
            else:
                response.content = self._make_comparison_json("A", 4.5, 1.5)
            return response

        mock_llm.chat = AsyncMock(side_effect=side_effect)

        simple_rubric.bias_mitigation["position"] = True
        judge = LLMJudge(mock_llm)
        result = await judge.compare_pairwise(simple_rubric, "test", "output A", "output B")

        assert call_count[0] == 2  # 调用了两次
        assert result.score_a > 0
        assert result.score_b > 0

    @pytest.mark.asyncio
    async def test_compare_position_bias_disabled(self, simple_rubric, mock_llm):
        """禁用位置偏差缓解时只调用一次"""
        mock_llm.chat.return_value.content = self._make_comparison_json("A", 4.0, 2.0)

        simple_rubric.bias_mitigation["position"] = False
        judge = LLMJudge(mock_llm)
        await judge.compare_pairwise(simple_rubric, "test", "output A", "output B")

        assert mock_llm.chat.call_count == 1


# ── JSON解析测试 ──

class TestScoreParsing:

    @pytest.fixture
    def dim(self):
        return RubricDimension(name="x", description="x", scale={1: "bad", 5: "good"}, weight=1.0)

    @pytest.fixture
    def rubric(self, dim):
        return EvalRubric(name="parse-test", description="解析测试", dimensions=[dim])

    def test_parse_valid_json(self, rubric):
        judge = LLMJudge(None)  # 不需要LLM
        raw = json.dumps({
            "dimension_scores": {"x": 4},
            "overall_score": 4.0,
            "reasoning": "good",
            "confidence": 0.9,
        })
        score = judge._parse_llm_score(raw, rubric)
        assert score.overall_score == 4.0
        assert score.dimension_scores["x"] == 4
        assert score.confidence == 0.9

    def test_parse_json_in_code_block(self, rubric):
        judge = LLMJudge(None)
        raw = '```json\n{"dimension_scores": {"x": 5}, "overall_score": 5.0, "reasoning": "perfect", "confidence": 1.0}\n```'
        score = judge._parse_llm_score(raw, rubric)
        assert score.overall_score == 5.0

    def test_parse_malformed_json_regex_extract(self, rubric):
        judge = LLMJudge(None)
        raw = '评分结果: "overall_score": 3.5, "dimension_scores": {"x": 3.5}, "reasoning": "ok ok ok ok ok", "confidence": 0.7'
        score = judge._parse_llm_score(raw, rubric)
        assert score.overall_score == 3.5
        assert score.dimension_scores["x"] == 3.5

    def test_parse_completely_invalid(self, rubric):
        judge = LLMJudge(None)
        raw = "这是一段无法解析的文本,没有任何JSON结构"
        score = judge._parse_llm_score(raw, rubric)
        assert score.overall_score == 0.0
        assert score.confidence == 0.0


class TestComparisonParsing:

    def test_parse_valid_comparison(self):
        judge = LLMJudge(None)
        raw = json.dumps({"winner": "A", "score_a": 4.0, "score_b": 2.0, "reasoning": "A is better"})
        result = judge._parse_comparison(raw, "A", "B")
        assert result.winner == "A"
        assert result.score_a == 4.0
        assert result.score_b == 2.0

    def test_parse_tie(self):
        judge = LLMJudge(None)
        raw = json.dumps({"winner": "tie", "score_a": 3.0, "score_b": 3.0, "reasoning": "tie"})
        result = judge._parse_comparison(raw, "A", "B")
        assert result.winner is None

    def test_parse_invalid_comparison_returns_zeros(self):
        judge = LLMJudge(None)
        raw = "invalid"
        result = judge._parse_comparison(raw, "A", "B")
        assert result.winner is None
        assert result.score_a == 0


# ── 偏差缓解测试 ──

class TestBiasMitigation:

    @pytest.fixture
    def sample_score(self):
        return EvalScore(
            rubric_name="test",
            dimension_scores={"clarity": 4.5, "accuracy": 4.0},
            overall_score=4.3,
            reasoning="输出非常出色，完美好输出无懈可击",
            confidence=0.9,
            raw_response="raw",
        )

    def test_position_swap_normal(self):
        """位置偏差<1.0时取平均"""
        s1 = EvalScore(
            rubric_name="test",
            dimension_scores={"x": 4.0},
            overall_score=4.0,
            reasoning="",
            confidence=0.9,
        )
        s2 = EvalScore(
            rubric_name="test",
            dimension_scores={"x": 3.5},
            overall_score=3.5,
            reasoning="",
            confidence=0.9,
        )

        result = BiasMitigator.position_swap_scores(s1, s2)
        assert result.overall_score == 3.8  # (4.0+3.5)/2 = 3.75 → round to 3.8
        assert "position_swap" in result.bias_corrections

    def test_position_swap_high_variance(self):
        """位置偏差>1.0时取较低分"""
        s1 = EvalScore(
            rubric_name="test",
            dimension_scores={"x": 5.0},
            overall_score=5.0,
            reasoning="",
            confidence=0.9,
        )
        s2 = EvalScore(
            rubric_name="test",
            dimension_scores={"x": 3.0},
            overall_score=3.0,
            reasoning="",
            confidence=0.9,
        )

        result = BiasMitigator.position_swap_scores(s1, s2)
        assert result.overall_score == 3.0  # 取较低分（min）
        assert "high_position_variance" in str(result.bias_corrections)

    def test_verbosity_penalty_no_penalty(self, sample_score):
        """长度比<=3时不惩罚"""
        result = BiasMitigator.verbosity_penalty(
            sample_score, output_length=200, ref_length=100
        )
        assert result.overall_score == sample_score.overall_score  # 不变

    def test_verbosity_penalty_moderate(self, sample_score):
        """长度比3-5时惩罚10%"""
        result = BiasMitigator.verbosity_penalty(
            sample_score, output_length=350, ref_length=100
        )
        assert result.overall_score == round(4.3 * 0.9, 1)

    def test_verbosity_penalty_severe(self, sample_score):
        """长度比>5时惩罚20%"""
        result = BiasMitigator.verbosity_penalty(
            sample_score, output_length=600, ref_length=100
        )
        assert result.overall_score == round(4.3 * 0.8, 1)

    def test_verbosity_no_reference(self, sample_score):
        """无参考时不惩罚（ref_length=0）"""
        result = BiasMitigator.verbosity_penalty(
            sample_score, output_length=200, ref_length=0
        )
        assert result.overall_score == sample_score.overall_score

    def test_detect_self_enhancement(self):
        """检测评分理由中的自我强化语言"""
        level = BiasMitigator.detect_self_enhancement("输出非常出色，完美好输出")
        assert level > 0

    def test_detect_no_self_enhancement(self):
        """正常评分理由不触发"""
        level = BiasMitigator.detect_self_enhancement("输出基本符合要求，但步骤描述可以更详细")
        assert level == 0.0

    def test_apply_self_enhancement_check(self, sample_score):
        """应用自我强化检测后confidence降低"""
        result = BiasMitigator.apply_self_enhancement_check(sample_score)
        assert result.confidence < sample_score.confidence  # confidence降低
        assert "self_enhancement_detected" in str(result.bias_corrections)
