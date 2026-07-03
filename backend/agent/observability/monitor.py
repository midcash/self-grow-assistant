"""Monitor — 在线监控引擎: 基线管理 + 漂移检测 + 异常报警

监控四个维度:
1. 质量与行为: success_rate波动, quality_score趋势
2. 漂移与异常: 关键指标偏离基线超过阈值
3. 成本/效率/延迟: P95延迟, token消耗趋势
4. 安全/合规: 安全违规计数

基线: 7天滚动窗口的均值和标准差
异常: 当前值偏离基线 > 阈值时触发报警
"""

import json
import logging
from datetime import date, timedelta
from sqlalchemy import func

logger = logging.getLogger(__name__)

# ── 监控阈值配置 ──

MONITOR_CONFIG = {
    "baseline_window_days": 7,
    "anomaly_thresholds": {
        "success_rate": {"direction": "drop", "threshold_pct": 0.20},     # 成功率下降>20%
        "avg_latency_ms": {"direction": "spike", "threshold_factor": 2.0}, # 延迟暴涨>2x
        "p95_latency_ms": {"direction": "spike", "threshold_factor": 2.5}, # P95暴涨>2.5x
        "quality_score": {"direction": "drop", "threshold_abs": 1.0},     # 质量分下降>1.0
        "error_count": {"direction": "spike", "threshold_factor": 3.0},    # 错误数暴涨>3x
        "safety_score": {"direction": "drop", "threshold_abs": 20},       # 安全分下降>20
    },
}


class Monitor:
    """在线监控引擎 — 基线管理 + 异常检测

    Usage:
        monitor = Monitor()

        # 每日聚合后检查基线
        anomalies = monitor.check_baseline(date.today())

        # 录制新基线
        monitor.rebuild_baseline()

        # 单指标即时检查
        anomaly = monitor.check_metric("success_rate", "orchestrator", 0.65)
    """

    def __init__(self, config: dict | None = None):
        self._config = config or MONITOR_CONFIG

    # ── 基线管理 ──

    def rebuild_baseline(self) -> dict:
        """从过去7天的AgentMetrics重建所有监控基线

        Returns:
            {metric_name: {baseline_value, std_dev, ...}}
        """
        from backend.database import SessionLocal
        from backend.models import AgentMetrics, AgentBaseline, AgentQualitySample

        db = SessionLocal()
        try:
            window = self._config["baseline_window_days"]
            since = date.today() - timedelta(days=window)

            results = {}

            # 1. 从 AgentMetrics 提取 success_rate / latency / error_count
            metrics_rows = db.query(AgentMetrics).filter(
                AgentMetrics.date >= since
            ).all()

            for agent_name in set(r.agent_name for r in metrics_rows):
                agent_rows = [r for r in metrics_rows if r.agent_name == agent_name]

                # 成功率基线
                rates = [r.success_count / max(r.total_calls, 1) for r in agent_rows]
                self._store_baseline(db, "success_rate", agent_name, rates)

                # 平均延迟基线
                latencies = [r.avg_latency_ms for r in agent_rows if r.avg_latency_ms > 0]
                self._store_baseline(db, "avg_latency_ms", agent_name, latencies)

                # P95延迟基线
                p95s = [r.p95_latency_ms for r in agent_rows if r.p95_latency_ms > 0]
                self._store_baseline(db, "p95_latency_ms", agent_name, p95s)

                # 错误数基线
                errors = [r.error_count for r in agent_rows]
                self._store_baseline(db, "error_count", agent_name, errors)

                results[agent_name] = True

            # 2. 从 AgentQualitySample 提取质量基线
            quality_rows = db.query(
                func.avg(AgentQualitySample.quality_score).label("avg"),
                func.count().label("cnt"),
            ).filter(
                AgentQualitySample.created_at >= since
            ).first()

            if quality_rows and quality_rows.cnt > 0:
                # 简化: 质量基线来自全局均值
                quality_scores = [r.quality_score for r in db.query(
                    AgentQualitySample.quality_score
                ).filter(AgentQualitySample.created_at >= since).all()]
                all_scores = [q[0] for q in quality_scores]
                self._store_baseline(db, "quality_score", "all", all_scores)

            # 3. 从 AgentSafetyLog 提取安全基线
            safety_rows = db.query(
                func.avg(AgentSafetyLog.safety_score).label("avg"),
            ).filter(
                AgentSafetyLog.created_at >= since
            ).first()

            if safety_rows:
                safety_scores = [s[0] for s in db.query(
                    AgentSafetyLog.safety_score
                ).filter(AgentSafetyLog.created_at >= since).all()]
                self._store_baseline(db, "safety_score", "all", safety_scores)

            db.commit()
            logger.info(f"Monitor: baseline rebuilt ({len(results)} agents)")
            return results
        finally:
            db.close()

    def _store_baseline(self, db, metric: str, agent: str, values: list[float]):
        """计算并存储单条基线"""
        from backend.models import AgentBaseline

        if not values:
            return

        n = len(values)
        mean = sum(values) / n
        std = (sum((v - mean) ** 2 for v in values) / n) ** 0.5 if n > 1 else 0
        sorted_vals = sorted(values)

        # Upsert
        db.query(AgentBaseline).filter(
            AgentBaseline.metric_name == metric,
            AgentBaseline.agent_name == agent,
        ).delete()

        db.add(AgentBaseline(
            metric_name=metric,
            agent_name=agent,
            baseline_value=round(mean, 3),
            std_dev=round(std, 3),
            sample_count=n,
            p50_value=round(sorted_vals[int(n * 0.5)], 1) if n > 0 else 0,
            p95_value=round(sorted_vals[min(int(n * 0.95), n - 1)], 1) if n > 1 else 0,
        ))

    # ── 异常检测 ──

    def check_baseline(self, target_date: date | None = None) -> list[dict]:
        """检查当日指标是否偏离基线, 返回异常列表

        Args:
            target_date: 检查的日期

        Returns:
            异常列表, 每项含 type/severity/deviation_pct/context
        """
        if target_date is None:
            target_date = date.today()

        from backend.database import SessionLocal
        from backend.models import AgentBaseline, AgentMetrics, AgentQualitySample, AgentSafetyLog

        anomalies = []
        db = SessionLocal()
        try:
            # 获取当日指标
            today_metrics = db.query(AgentMetrics).filter(
                AgentMetrics.date == target_date
            ).all()

            thresholds = self._config["anomaly_thresholds"]

            for metric_row in today_metrics:
                agent = metric_row.agent_name

                # 检查每个指标
                checks = [
                    ("success_rate", metric_row.success_count / max(metric_row.total_calls, 1)),
                    ("avg_latency_ms", metric_row.avg_latency_ms),
                    ("p95_latency_ms", metric_row.p95_latency_ms),
                    ("error_count", metric_row.error_count),
                ]

                for metric_name, current_val in checks:
                    if current_val == 0 and metric_name != "error_count":
                        continue

                    anomaly = self._check_single(metric_name, agent, current_val, thresholds, db)
                    if anomaly:
                        anomaly["context_json"] = json.dumps({
                            "date": target_date.isoformat(),
                            "agent": agent,
                            "current": current_val,
                        }, ensure_ascii=False)
                        anomalies.append(anomaly)

            # 检查质量基线
            quality_today = db.query(
                func.avg(AgentQualitySample.quality_score).label("avg")
            ).filter(
                AgentQualitySample.created_at >= target_date,
                AgentQualitySample.created_at < target_date + timedelta(days=1),
            ).first()

            if quality_today and quality_today.avg:
                anomaly = self._check_single(
                    "quality_score", "all", quality_today.avg, thresholds, db)
                if anomaly:
                    anomalies.append(anomaly)

            # 检查安全基线
            safety_today = db.query(
                func.avg(AgentSafetyLog.safety_score).label("avg")
            ).filter(
                AgentSafetyLog.created_at >= target_date,
                AgentSafetyLog.created_at < target_date + timedelta(days=1),
            ).first()

            if safety_today and safety_today.avg:
                anomaly = self._check_single(
                    "safety_score", "all", safety_today.avg, thresholds, db)
                if anomaly:
                    anomalies.append(anomaly)

            # 持久化异常
            for a in anomalies:
                db.add(AgentAnomaly(**a))
            db.commit()

            if anomalies:
                logger.warning(f"Monitor: {len(anomalies)} anomalies detected on {target_date}")

            return anomalies
        finally:
            db.close()

    def _check_single(
        self, metric: str, agent: str, current: float,
        thresholds: dict, db,
    ) -> dict | None:
        """检查单个指标是否偏离基线"""
        from backend.models import AgentBaseline

        baseline = db.query(AgentBaseline).filter(
            AgentBaseline.metric_name == metric,
            AgentBaseline.agent_name == agent,
        ).first()

        if not baseline or baseline.baseline_value == 0:
            return None  # 无基线不报警

        threshold = thresholds.get(metric, {})

        if threshold.get("direction") == "drop":
            # 下降型: 值低于基线
            factor = threshold.get("threshold_factor") or threshold.get("threshold_pct")
            abs_threshold = threshold.get("threshold_abs")

            if factor and current < baseline.baseline_value * (1 - factor):
                deviation = (baseline.baseline_value - current) / baseline.baseline_value
            elif abs_threshold and (baseline.baseline_value - current) > abs_threshold:
                deviation = (baseline.baseline_value - current) / max(baseline.baseline_value, 0.01)
            else:
                return None

        elif threshold.get("direction") == "spike":
            # 暴涨型: 值超出基线N倍
            factor = threshold.get("threshold_factor", 2.0)
            if current > baseline.baseline_value * factor:
                deviation = (current - baseline.baseline_value) / baseline.baseline_value
            else:
                return None
        else:
            return None

        severity = "critical" if deviation > 2.0 else "warning"
        if metric == "safety_score":
            severity = "critical"  # 安全问题的严重性直接拉满

        return {
            "anomaly_type": f"{metric}_anomaly",
            "severity": severity,
            "metric_name": metric,
            "current_value": round(current, 3),
            "baseline_value": round(baseline.baseline_value, 3),
            "deviation_pct": round(deviation * 100, 1),
            "acknowledged": False,
        }

    def get_recent_anomalies(self, hours: int = 24, limit: int = 20) -> list[dict]:
        """获取最近的异常记录"""
        from backend.database import SessionLocal
        from backend.models import AgentAnomaly

        db = SessionLocal()
        try:
            since = date.today()
            rows = db.query(AgentAnomaly).filter(
                AgentAnomaly.created_at >= since
            ).order_by(
                AgentAnomaly.created_at.desc()
            ).limit(limit).all()

            return [
                {
                    "id": r.id,
                    "anomaly_type": r.anomaly_type,
                    "severity": r.severity,
                    "metric_name": r.metric_name,
                    "current_value": r.current_value,
                    "baseline_value": r.baseline_value,
                    "deviation_pct": r.deviation_pct,
                    "acknowledged": r.acknowledged,
                    "created_at": r.created_at.isoformat() if r.created_at else "",
                }
                for r in rows
            ]
        finally:
            db.close()
