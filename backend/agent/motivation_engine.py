"""MotivationEngine — 自主动机引擎

参考 NeoPsyke 的 Id-Ego-Superego 模型，简化为适合个人助手的压力驱动系统:
- 每个活跃 Goal 有 "pressure" 值
- pressure = 进度差距 × 时间紧迫度
- 压力超阈值 → 自主提醒 + 自动提权
- 提醒 3 次未处理 → 升级为紧急
"""

import logging
from datetime import date, datetime

logger = logging.getLogger(__name__)


class MotivationEngine:
    """自主动机引擎

    每次调度器触发时运行，扫描所有活跃目标:
    1. 计算压力值
    2. 压力 > 0.5 → 生成提醒
    3. 压力 > 0.8 → 紧急提醒
    4. 提醒 3 次 → 升级 + 自动提权子任务
    """

    def __init__(self):
        try:
            from backend.agent.config import ConfigLoader
            config = ConfigLoader.get_default_config()
            cfg = config.get("plugins", {}).get("motivation", {})
            self.alert_threshold = cfg.get("alert_threshold", 0.4)
            self.urgent_threshold = cfg.get("urgent_threshold", 0.7)
            self.max_reminders = cfg.get("max_reminders", 3)
        except Exception:
            self.alert_threshold = 0.4
            self.urgent_threshold = 0.7
            self.max_reminders = 3

    async def tick(self, notify_plugin, tts_plugin) -> list[dict]:
        """执行一次动机检查，返回需要提醒的目标列表"""
        try:
            from backend.database import SessionLocal
            from backend.models import Goal, GoalTask

            db = SessionLocal()
            try:
                today = date.today()
                active_goals = db.query(Goal).filter(
                    Goal.status == "active"
                ).all()

                alerts = []
                for goal in active_goals:
                    # 计算压力
                    pressure = self._calc_pressure(goal, today)
                    goal.pressure = pressure

                    if pressure < self.alert_threshold:
                        continue

                    # 更新提醒计数
                    goal.reminder_count += 1
                    goal.last_reminded_at = datetime.utcnow()

                    # 生成提醒
                    level = "urgent" if pressure >= self.urgent_threshold else "normal"
                    days_left = (goal.deadline - today).days if goal.deadline else "?"
                    # Compute progress pct
                    import re as _re
                    _t_str = str(goal.target_metric or "1")
                    _t_nums = _re.findall(r'\d+', _t_str)
                    _target = max(float(_t_nums[0]) if _t_nums else 1.0, 1.0)
                    pct = round(goal.current_progress / max(_target, 0.01) * 100)

                    alert = {
                        "goal_id": goal.id,
                        "title": goal.title,
                        "pressure": round(pressure, 2),
                        "days_left": days_left,
                        "progress_pct": pct,
                        "reminder_count": goal.reminder_count,
                        "level": level,
                    }

                    # 超过最大提醒次数 → 升级
                    if goal.reminder_count >= self.max_reminders:
                        alert["escalated"] = True
                        self._escalate_goal_tasks(goal, db)

                    alerts.append(alert)

                    # 生成语音提醒
                    msg = self._build_alert_message(goal, pressure)
                    if notify_plugin and tts_plugin:
                        try:
                            from backend.agent.plugins.notifier.base import Alert
                            await notify_plugin.notify(Alert(
                                title=f"目标提醒: {goal.title[:20]}",
                                message=msg,
                                level=level,
                                task_id=goal.id,
                            ))
                        except Exception as e:
                            logger.warning(f"Notify failed: {e}")

                db.commit()
                if alerts:
                    logger.info(f"MotivationEngine: {len(alerts)} alerts generated")
                return alerts

            finally:
                db.close()
        except Exception as e:
            logger.error(f"MotivationEngine tick failed: {e}")
            return []

    def _calc_pressure(self, goal, today: date) -> float:
        """计算目标压力值

        pressure = gap × urgency
          gap = (target - progress) / max(target, 1)  # 0~1
          urgency = 1.0 / max(days_left, 1)           # 越近越高
        """
        # Parse target_metric: may be numeric ("10") or string ("投10份简历")
        target_str = str(goal.target_metric or "1")
        import re
        nums = re.findall(r'\d+', target_str)
        target = max(float(nums[0]) if nums else 1.0, 1.0)
        progress = goal.current_progress

        if goal.deadline:
            days_left = max((goal.deadline - today).days, 1)
        else:
            days_left = 30  # 无 ddl，默认 30 天

        gap = max((target - progress) / target, 0)
        urgency = 1.0 / days_left

        # 重要性加权
        importance_weight = goal.importance / 10.0
        return gap * urgency * importance_weight * 10  # 归一化到 0~1

    def _build_alert_message(self, goal, pressure: float) -> str:
        days_left = (goal.deadline - date.today()).days if goal.deadline else "?"
        import re
        target_str = str(goal.target_metric or "1")
        nums = re.findall(r'\d+', target_str)
        target = max(float(nums[0]) if nums else 1.0, 1.0)
        pct = round(goal.current_progress / max(target, 0.01) * 100)

        if pressure >= self.urgent_threshold:
            return (
                f"紧急！{goal.title}还剩{days_left}天，"
                f"当前进度{pct}%，已提醒{goal.reminder_count}次，"
                f"请立即处理"
            )
        else:
            return (
                f"{goal.title}还剩{days_left}天，"
                f"进度{pct}%，建议加快进度"
            )

    def _escalate_goal_tasks(self, goal, db) -> None:
        """升级: 自动将目标子任务优先级拉满"""
        try:
            from backend.models import GoalTask
            tasks = db.query(GoalTask).filter(
                GoalTask.goal_id == goal.id,
                GoalTask.status == "pending",
            ).all()
            for t in tasks:
                t.today_progress = 0  # 重置今日进度，重新触发提醒
        except Exception as e:
            logger.warning(f"Escalate failed: {e}")
