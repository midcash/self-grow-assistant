import os
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.services import role_model_service
from backend.schemas import ApiResponse
from backend.utils import get_data_dir

router = APIRouter(prefix="/api/v1/role-models", tags=["role-models"])
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _save_upload(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename or ".jpg")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="不支持的图片格式，仅支持 jpg/png/webp/gif")
    images_dir = get_data_dir() / "images" / "role_models"
    os.makedirs(images_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = images_dir / filename
    with open(filepath, "wb") as f:
        f.write(file.file.read())
    return f"/api/v1/static/images/role_models/{filename}"


@router.get("")
def list_role_models(db: Session = Depends(get_db)):
    data = role_model_service.list_role_models(db)
    return ApiResponse(data=data)


@router.get("/{role_model_id}")
def get_role_model(role_model_id: int, db: Session = Depends(get_db)):
    data = role_model_service.get_role_model_detail(db, role_model_id)
    if not data:
        return ApiResponse(code=40001, message="明星不存在", data=None)
    return ApiResponse(data=data)


@router.post("/{role_model_id}/adopt/{quality_id}")
def adopt_quality(role_model_id: int, quality_id: int, db: Session = Depends(get_db)):
    result = role_model_service.adopt_quality(db, role_model_id, quality_id)
    if not result:
        return ApiResponse(code=40001, message="品质不存在", data=None)
    return ApiResponse(data=result)


@router.post("/{role_model_id}/upload-image")
def upload_role_model_image(role_model_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    image_url = _save_upload(file)
    updated = role_model_service.update_image_url(db, role_model_id, image_url)
    if not updated:
        return ApiResponse(code=40001, message="明星不存在", data=None)
    return ApiResponse(data={"image_url": image_url})
