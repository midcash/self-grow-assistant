from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import ApiResponse
from backend.services import report_service

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/summary")
def summary(type: str = "weekly", date: str = None, db: Session = Depends(get_db)):
    from datetime import date as date_type
    if date:
        try:
            d = date_type.fromisoformat(date)
        except ValueError:
            raise HTTPException(status_code=400, detail="日期格式错误")
    else:
        d = date_type.today()

    if type not in ("weekly", "monthly"):
        raise HTTPException(status_code=400, detail="type 仅支持 weekly 或 monthly")

    data = report_service.get_summary(db, type, d)
    return ApiResponse(data=data)
