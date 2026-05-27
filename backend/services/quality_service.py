from sqlalchemy.orm import Session
from backend.models import Quality, QualityLevel, CategoryMapping
from backend.schemas import QualityCreate, QualityUpdate, MappingUpdateRequest

DEFAULT_LEVELS = [
    (1, "萌芽期", "刚刚开始，需要刻意提醒自己", 0),
    (2, "习惯期", "已经形成初步习惯，不再需要强烈意志力", 100),
    (3, "内化期", "行为已融入日常，自然而然地做到", 300),
    (4, "精通期", "不仅自己能做好，还能影响他人", 600),
    (5, "无意识期", "已成为你的身份标签，别人因这点记住你", 1000),
]

DEFAULT_CATEGORIES = ["学习", "运动", "工作", "生活", "阅读", "冥想"]


def create_quality(db: Session, data: QualityCreate) -> Quality:
    quality = Quality(
        name=data.name,
        description=data.description,
        icon=data.icon,
        target_level=data.target_level,
    )
    db.add(quality)
    db.flush()

    for level, name, desc, threshold in DEFAULT_LEVELS:
        db.add(QualityLevel(
            quality_id=quality.id,
            level=level,
            name=name,
            description=desc,
            threshold_score=threshold,
        ))

    for cat in DEFAULT_CATEGORIES:
        db.add(CategoryMapping(
            quality_id=quality.id,
            category=cat,
            score_per_duration=0.05,
            score_per_completion=5,
        ))

    db.commit()
    db.refresh(quality)
    return quality


def list_qualities(db: Session, is_active: bool = True) -> list[Quality]:
    q = db.query(Quality)
    if is_active:
        q = q.filter(Quality.is_active == True)
    return q.order_by(Quality.created_at.desc()).all()


def get_quality(db: Session, quality_id: int) -> Quality | None:
    return db.query(Quality).filter(Quality.id == quality_id).first()


def update_quality(db: Session, quality_id: int, data: QualityUpdate) -> Quality | None:
    quality = get_quality(db, quality_id)
    if not quality:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(quality, key, value)
    db.commit()
    db.refresh(quality)
    return quality


def delete_quality(db: Session, quality_id: int) -> bool:
    quality = get_quality(db, quality_id)
    if not quality:
        return False
    quality.is_active = False
    db.commit()
    return True


def get_quality_detail(db: Session, quality_id: int) -> dict | None:
    quality = get_quality(db, quality_id)
    if not quality:
        return None

    from backend.models import QualityProgress
    from sqlalchemy import func

    total_result = db.query(func.sum(QualityProgress.score)).filter(
        QualityProgress.quality_id == quality_id
    ).scalar()
    total_score = total_result or 0

    current_level = 1
    for level in sorted(quality.levels, key=lambda l: l.level):
        if total_score >= level.threshold_score:
            current_level = level.level

    progress = db.query(QualityProgress).filter(
        QualityProgress.quality_id == quality_id
    ).order_by(QualityProgress.date.desc()).limit(30).all()

    return {
        "id": quality.id,
        "name": quality.name,
        "description": quality.description,
        "icon": quality.icon,
        "target_level": quality.target_level,
        "created_at": quality.created_at,
        "is_active": quality.is_active,
        "current_level": current_level,
        "total_score": total_score,
        "levels": [{"level": l.level, "name": l.name, "description": l.description, "threshold_score": l.threshold_score} for l in sorted(quality.levels, key=lambda x: x.level)],
        "progress": [{"date": str(p.date), "score": p.score, "total_score": p.total_score} for p in progress],
    }


def update_mappings(db: Session, quality_id: int, data: MappingUpdateRequest) -> list[CategoryMapping] | None:
    quality = get_quality(db, quality_id)
    if not quality:
        return None

    db.query(CategoryMapping).filter(CategoryMapping.quality_id == quality_id).delete()
    for item in data.mappings:
        db.add(CategoryMapping(
            quality_id=quality_id,
            category=item.category,
            score_per_duration=item.score_per_duration,
            score_per_completion=item.score_per_completion,
        ))
    db.commit()
    return db.query(CategoryMapping).filter(CategoryMapping.quality_id == quality_id).all()
