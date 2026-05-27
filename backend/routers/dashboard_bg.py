import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.schemas import ApiResponse
from backend.utils import get_data_dir

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard-bg"])
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

BG_DIR = get_data_dir() / "images" / "dashboard"


def _get_orientation(filepath) -> str:
    """Returns 'portrait' if height > width, otherwise 'landscape'.
    Respects EXIF orientation tag from phone cameras."""
    try:
        from PIL import Image, ImageOps
        with Image.open(filepath) as img:
            img = ImageOps.exif_transpose(img)
            w, h = img.size
        return "portrait" if h > w else "landscape"
    except Exception:
        return "landscape"


@router.get("/background")
def get_background():
    if not BG_DIR.exists():
        return ApiResponse(data={"image_url": None, "orientation": "landscape"})
    for f in sorted(BG_DIR.iterdir()):
        if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS:
            return ApiResponse(data={
                "image_url": f"/api/v1/static/images/dashboard/{f.name}",
                "orientation": _get_orientation(f),
            })
    return ApiResponse(data={"image_url": None, "orientation": "landscape"})


@router.post("/background")
def upload_background(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or ".jpg")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported image format, only jpg/png/webp/gif allowed")
    os.makedirs(BG_DIR, exist_ok=True)
    # Clean old background files
    for old in BG_DIR.iterdir():
        if old.is_file():
            old.unlink()
    filename = f"background{ext}"
    filepath = BG_DIR / filename
    with open(filepath, "wb") as f:
        f.write(file.file.read())
    image_url = f"/api/v1/static/images/dashboard/{filename}"
    orientation = _get_orientation(filepath)
    return ApiResponse(data={"image_url": image_url, "orientation": orientation})
