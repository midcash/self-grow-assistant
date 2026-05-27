from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import ApiResponse
from backend.services import progress_service

router = APIRouter(prefix="/api/v1/progress", tags=["progress"])


@router.get("/dashboard")
def dashboard(date: str, db: Session = Depends(get_db)):
    from datetime import date as date_type
    try:
        d = date_type.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误")
    data = progress_service.get_dashboard(db, d)
    return ApiResponse(data=data)


@router.get("/qualities/{quality_id}/history")
def quality_history(quality_id: int, days: int = Query(default=30, ge=1, le=365), db: Session = Depends(get_db)):
    data = progress_service.get_quality_history(db, quality_id, days)
    if not data:
        raise HTTPException(status_code=404, detail="品质目标不存在")
    return ApiResponse(data=data)


@router.get("/heatmap")
def heatmap(start_date: str, end_date: str, db: Session = Depends(get_db)):
    from datetime import date as date_type
    try:
        start = date_type.fromisoformat(start_date)
        end = date_type.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误")
    data = progress_service.get_heatmap_data(db, start, end)
    return ApiResponse(data=data)


@router.get("/trend")
def trend(quality_id: int, days: int = Query(default=30, ge=1, le=365), db: Session = Depends(get_db)):
    data = progress_service.get_trend_data(db, quality_id, days)
    if not data:
        raise HTTPException(status_code=404, detail="品质目标不存在")
    return ApiResponse(data=data)
