"""MetricsAggregator — Agent 每日指标聚合"""

import logging
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func

logger = logging.getLogger(__name__)


class MetricsAggregator:
    """Agent 指标聚合器

    用法:
        agg = MetricsAggregator()
        agg.aggregate_daily(date.today())
        metrics = agg.get_metrics(days=7, agent_name="searcher")
    """

    def aggregate_daily(self, target_date: date | None = None) -> dict[str, int]:
        """从 AgentTrace 聚合指定日期的指标，写入 agent_metrics 表。返回 {agent_name: rows_written}"""
        if target_date is None:
            target_date = date.today()

        try:
            from backend.database import SessionLocal
            from backend.models import AgentTrace, AgentMetrics

            db = SessionLocal()
            try:
                # 查询当天的所有 trace 记录，按 agent_name 分组
                day_start = target_date
                day_end = target_date + timedelta(days=1)

                rows = db.query(
                    AgentTrace.agent_name,
                    func.count().label("total"),
                    func.sum(
                        func.case((AgentTrace.success == True, 1), else_=0)
                    ).label("successes"),
                    func.sum(
                        func.case((AgentTrace.success == False, 1), else_=0)
                    ).label("errors"),
                    func.avg(AgentTrace.latency_ms).label("avg_ms"),
                ).filter(
                    AgentTrace.created_at >= day_start,
                    AgentTrace.created_at < day_end,
                ).group_by(AgentTrace.agent_name).all()

                result = {}
                for row in rows:
                    # 计算 P50 / P95（查询该 agent 的所有延迟值）
                    latency_rows = db.query(AgentTrace.latency_ms).filter(
                        AgentTrace.agent_name == row.agent_name,
                        AgentTrace.created_at >= day_start,
                        AgentTrace.created_at < day_end,
                    ).order_by(AgentTrace.latency_ms).all()
                    latencies = sorted([r[0] for r in latency_rows if r[0] is not None])
                    n = len(latencies)
                    p50 = latencies[int(n * 0.5)] if n > 0 else 0
                    p95 = latencies[int(n * 0.95)] if n > 1 else (latencies[0] if n == 1 else 0)

                    # Upsert: 删除旧记录 → 插入新记录
                    db.query(AgentMetrics).filter(
                        AgentMetrics.date == target_date,
                        AgentMetrics.agent_name == row.agent_name,
                    ).delete()

                    db.add(AgentMetrics(
                        date=target_date,
                        agent_name=row.agent_name,
                        total_calls=row.total,
                        success_count=row.successes or 0,
                        error_count=row.errors or 0,
                        avg_latency_ms=int(row.avg_ms or 0),
                        p50_latency_ms=p50,
                        p95_latency_ms=p95,
                        total_token_estimate=0,
                    ))
                    result[row.agent_name] = 1

                db.commit()
                logger.info(f"MetricsAggregator: aggregated {target_date} → {len(result)} agents")
                return result
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"MetricsAggregator failed: {e}")
            return {}

    def get_metrics(
        self, days: int = 7, agent_name: str | None = None
    ) -> list[dict[str, Any]]:
        """查询 AgentMetrics，返回最近 N 天的指标列表"""
        try:
            from backend.database import SessionLocal
            from backend.models import AgentMetrics

            db = SessionLocal()
            try:
                since = date.today() - timedelta(days=days)
                q = db.query(AgentMetrics).filter(AgentMetrics.date >= since)
                if agent_name:
                    q = q.filter(AgentMetrics.agent_name == agent_name)
                rows = q.order_by(AgentMetrics.date.desc(), AgentMetrics.agent_name).all()

                return [
                    {
                        "date": r.date.isoformat() if r.date else "",
                        "agent_name": r.agent_name,
                        "total_calls": r.total_calls,
                        "success_count": r.success_count,
                        "error_count": r.error_count,
                        "avg_latency_ms": r.avg_latency_ms,
                        "p50_latency_ms": r.p50_latency_ms,
                        "p95_latency_ms": r.p95_latency_ms,
                        "total_token_estimate": r.total_token_estimate,
                    }
                    for r in rows
                ]
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"MetricsAggregator get_metrics failed: {e}")
            return []
