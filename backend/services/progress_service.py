import datetime
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.models import Quality, QualityProgress, QualityLevel, TodoItem


def _todo_to_dict(t: TodoItem) -> dict:
    return {
        "id": t.id,
        "date": str(t.date) if t.date else None,
        "content": t.content,
        "category": t.category,
        "duration_minutes": t.duration_minutes,
        "actual_duration": t.actual_duration,
        "status": t.status,
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def get_dashboard(db: Session, date: datetime.date) -> dict:
    todos = db.query(TodoItem).filter(TodoItem.date == date).order_by(TodoItem.created_at.asc()).all()
    total = len(todos)
    done = sum(1 for t in todos if t.status == "done")
    completion_rate = done / total if total > 0 else 0.0
    total_duration = sum(t.actual_duration or t.duration_minutes for t in todos if t.status == "done")
    total_score_today = 0

    qualities_data = []
    active_qualities = db.query(Quality).filter(Quality.is_active == True).all()

    for q in active_qualities:
        total_score_result = db.query(func.sum(QualityProgress.score)).filter(
            QualityProgress.quality_id == q.id
        ).scalar()
        current_score = total_score_result or 0

        current_level = 1
        current_level_name = "萌芽期"
        next_level_name = "习惯期"
        next_level_score = 100

        levels = sorted(q.levels, key=lambda l: l.level)
        for lv in levels:
            if current_score >= lv.threshold_score:
                current_level = lv.level
                current_level_name = lv.name
            else:
                next_level_name = lv.name
                next_level_score = lv.threshold_score
                break
        else:
            next_level_name = current_level_name
            next_level_score = current_score

        if next_level_score == 0:
            progress_pct = 100.0
        else:
            prev_threshold = 0
            for lv in levels:
                if lv.level == current_level:
                    prev_threshold = lv.threshold_score
            range_size = next_level_score - prev_threshold
            progress_pct = ((current_score - prev_threshold) / range_size * 100) if range_size > 0 else 100.0

        today_progress = db.query(QualityProgress).filter(
            QualityProgress.quality_id == q.id,
            QualityProgress.date == date,
        ).first()
        today_score = today_progress.score if today_progress else 0
        total_score_today += today_score

        qualities_data.append({
            "id": q.id,
            "name": q.name,
            "icon": q.icon,
            "current_score": current_score,
            "current_level": current_level,
            "level_name": current_level_name,
            "next_level_name": next_level_name,
            "next_level_score": next_level_score,
            "progress_pct": round(progress_pct, 1),
        })

    # Calculate streak
    streak_days = 0
    check_date = date
    while True:
        day_todos = db.query(TodoItem).filter(TodoItem.date == check_date).all()
        if day_todos and any(t.status == "done" for t in day_todos):
            streak_days += 1
            check_date -= datetime.timedelta(days=1)
        else:
            break

    return {
        "date": date,
        "completion_rate": round(completion_rate, 2),
        "total_duration": total_duration,
        "total_score_today": total_score_today,
        "streak_days": streak_days,
        "qualities": qualities_data,
        "todos": [_todo_to_dict(t) for t in todos],
    }


def get_quality_history(db: Session, quality_id: int, days: int = 30) -> dict | None:
    quality = db.query(Quality).filter(Quality.id == quality_id).first()
    if not quality:
        return None

    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days - 1)

    records = db.query(QualityProgress).filter(
        QualityProgress.quality_id == quality_id,
        QualityProgress.date >= start_date,
        QualityProgress.date <= end_date,
    ).order_by(QualityProgress.date.asc()).all()

    history = [{"date": str(r.date), "score": r.score, "total_score": r.total_score} for r in records]

    return {
        "quality": {
            "id": quality.id,
            "name": quality.name,
            "description": quality.description,
            "icon": quality.icon,
        },
        "history": history,
    }


def get_heatmap_data(db: Session, start_date: datetime.date, end_date: datetime.date) -> dict:
    CATEGORIES = ["学习", "运动", "工作", "生活", "阅读", "冥想"]

    todos = db.query(TodoItem).filter(
        TodoItem.date >= start_date,
        TodoItem.date <= end_date,
        TodoItem.status == "done",
    ).all()

    grouped = defaultdict(lambda: defaultdict(int))
    for t in todos:
        grouped[str(t.date)][t.category] += (t.actual_duration or t.duration_minutes)

    data = []
    current = start_date
    while current <= end_date:
        row = {"date": str(current)}
        for cat in CATEGORIES:
            row[cat] = grouped[str(current)].get(cat, 0)
        data.append(row)
        current += datetime.timedelta(days=1)

    return {"categories": CATEGORIES, "data": data}


def get_trend_data(db: Session, quality_id: int, days: int = 30) -> dict | None:
    quality = db.query(Quality).filter(Quality.id == quality_id).first()
    if not quality:
        return None

    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days - 1)

    records = db.query(QualityProgress).filter(
        QualityProgress.quality_id == quality_id,
        QualityProgress.date >= start_date,
        QualityProgress.date <= end_date,
    ).order_by(QualityProgress.date.asc()).all()

    points = [{"date": str(r.date), "cumulative_score": r.total_score} for r in records]

    thresholds = [0]
    for lv in sorted(quality.levels, key=lambda l: l.level):
        thresholds.append(lv.threshold_score)

    return {
        "quality_name": quality.name,
        "points": points,
        "level_thresholds": thresholds,
    }
