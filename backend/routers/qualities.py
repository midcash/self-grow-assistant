from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import (
    QualityCreate, QualityUpdate, QualityOut, QualityDetailOut,
    MappingUpdateRequest, MappingOut, ApiResponse,
)
from backend.services import quality_service

router = APIRouter(prefix="/api/v1/qualities", tags=["qualities"])


@router.post("")
def create(data: QualityCreate, db: Session = Depends(get_db)):
    quality = quality_service.create_quality(db, data)
    return ApiResponse(data=QualityOut.model_validate(quality))


@router.get("")
def list_qualities(is_active: bool = True, db: Session = Depends(get_db)):
    qualities = quality_service.list_qualities(db, is_active)
    return ApiResponse(data=[QualityOut.model_validate(q) for q in qualities])


@router.get("/{quality_id}")
def get_detail(quality_id: int, db: Session = Depends(get_db)):
    detail = quality_service.get_quality_detail(db, quality_id)
    if not detail:
        raise HTTPException(status_code=404, detail="品质目标不存在")
    return ApiResponse(data=detail)


@router.put("/{quality_id}")
def update(quality_id: int, data: QualityUpdate, db: Session = Depends(get_db)):
    quality = quality_service.update_quality(db, quality_id, data)
    if not quality:
        raise HTTPException(status_code=404, detail="品质目标不存在")
    return ApiResponse(data=QualityOut.model_validate(quality))


@router.delete("/{quality_id}")
def delete(quality_id: int, db: Session = Depends(get_db)):
    ok = quality_service.delete_quality(db, quality_id)
    if not ok:
        raise HTTPException(status_code=404, detail="品质目标不存在")
    return ApiResponse(message="已停用")


@router.put("/{quality_id}/mappings")
def update_mappings(quality_id: int, data: MappingUpdateRequest, db: Session = Depends(get_db)):
    mappings = quality_service.update_mappings(db, quality_id, data)
    if mappings is None:
        raise HTTPException(status_code=404, detail="品质目标不存在")
    return ApiResponse(data=[MappingOut.model_validate(m) for m in mappings])
