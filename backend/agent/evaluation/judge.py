"""LLM-as-Judge 核心引擎

LLM-as-Judge是Agent评估的"三把通用武器"之首。
使用现有LLM插件对Worker输出进行多维度评分。

三种评分模式:
1. absolute_score — 绝对评分(1-5分,含维度评分和理由)
2. score_with_reference — 参照标准答案对比评分
3. compare_pairwise — 成对比较(A vs B),含位置偏差缓解

偏差缓解:
- Position Bias: 双向比较取平均
- Verbosity Bias: 长度比>3x时施加惩罚
- Self-Enhancement Bias: 检测评分理由中的自我强化语言
"""

import json
import logging
import re
from dataclasses import dataclass, field

from .rubric import EvalRubric
from .bias import BiasMitigator

logger = logging.getLogger(__name__)


@dataclass
class EvalScore:
    """单次评估的评分结果"""

    rubric_name: str
    dimension_scores: dict[str, float]
    overall_score: float
    reasoning: str
    confidence: float
    bias_corrections: list[str] = field(default_factory=list)
    raw_response: str = ""  # LLM原始响应,用于审计


@dataclass
class ComparisonResult:
    """成对比较结果"""

    winner: str | None  # "A", "B", None(平局)
    score_a: float
    score_b: float
    reasoning: str


class LLMJudge:
    """LLM-as-Judge 核心引擎

    使用现有LLM插件对Worker输出进行多维度评分。

    Usage:
        judge = LLMJudge(llm_plugin)

        score = await judge.score(
            rubric=prompt_rubric,
            subject="SearcherWorker system prompt",
            output=worker.system_prompt,
        )
        print(f"Score: {score.overall_score}/5")
        print(f"Dimensions: {score.dimension_scores}")
    """

    def __init__(self, llm):
        """初始化Judge

        Args:
            llm: LLM插件实例(LLMAdapterBase子类),用于评分调用
        """
        self._llm = llm
        self._judge_temperature = 0.2  # 低温度确保评分一致性

    async def score(
        self,
        rubric: EvalRubric,
        subject: str,
        output: str,
        context: dict | None = None,
    ) -> EvalScore:
        """绝对评分: 对输出按Rubric进行1-5分评分

        Args:
            rubric: 评分Rubric
            subject: 评估主题描述
            output: 被评估的输出文本
            context: 额外上下文(如输入、数据等)

        Returns:
            EvalScore含所有维度的分数、总分和理由
        """
        prompt = rubric.to_scoring_prompt(subject, output)

        if context:
            ctx_str = json.dumps(context, ensure_ascii=False)[:500]
            prompt += f"\n\n## 额外上下文\n```json\n{ctx_str}\n```"

        messages = [
            {"role": "system", "content": "你是一个严格但公正的Agent输出评估专家。只按照给定的评分标准评分，不要受文本风格或长度影响。"},
            {"role": "user", "content": prompt},
        ]

        raw = ""
        try:
            response = await self._llm.chat(
                messages,
                temperature=self._judge_temperature,
                max_tokens=1024,
            )
            raw = response.content
            score = self._parse_llm_score(raw, rubric)
            score.raw_response = raw
        except Exception as e:
            logger.warning(f"LLMJudge.score failed: {e}")
            return EvalScore(
                rubric_name=rubric.name,
                dimension_scores={d.name: 0.0 for d in rubric.dimensions},
                overall_score=0.0,
                reasoning=f"LLM评分失败: {e}",
                confidence=0.0,
                raw_response=raw,
            )

        # 应用偏差缓解
        if rubric.bias_mitigation.get("self_enhancement", False):
            score = BiasMitigator.apply_self_enhancement_check(score)

        return score

    async def compare_pairwise(
        self,
        rubric: EvalRubric,
        subject: str,
        output_a: str,
        output_b: str,
    ) -> ComparisonResult:
        """成对比较: 判断A和B哪个更好

        位置偏差缓解: 双向比较,取平均值
        - 第一次: (A, B)顺序
        - 第二次: (B, A)顺序
        - 如果两次结果不一致,降低置信度并标注

        Args:
            rubric: 评分Rubric
            subject: 评估主题描述
            output_a: 输出A
            output_b: 输出B

        Returns:
            ComparisonResult含winner和双方分数
        """
        async def _compare(first: str, second: str, first_label: str, second_label: str) -> ComparisonResult:
            prompt = rubric.to_comparison_prompt(subject, first, second)
            messages = [
                {"role": "system", "content": "你是一个公正的对比评估专家。不受顺序和长度影响,只关注质量。"},
                {"role": "user", "content": prompt},
            ]

            try:
                response = await self._llm.chat(
                    messages,
                    temperature=self._judge_temperature,
                    max_tokens=512,
                )
                return self._parse_comparison(response.content, first_label, second_label)
            except Exception as e:
                logger.warning(f"LLMJudge.compare_pairwise failed: {e}")
                return ComparisonResult(winner=None, score_a=0, score_b=0, reasoning=f"比较失败: {e}")

        if not rubric.bias_mitigation.get("position", False):
            # 不做位置偏差缓解,直接比较
            return await _compare(output_a, output_b, "A", "B")

        # 位置偏差缓解: 双向比较
        result1 = await _compare(output_a, output_b, "A", "B")
        result2 = await _compare(output_b, output_a, "B", "A")

        # 合并两次结果
        if result1.winner == "A" and result2.winner == "B":
            # 不一致: 位置偏差很大,评定为不确定
            return ComparisonResult(
                winner=None,
                score_a=(result1.score_a + result2.score_a) / 2,
                score_b=(result1.score_b + result2.score_b) / 2,
                reasoning=f"[位置偏差较大,A/B结果不一致]\n正向: {result1.reasoning}\n反向: {result2.reasoning}",
            )

        # 合并分数
        return ComparisonResult(
            winner=result1.winner,
            score_a=round((result1.score_a + result2.score_a) / 2, 1),
            score_b=round((result1.score_b + result2.score_b) / 2, 1),
            reasoning=f"[位置偏差已校正]\n{result1.reasoning}",
        )

    async def score_with_reference(
        self,
        rubric: EvalRubric,
        subject: str,
        output: str,
        reference: str,
        context: dict | None = None,
    ) -> EvalScore:
        """参照评分: 将输出与标准答案对比评分

        Args:
            rubric: 评分Rubric(其reference_answer字段会被临时覆盖)
            subject: 评估主题描述
            output: 被评估的输出文本
            reference: 标准答案/预期输出

        Returns:
            EvalScore含对比评分
        """
        temp_rubric = EvalRubric(
            name=rubric.name,
            description=rubric.description + " (参照标准答案进行对比评分)",
            dimensions=rubric.dimensions,
            reference_answer=reference,
            bias_mitigation=dict(rubric.bias_mitigation),
        )
        return await self.score(temp_rubric, subject, output, context)

    # ── 内部方法 ──

    def _parse_llm_score(self, raw: str, rubric: EvalRubric) -> EvalScore:
        """解析LLM返回的JSON评分结果

        容错策略:
        1. 提取```json...```代码块中的JSON
        2. 直接解析整个响应
        3. 正则表达式逐字段提取
        4. 返回0分(fallback)
        """
        dim_names = rubric.get_dimension_names()
        default_dims = {name: 0.0 for name in dim_names}

        # Step 1: 提取JSON代码块
        json_str = raw
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
        if match:
            json_str = match.group(1).strip()

        # Step 2: 解析JSON
        try:
            data = json.loads(json_str)
            return EvalScore(
                rubric_name=rubric.name,
                dimension_scores=data.get("dimension_scores", default_dims),
                overall_score=float(data.get("overall_score", 0)),
                reasoning=data.get("reasoning", "")[:500],
                confidence=float(data.get("confidence", 0.5)),
            )
        except (json.JSONDecodeError, ValueError):
            pass

        # Step 3: 正则表达式逐字段提取
        try:
            dim_scores = {}
            for name in dim_names:
                m = re.search(rf'"{name}"\s*:\s*([\d.]+)', raw)
                if m:
                    dim_scores[name] = float(m.group(1))
                else:
                    dim_scores[name] = 0.0

            overall_m = re.search(r'"overall_score"\s*:\s*([\d.]+)', raw)
            overall = float(overall_m.group(1)) if overall_m else 0.0

            conf_m = re.search(r'"confidence"\s*:\s*([\d.]+)', raw)
            conf = float(conf_m.group(1)) if conf_m else 0.0

            reason_m = re.search(r'"reasoning"\s*:\s*"([^"]*)"', raw)
            reason = reason_m.group(1)[:500] if reason_m else "无法提取评分理由"

            return EvalScore(
                rubric_name=rubric.name,
                dimension_scores=dim_scores,
                overall_score=overall,
                reasoning=reason,
                confidence=conf,
            )
        except Exception:
            pass

        # Step 4: 解析失败,返回0分
        logger.warning(f"LLMJudge: 无法解析评分结果,返回0分。原始响应: {raw[:200]}")
        return EvalScore(
            rubric_name=rubric.name,
            dimension_scores=default_dims,
            overall_score=0.0,
            reasoning=f"无法解析LLM评分响应: {raw[:300]}",
            confidence=0.0,
        )

    def _parse_comparison(self, raw: str, label_a: str, label_b: str) -> ComparisonResult:
        """解析LLM返回的成对比较JSON结果"""
        json_str = raw
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw)
        if match:
            json_str = match.group(1).strip()

        try:
            data = json.loads(json_str)
            winner = data.get("winner")
            # 如果标签不是"A"/"B",进行映射
            if winner == label_a:
                winner = "A"
            elif winner == label_b:
                winner = "B"
            elif winner == "tie":
                winner = None

            return ComparisonResult(
                winner=winner,
                score_a=float(data.get("score_a", 0)),
                score_b=float(data.get("score_b", 0)),
                reasoning=data.get("reasoning", "")[:500],
            )
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"LLMJudge: 无法解析比较结果。原始响应: {raw[:200]}")
            return ComparisonResult(
                winner=None,
                score_a=0,
                score_b=0,
                reasoning=f"无法解析比较结果: {raw[:300]}",
            )
