"""TraceCollector — 结构化编排 Trace 写入

双写策略:
- SQLite agent_traces 表（结构化，可查询）
- 保留现有 Markdown plan-logs（向后兼容）
"""

import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class TraceCollector:
    """编排 Trace 收集器（单例模式）

    用法:
        tracer = TraceCollector()

        # 开始一次编排
        orch_id = tracer.start_orchestration(user_message[:200])

        # 记录各阶段 span
        tracer.record_span(
            orchestration_id=orch_id,
            span_type="plan",
            agent_name="orchestrator",
            objective=intent,
            input_summary=user_message[:300],
            output_summary=json.dumps(plan, ensure_ascii=False)[:500],
            latency_ms=plan_elapsed_ms,
            success=True,
        )

        # 写入 worker 执行
        tracer.record_span(
            orchestration_id=orch_id,
            span_type="worker_execute",
            agent_name="searcher",
            objective=brief.objective,
            input_summary=json.dumps({
                "task_id": brief.task_id,
                "constraints": brief.constraints,
            }, ensure_ascii=False)[:500],
            output_summary=result.content[:300],
            latency_ms=elapsed_ms,
            success=result.success,
            error_message="" if result.success else result.content[:300],
            metadata=json.dumps({
                "confidence": result.confidence,
                "sources": result.sources,
            }, ensure_ascii=False),
        )

        # 完成编排
        tracer.flush()
    """

    def __init__(self):
        self._pending_spans: list[dict] = []

    def start_orchestration(self, user_message: str = "") -> str:
        """开始一次编排，返回 orchestration_id"""
        import uuid
        orch_id = str(uuid.uuid4())[:8]
        logger.debug(f"TraceCollector: start orchestration {orch_id}")
        return orch_id

    def record_span(
        self,
        orchestration_id: str,
        span_type: str,
        agent_name: str = "orchestrator",
        parent_span_id: int | None = None,
        objective: str = "",
        input_summary: str = "",
        output_summary: str = "",
        latency_ms: int = 0,
        success: bool = True,
        error_message: str = "",
        metadata: str = "{}",
    ) -> None:
        """记录一个 span（缓存，待 flush 写入数据库）"""
        span = {
            "orchestration_id": orchestration_id,
            "span_type": span_type,
            "agent_name": agent_name,
            "parent_span_id": parent_span_id,
            "objective": objective[:200],
            "input_summary": input_summary[:500],
            "output_summary": output_summary[:500],
            "latency_ms": latency_ms,
            "success": success,
            "error_message": error_message[:300],
            "metadata_json": metadata if isinstance(metadata, str) else json.dumps(metadata, ensure_ascii=False),
        }
        self._pending_spans.append(span)
        logger.debug(f"TraceCollector: record {span_type}/{agent_name} ({latency_ms}ms)")

    def flush(self) -> int:
        """将所有缓存的 span 写入 SQLite，返回写入数量"""
        if not self._pending_spans:
            return 0
        try:
            from backend.database import SessionLocal
            from backend.models import AgentTrace

            db = SessionLocal()
            try:
                count = 0
                for s in self._pending_spans:
                    db.add(AgentTrace(
                        orchestration_id=s["orchestration_id"],
                        span_type=s["span_type"],
                        agent_name=s["agent_name"],
                        parent_span_id=s["parent_span_id"],
                        objective=s["objective"],
                        input_summary=s["input_summary"],
                        output_summary=s["output_summary"],
                        latency_ms=s["latency_ms"],
                        success=s["success"],
                        error_message=s["error_message"],
                        metadata_json=s["metadata_json"],
                    ))
                    count += 1
                db.commit()
                logger.info(f"TraceCollector: flushed {count} spans to SQLite")
            finally:
                db.close()

            self._pending_spans.clear()
            return count
        except Exception as e:
            logger.warning(f"TraceCollector flush failed: {e}")
            return 0

    def get_pending_count(self) -> int:
        """返回待写入的 span 数量"""
        return len(self._pending_spans)


# 模块级单例
_tracer_singleton: TraceCollector | None = None


def get_tracer() -> TraceCollector:
    """获取全局 TraceCollector 单例"""
    global _tracer_singleton
    if _tracer_singleton is None:
        _tracer_singleton = TraceCollector()
    return _tracer_singleton
