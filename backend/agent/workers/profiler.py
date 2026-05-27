"""Profiler Agent — 个人画像 Worker

能力: 用户偏好分析、历史数据查询、习惯推断
工具: SQLite 查询 (todo_items, quality_progress, agent_memory_digests)
"""

import logging
from datetime import date, timedelta

from backend.agent.workers.base import WorkerBase, WorkerResult, TaskBrief

logger = logging.getLogger(__name__)


class ProfilerWorker(WorkerBase):
    """个人画像 Agent

    分析用户的偏好、习惯、能力和约束:
    - 任务完成模式 (哪些类别完成率高、什么时间段效率高)
    - 品质成长数据 (在哪些品质上花了最多时间)
    - 历史偏好 (从对话摘要中提取)
    - 当前状态 (连续天数、积分、等级)
    """

    @property
    def role(self) -> str:
        return "profiler"

    @property
    def system_prompt(self) -> str:
        return """你是个人画像分析专家。你的工作是分析用户的行为数据、偏好和习惯。

你的工作方式:
1. 查询用户的历史数据
2. 分析模式、偏好和趋势
3. 以结构化的方式呈现用户画像
4. 识别用户的约束和限制

输出要求:
- 包含用户偏好总结
- 包含行为模式分析
- 包含当前状态
- 如果数据不足，说明需要更多数据"""

    def capabilities(self) -> list[str]:
        return ["profile", "analyze", "preference", "habit", "user_info"]

    async def execute(self, brief: TaskBrief) -> WorkerResult:
        """分析用户画像"""
        try:
            profile_data = {}

            # 1. 分析任务完成模式
            completion = self._analyze_completion_patterns()
            profile_data["completion"] = completion

            # 2. 分析品质成长
            qualities = self._analyze_qualities()
            profile_data["qualities"] = qualities

            # 3. 分析类别偏好
            categories = self._analyze_categories()
            profile_data["categories"] = categories

            # 4. 提取历史偏好
            recent = self._get_recent_context()
            profile_data["recent"] = recent

            # 4b. 目标进度差距分析
            gaps = self._analyze_goal_gaps()
            profile_data["goal_gaps"] = gaps

            # 5. 格式化输出
            content = self._format_profile(brief.objective, profile_data)

            return WorkerResult(
                task_id=brief.task_id,
                success=True,
                content=content,
                data=profile_data,
                sources=["本地数据库"],
                confidence=0.85,
            )
        except Exception as e:
            logger.error(f"Profiler failed: {e}")
            return WorkerResult(
                task_id=brief.task_id,
                success=False,
                content=f"画像分析失败: {e}",
                confidence=0.0,
            )

    def _analyze_completion_patterns(self) -> dict:
        """分析任务完成模式"""
        try:
            from backend.database import SessionLocal
            from backend.models import TodoItem

            db = SessionLocal()
            try:
                today = date.today()
                week_ago = today - timedelta(days=7)

                todos = db.query(TodoItem).filter(
                    TodoItem.date >= week_ago,
                    TodoItem.date <= today,
                ).all()

                total = len(todos)
                done = sum(1 for t in todos if t.status == "done")
                skipped = sum(1 for t in todos if t.status == "skipped")

                # 按时段分析
                by_category = {}
                for t in todos:
                    cat = t.category
                    if cat not in by_category:
                        by_category[cat] = {"total": 0, "done": 0}
                    by_category[cat]["total"] += 1
                    if t.status == "done":
                        by_category[cat]["done"] += 1

                return {
                    "total_tasks_7d": total,
                    "completed_7d": done,
                    "skipped_7d": skipped,
                    "completion_rate": round(done / total * 100, 1) if total else 0,
                    "by_category": by_category,
                }
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Completion analysis failed: {e}")
            return {}

    def _analyze_qualities(self) -> dict:
        """分析品质成长数据"""
        try:
            from backend.database import SessionLocal
            from backend.models import Quality, QualityProgress

            db = SessionLocal()
            try:
                qualities = db.query(Quality).filter(Quality.is_active == True).all()
                result = {}
                for q in qualities:
                    progress = db.query(QualityProgress).filter(
                        QualityProgress.quality_id == q.id
                    ).order_by(QualityProgress.date.desc()).limit(1).first()
                    result[q.name] = {
                        "total_score": progress.total_score if progress else 0,
                        "target_level": q.target_level,
                    }
                return result
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Quality analysis failed: {e}")
            return {}

    def _analyze_categories(self) -> dict:
        """分析类别偏好（最近30天）"""
        try:
            from backend.database import SessionLocal
            from backend.models import TodoItem

            db = SessionLocal()
            try:
                today = date.today()
                month_ago = today - timedelta(days=30)
                todos = db.query(TodoItem).filter(
                    TodoItem.date >= month_ago
                ).all()

                cat_duration = {}
                for t in todos:
                    if t.category not in cat_duration:
                        cat_duration[t.category] = 0
                    cat_duration[t.category] += t.actual_duration or t.duration_minutes

                # 排序取 top 3
                sorted_cats = sorted(cat_duration.items(), key=lambda x: x[1], reverse=True)
                return {
                    "top_categories": [{"name": c, "minutes": m} for c, m in sorted_cats[:3]],
                    "total_categories": len(cat_duration),
                }
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Category analysis failed: {e}")
            return {}

    def _get_recent_context(self) -> dict:
        """获取最近的用户上下文"""
        try:
            from backend.database import SessionLocal
            from backend.models import AgentMemoryDigest

            db = SessionLocal()
            try:
                today = date.today()
                digests = db.query(AgentMemoryDigest).filter(
                    AgentMemoryDigest.date <= today
                ).order_by(AgentMemoryDigest.date.desc()).limit(3).all()

                return {
                    "recent_summaries": [
                        {"date": str(d.date), "summary": d.summary[:100]}
                        for d in digests
                    ],
                }
            finally:
                db.close()
        except Exception as e:
            logger.debug(f"Recent context failed: {e}")
            return {}

    def _analyze_goal_gaps(self) -> list[dict]:
        """分析目标进度差距"""
        try:
            from backend.database import SessionLocal
            from backend.models import Goal
            from datetime import date as date_type
            import re

            db = SessionLocal()
            try:
                today = date_type.today()
                goals = db.query(Goal).filter(Goal.status == "active").all()
                gaps = []
                for g in goals:
                    target_str = str(g.target_metric or "1")
                    nums = re.findall(r'\d+', target_str)
                    target = max(float(nums[0]) if nums else 1.0, 1.0)
                    progress = g.current_progress
                    days_left = (g.deadline - today).days if g.deadline else 30
                    days_left = max(days_left, 1)

                    required_daily = max((target - progress) / days_left, 0)
                    actual_daily = progress / max((30 - days_left), 1) if days_left < 30 else 0
                    gap_ratio = max(required_daily - actual_daily, 0) / max(required_daily, 0.01)

                    gaps.append({
                        "goal_id": g.id,
                        "title": g.title,
                        "target": int(target),
                        "progress": progress,
                        "progress_pct": round(progress / max(target, 0.01) * 100),
                        "days_left": days_left,
                        "required_daily": round(required_daily, 1),
                        "gap_ratio": round(gap_ratio, 2),
                        "status": "on_track" if gap_ratio < 0.5 else "at_risk" if gap_ratio < 1.0 else "off_track",
                    })
                return sorted(gaps, key=lambda x: x["gap_ratio"], reverse=True)
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Goal gap analysis failed: {e}")
            return []

    def _format_profile(self, objective: str, data: dict) -> str:
        parts = [f"## 用户画像\n"]
        parts.append(f"分析目标: {objective}\n")

        comp = data.get("completion", {})
        if comp:
            parts.append(f"### 任务完成 (7天)")
            parts.append(f"- 完成率: {comp.get('completion_rate', 'N/A')}%")
            parts.append(f"- 完成: {comp.get('completed_7d', 0)} / 跳过: {comp.get('skipped_7d', 0)}")
            by_cat = comp.get("by_category", {})
            if by_cat:
                cat_summary = ", ".join(
                    f"{c}({d['done']}/{d['total']})"
                    for c, d in sorted(by_cat.items(), key=lambda x: x[1].get('done', 0), reverse=True)[:3]
                )
                parts.append(f"- 擅长领域: {cat_summary}")

        cats = data.get("categories", {})
        if cats:
            top = cats.get("top_categories", [])
            if top:
                parts.append(f"\n### 偏好类别")
                for item in top:
                    parts.append(f"- {item['name']}: {item['minutes']}分钟/30天")

        gaps = data.get("goal_gaps", [])
        if gaps:
            parts.append(f"\n### 目标进度差距")
            for g in gaps[:5]:
                tag = {"on_track": "正常", "at_risk": "⚠需关注", "off_track": "🔴严重滞后"}
                parts.append(
                    f"- [{tag.get(g['status'], '?')}] {g['title']}: "
                    f"进度{g['progress_pct']}%, 剩余{g['days_left']}天, "
                    f"每日需推进{g['required_daily']}"
                )

        qual = data.get("qualities", {})
        if qual:
            parts.append(f"\n### 品质成长")
            for name, info in list(qual.items())[:5]:
                parts.append(f"- {name}: {info['total_score']}分 (目标Lv{info['target_level']})")

        return "\n".join(parts)
