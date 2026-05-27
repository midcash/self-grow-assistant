import re
import datetime
from sqlalchemy.orm import Session
from backend.models import TodoItem, QualityProgress, CategoryMapping, Quality
from backend.schemas import TodoCreate, TodoBatchCreate, TodoUpdate, TodoCheckIn

CATEGORY_KEYWORDS = {
    "学习": ["读", "学", "看", "书", "课程", "复习", "练习", "研究", "写", "编程", "代码", "Python", "算法"],
    "运动": ["跑", "步", "健身", "瑜伽", "游泳", "跳", "绳", "球", "运动", "撸铁", "有氧", "HIIT", "骑"],
    "阅读": ["阅读", "读书", "看书", "页", "章", "节", "Kindle", "小说", "文学"],
    "工作": ["会议", "项目", "报告", "方案", "PPT", "文档", "邮件", "需求", "排期", "对接"],
    "生活": ["做饭", "打扫", "整理", "买菜", "洗", "家务", "购物", "收拾"],
    "冥想": ["冥想", "冥想", "静坐", "深呼吸", "正念", "禅", "打坐"],
}

# Matches time ranges: 7:00-8:30, 7：00~8：30, 14:00 - 15:30
TIME_RANGE_RE = re.compile(
    r"(\d{1,2})\s*[:：]\s*(\d{2})\s*[-~～—]\s*(\d{1,2})\s*[:：]\s*(\d{2})"
)

DURATION_PATTERNS = [
    (re.compile(r"(\d+)\s*小时"), 60),
    (re.compile(r"(\d+)\s*[hH]"), 60),
    (re.compile(r"(\d+)\s*分钟"), 1),
    (re.compile(r"(\d+)\s*[mM](?!\w)"), 1),
    (re.compile(r"(\d+\.?\d*)\s*小时"), 60),
    (re.compile(r"(\d+)\s*个?钟"), 60),
]


def _parse_time_range(text: str) -> int:
    """Extract duration in minutes from a time range like '7:00-8:30'."""
    m = TIME_RANGE_RE.search(text)
    if not m:
        return 0
    h1, m1, h2, m2 = int(m[1]), int(m[2]), int(m[3]), int(m[4])
    start = h1 * 60 + m1
    end = h2 * 60 + m2
    if end <= start:
        end += 24 * 60  # cross midnight
    return end - start


def parse_todo_text(text: str) -> list[dict]:
    """
    Parse natural language todo text into structured items.
    Uses regex + keyword matching (v1 local).
    """
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    # Also split by common Chinese separators
    items_text = []
    for line in lines:
        parts = re.split(r"[，。,\.;；、\s]{2,}", line)
        items_text.extend([p.strip() for p in parts if p.strip() and len(p.strip()) > 2])

    if not items_text:
        items_text = lines

    result = []
    for item_text in items_text:
        # 1. Try time range (7:00-8:30 → 90min)
        duration = _parse_time_range(item_text)

        # 2. Fallback to keyword-based duration
        if duration == 0:
            for pattern, multiplier in DURATION_PATTERNS:
                m = pattern.search(item_text)
                if m:
                    duration = int(float(m.group(1)) * multiplier)
                    break

        category = "其他"
        for cat, keywords in CATEGORY_KEYWORDS.items():
            if any(kw in item_text for kw in keywords):
                category = cat
                break

        content = re.sub(r"\s+", " ", item_text).strip()
        result.append({
            "content": content,
            "category": category,
            "duration_minutes": duration,
        })

    return result


def batch_create_todos(db: Session, data: TodoBatchCreate) -> list[TodoItem]:
    items = []
    for td in data.todos:
        todo = TodoItem(
            date=data.date,
            content=td.content,
            category=td.category,
            duration_minutes=td.duration_minutes,
        )
        db.add(todo)
        items.append(todo)
    db.commit()
    for item in items:
        db.refresh(item)
    return items


def get_todos_by_date(db: Session, date: datetime.date) -> list[TodoItem]:
    return db.query(TodoItem).filter(TodoItem.date == date).order_by(TodoItem.created_at.asc()).all()


def get_todo(db: Session, todo_id: int) -> TodoItem | None:
    return db.query(TodoItem).filter(TodoItem.id == todo_id).first()


def update_todo(db: Session, todo_id: int, data: TodoUpdate) -> TodoItem | None:
    todo = get_todo(db, todo_id)
    if not todo:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(todo, key, value)
    db.commit()
    db.refresh(todo)
    return todo


def delete_todo(db: Session, todo_id: int) -> bool:
    todo = get_todo(db, todo_id)
    if not todo:
        return False
    db.delete(todo)
    db.commit()
    return True


def checkin_todo(db: Session, todo_id: int, data: TodoCheckIn) -> dict | None:
    todo = get_todo(db, todo_id)
    if not todo:
        return None

    todo.status = "done"
    todo.actual_duration = data.actual_duration or todo.duration_minutes
    todo.completed_at = datetime.datetime.utcnow()

    # Calculate score earned
    minutes = todo.actual_duration or todo.duration_minutes
    score_earned = 0

    mappings = db.query(CategoryMapping).join(Quality).filter(
        CategoryMapping.category == todo.category,
        Quality.is_active == True,
    ).all()

    for mapping in mappings:
        earned = int(minutes * mapping.score_per_duration) + mapping.score_per_completion
        score_earned += earned

        # Update quality progress
        today = todo.date
        progress = db.query(QualityProgress).filter(
            QualityProgress.quality_id == mapping.quality_id,
            QualityProgress.date == today,
        ).first()

        if progress:
            progress.score += earned
        else:
            progress = QualityProgress(
                quality_id=mapping.quality_id,
                date=today,
                score=earned,
                total_score=0,
            )
            db.add(progress)
            db.flush()

        # Update total_score
        from sqlalchemy import func
        total = db.query(func.sum(QualityProgress.score)).filter(
            QualityProgress.quality_id == mapping.quality_id
        ).scalar() or 0
        progress.total_score = total

    db.commit()
    db.refresh(todo)
    return {"todo": todo, "score_earned": score_earned}


def skip_todo(db: Session, todo_id: int) -> TodoItem | None:
    todo = get_todo(db, todo_id)
    if not todo:
        return None
    todo.status = "skipped"
    db.commit()
    db.refresh(todo)
    return todo
