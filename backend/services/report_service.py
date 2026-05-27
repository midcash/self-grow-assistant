import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.models import TodoItem, QualityProgress, Quality


def get_summary(db: Session, report_type: str, date: datetime.date) -> dict:
    if report_type == "weekly":
        start_date = date - datetime.timedelta(days=6)
    elif report_type == "monthly":
        start_date = date - datetime.timedelta(days=29)
    else:
        start_date = date - datetime.timedelta(days=6)

    period = f"{start_date} ~ {date}"

    done_todos = db.query(TodoItem).filter(
        TodoItem.date >= start_date,
        TodoItem.date <= date,
        TodoItem.status == "done",
    ).all()

    total_duration = sum(t.actual_duration or t.duration_minutes for t in done_todos)

    total_score = 0
    scores = db.query(func.sum(QualityProgress.score)).join(Quality).filter(
        QualityProgress.date >= start_date,
        QualityProgress.date <= date,
        Quality.is_active == True,
    ).scalar()
    total_score = scores or 0

    # Find top quality
    quality_scores = db.query(
        Quality.name, func.sum(QualityProgress.score).label("total")
    ).join(QualityProgress).filter(
        QualityProgress.date >= start_date,
        QualityProgress.date <= date,
        Quality.is_active == True,
    ).group_by(Quality.id).order_by(func.sum(QualityProgress.score).desc()).first()

    top_quality = {"name": quality_scores[0], "score_gained": quality_scores[1]} if quality_scores else {"name": "无", "score_gained": 0}

    # Streak
    streak_days = 0
    check_date = date
    while True:
        day_todos = db.query(TodoItem).filter(TodoItem.date == check_date).all()
        if day_todos and any(t.status == "done" for t in day_todos):
            streak_days += 1
            check_date -= datetime.timedelta(days=1)
        else:
            break

    # Generate insight
    done_count = len(done_todos)
    unique_days = len(set(str(t.date) for t in done_todos))
    insight = f"本周期内你有 {unique_days} 天完成了计划，共完成 {done_count} 项任务，累计投入 {total_duration} 分钟。"
    if top_quality["name"] != "无":
        insight += f"表现最突出的是「{top_quality['name']}」，获得 {top_quality['score_gained']} 积分。"
    if streak_days >= 7:
        insight += f"你已经连续 {streak_days} 天打卡，继续保持！"

    return {
        "period": period,
        "total_duration": total_duration,
        "total_score": total_score,
        "streak_days": streak_days,
        "top_quality": top_quality,
        "insight": insight,
    }
