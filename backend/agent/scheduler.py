"""定时调度器 — 基于 APScheduler 的 Cron 调度

每 20 分钟触发优先级评估 (默认: */20 * * * *)
"""

import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False
    logger.warning("APScheduler not installed. Install with: pip install apscheduler")


class AgentScheduler:
    """智能体定时调度器

    管理 20 分钟间隔的优先级评估任务。
    支持 cron 表达式修改。
    """

    def __init__(self, cron_expr: str = "*/20 * * * *"):
        self._cron_expr = cron_expr
        self._scheduler: AsyncIOScheduler | None = None
        self._job_id: str | None = None
        self._evaluate_callback = None
        self._running = False

    @property
    def cron_expr(self) -> str:
        return self._cron_expr

    @property
    def is_running(self) -> bool:
        return self._running

    # === 启动 / 停止 ===

    def start(self, evaluate_callback) -> None:
        """启动定时调度

        Args:
            evaluate_callback: async callable, 每次触发时调用
        """
        if not HAS_APSCHEDULER:
            logger.error("Cannot start scheduler: APScheduler not installed")
            return

        self._evaluate_callback = evaluate_callback
        self._scheduler = AsyncIOScheduler()

        self._job_id = self._scheduler.add_job(
            self._run_evaluation,
            "cron",
            minute=self._parse_cron_minute(),
            id="agent_priority_eval",
            name="Priority Evaluation",
            replace_existing=True,
        ).id

        self._scheduler.start()
        self._running = True
        logger.info(f"Scheduler started with cron: {self._cron_expr}")

    def stop(self) -> None:
        """停止定时调度"""
        if self._scheduler and self._running:
            self._scheduler.shutdown(wait=False)
            self._running = False
            logger.info("Scheduler stopped")

    # === Cron 修改 ===

    def update_cron(self, cron_expr: str) -> bool:
        """动态修改 cron 表达式"""
        self._cron_expr = cron_expr
        if self._scheduler and self._job_id:
            try:
                self._scheduler.reschedule_job(
                    self._job_id,
                    trigger="cron",
                    minute=self._parse_cron_minute(),
                )
                logger.info(f"Cron updated to: {cron_expr}")
                return True
            except Exception as e:
                logger.error(f"Failed to update cron: {e}")
                return False
        return True

    # === 状态 ===

    def get_status(self) -> dict:
        """获取调度器状态"""
        job = None
        if self._scheduler and self._job_id:
            job = self._scheduler.get_job(self._job_id)

        return {
            "running": self._running,
            "cron": self._cron_expr,
            "next_run": str(job.next_run_time) if job and job.next_run_time else None,
        }

    # === 内部 ===

    async def _run_evaluation(self) -> None:
        """执行优先级评估"""
        logger.debug("Scheduled evaluation triggered")
        if self._evaluate_callback:
            try:
                await self._evaluate_callback()
            except Exception as e:
                logger.error(f"Scheduled evaluation failed: {e}")

    def _parse_cron_minute(self) -> str:
        """从 cron 表达式解析分钟字段"""
        parts = self._cron_expr.strip().split()
        if len(parts) >= 1:
            return parts[0]
        return "*/20"
