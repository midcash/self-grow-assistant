"""偏差缓解策略 — 缓解LLM-as-Judge的常见偏差

三种偏差:
1. Position Bias(位置偏差): LLM倾向偏好排在前面的选项
2. Verbosity Bias(冗长偏差): LLM倾向给更长的输出打高分
3. Self-Enhancement Bias(自我强化偏差): LLM倾向给自己的输出打高分

缓解方法参考: Google Gemini Judge Cookbook + 美团龙猫论文
"""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .judge import EvalScore


class BiasMitigator:
    """偏差缓解器 — 所有方法为静态方法"""

    # ── 位置偏差 ──

    @staticmethod
    def position_swap_scores(
        score_original: "EvalScore",
        score_swapped: "EvalScore",
    ) -> "EvalScore":
        """双向评分的平均值，消除位置偏差。

        当两次评分差距>1.0时，取较低分并标注不确定。
        """
        from .judge import EvalScore as _EvalScore

        diff = abs(score_original.overall_score - score_swapped.overall_score)
        avg_score = (score_original.overall_score + score_swapped.overall_score) / 2

        avg_dim = {}
        all_dims = set(score_original.dimension_scores.keys()) | set(score_swapped.dimension_scores.keys())
        for d in all_dims:
            a = score_original.dimension_scores.get(d, 0)
            b = score_swapped.dimension_scores.get(d, 0)
            avg_dim[d] = round((a + b) / 2, 1)

        corrections = list(score_original.bias_corrections)
        if "position_swap" not in corrections:
            corrections.append("position_swap")

        if diff > 1.0:
            corrections.append(f"high_position_variance({diff:.1f})")
            avg_score = min(score_original.overall_score, score_swapped.overall_score)

        return _EvalScore(
            rubric_name=score_original.rubric_name,
            dimension_scores=avg_dim,
            overall_score=round(avg_score, 1),
            reasoning=f"[位置偏差已校正|原始={score_original.overall_score:.1f}|交换后={score_swapped.overall_score:.1f}]\n{score_original.reasoning}",
            confidence=min(score_original.confidence, score_swapped.confidence),
            bias_corrections=corrections,
            raw_response=score_original.raw_response,
        )

    # ── 冗长偏差 ──

    @staticmethod
    def verbosity_penalty(score: "EvalScore", output_length: int, ref_length: int) -> "EvalScore":
        """当输出长度远大于参考长度时施加惩罚。

        length_ratio > 3.0: 惩罚10%
        length_ratio > 5.0: 惩罚20%
        """
        from .judge import EvalScore as _EvalScore

        if ref_length <= 0:
            return score  # 无参考时不惩罚

        ratio = output_length / ref_length
        if ratio <= 3.0:
            return score  # 正常范围

        if ratio > 5.0:
            penalty = 0.20
        else:
            penalty = 0.10

        adjusted_score = round(score.overall_score * (1 - penalty), 1)
        corrections = list(score.bias_corrections) + [f"verbosity_penalty(ratio={ratio:.1f},penalty={penalty})"]

        return _EvalScore(
            rubric_name=score.rubric_name,
            dimension_scores=dict(score.dimension_scores),
            overall_score=adjusted_score,
            reasoning=f"[冗长偏差已校正|长度比={ratio:.1f}|惩罚={penalty:.0%}]\n{score.reasoning}",
            confidence=score.confidence,
            bias_corrections=corrections,
            raw_response=score.raw_response,
        )

    # ── 自我强化偏差 ──

    @staticmethod
    def detect_self_enhancement(reasoning: str) -> float:
        """检测评分理由中的自我强化语言。

        返回0-1的自我强化程度分数。
        """
        indicators = [
            r"完[美善].*输出",
            r"非常出色",
            r"无懈可击",
            r"完美无缺",
            r"excellent.*output",
            r"flawless",
            r"almost perfect",
        ]

        matches = 0
        for pattern in indicators:
            if re.search(pattern, reasoning, re.IGNORECASE):
                matches += 1

        if matches == 0:
            return 0.0
        elif matches <= 2:
            return 0.25
        elif matches <= 4:
            return 0.5
        else:
            return 0.75

    @staticmethod
    def apply_self_enhancement_check(score: "EvalScore") -> "EvalScore":
        """检查并标记自我强化偏差"""
        from .judge import EvalScore as _EvalScore

        se_level = BiasMitigator.detect_self_enhancement(score.reasoning)
        if se_level == 0.0:
            return score

        corrections = list(score.bias_corrections) + [f"self_enhancement_detected(level={se_level})"]

        return _EvalScore(
            rubric_name=score.rubric_name,
            dimension_scores=dict(score.dimension_scores),
            overall_score=score.overall_score,
            reasoning=f"[自我强化偏差已检测|级别={se_level}]\n{score.reasoning}",
            confidence=max(0.0, score.confidence - se_level * 0.3),
            bias_corrections=corrections,
            raw_response=score.raw_response,
        )
