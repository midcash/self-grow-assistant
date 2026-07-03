"""QualitySampler — 生产聊天质量抽样评分

对生产环境的聊天进行周期性抽样(默认1/10)，
使用轻量级LLM-as-Judge快速评分，检测质量漂移。

与评估系统(EvalRunner)的区别:
- EvalRunner: 离线, 用预定义测试集, 完整多维度评分
- QualitySampler: 在线, 对真实聊天抽样, 轻量2维度评分(relevance + coherence)
"""

import json
import logging
import random
from datetime import date
from backend.agent.evaluation.rubric import EvalRubric, RubricDimension

logger = logging.getLogger(__name__)

# 轻量级快速评分Rubric (仅2维度, 减少token消耗)
QUALITY_RUBRIC = EvalRubric(
    name="online-quality-check",
    description="快速评估Agent在线回复质量: 相关性 + 连贯性",
    dimensions=[
        RubricDimension(
            name="relevance",
            description="回复是否紧扣用户问题, 有无答非所问",
            scale={
                1: "完全偏离用户问题",
                2: "与问题关联弱, 大部分不相关",
                3: "基本回答用户问题",
                4: "准确回答, 有补充价值",
                5: "精准回答, 洞察深刻",
            },
            weight=1.0,
        ),
        RubricDimension(
            name="coherence",
            description="回复在逻辑和语言上是否连贯, 无矛盾或混乱",
            scale={
                1: "逻辑混乱, 语句不连贯",
                2: "部分连贯, 有跳跃或矛盾",
                3: "基本连贯, 可理解",
                4: "逻辑清晰, 表述完整",
                5: "过度连贯, 表达精准流畅",
            },
            weight=1.0,
        ),
    ],
)


class QualitySampler:
    """生产聊天质量抽样评分器

    Usage:
        sampler = QualitySampler(llm, sampling_rate=10)
        await sampler.maybe_sample(
            orch_id="abc123",
            user_message="帮我安排...",
            agent_reply="好的, 我已经...",
            workers_used=["searcher", "executor"],
        )
    """

    def __init__(self, llm, sampling_rate: int = 10):
        self._llm = llm
        self._rate = max(1, sampling_rate)
        self._counter = 0
        self._scores: list[float] = []  # 内存中保存最近评分

    def _should_sample(self) -> bool:
        """按采样率判断是否触发"""
        self._counter += 1
        return self._counter % self._rate == 0

    async def maybe_sample(
        self,
        orchestration_id: str,
        user_message: str,
        agent_reply: str,
        workers_used: list[str],
    ) -> dict | None:
        """如果命中采样率, 进行质量评分并持久化

        Returns:
            评分结果dict或None(未命中采样)
        """
        if not self._should_sample():
            return None

        # 轻量评分
        from backend.agent.evaluation.judge import LLMJudge

        judge = LLMJudge(self._llm)
        score = await judge.score(
            rubric=QUALITY_RUBRIC,
            subject=f"用户问题: {user_message[:200]}",
            output=agent_reply[:1500],
            context={"workers_used": workers_used},
        )

        # 内存记录
        self._scores.append(score.overall_score)
        if len(self._scores) > 100:
            self._scores = self._scores[-100:]

        # 持久化
        try:
            self._persist(orchestration_id, user_message, agent_reply, workers_used, score)
        except Exception as e:
            logger.warning(f"QualitySampler persist failed: {e}")

        return {
            "quality_score": score.overall_score,
            "dimensions": score.dimension_scores,
            "reasoning": score.reasoning[:300],
        }

    def _persist(self, orch_id, user_msg, reply, workers, score):
        from backend.database import SessionLocal
        from backend.models import AgentQualitySample

        db = SessionLocal()
        try:
            db.add(AgentQualitySample(
                orchestration_id=orch_id,
                user_message=user_msg[:500],
                agent_reply=reply[:1000],
                workers_used=",".join(workers[:5]) if workers else "",
                quality_score=score.overall_score,
                quality_dims_json=json.dumps(score.dimension_scores, ensure_ascii=False),
                quality_reasoning=score.reasoning[:500],
                sampling_rate=self._rate,
            ))
            db.commit()
        finally:
            db.close()

    def get_recent_avg(self) -> float:
        """获取内存中最近评分的均值"""
        if not self._scores:
            return 0.0
        return round(sum(self._scores) / len(self._scores), 1)

    @staticmethod
    def aggregate_daily(target_date: date | None = None) -> dict:
        """聚合某天的质量样本统计"""
        if target_date is None:
            target_date = date.today()

        from backend.database import SessionLocal
        from backend.models import AgentQualitySample
        from sqlalchemy import func
        from datetime import timedelta

        db = SessionLocal()
        try:
            day_start = target_date
            day_end = target_date + timedelta(days=1)

            row = db.query(
                func.count().label("total"),
                func.avg(AgentQualitySample.quality_score).label("avg_score"),
                func.min(AgentQualitySample.quality_score).label("min_score"),
                func.max(AgentQualitySample.quality_score).label("max_score"),
            ).filter(
                AgentQualitySample.created_at >= day_start,
                AgentQualitySample.created_at < day_end,
            ).first()

            return {
                "date": target_date.isoformat(),
                "total_samples": row.total or 0,
                "avg_score": round(row.avg_score or 0, 1),
                "min_score": round(row.min_score or 0, 1),
                "max_score": round(row.max_score or 0, 1),
            }
        finally:
            db.close()
