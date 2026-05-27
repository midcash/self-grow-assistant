from __future__ import annotations
import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ── Quality ──
class QualityCreate(BaseModel):
    name: str = Field(..., max_length=50)
    description: str = Field(default="", max_length=200)
    icon: str = Field(default="star", max_length=20)
    target_level: int = Field(default=3, ge=1, le=5)


class QualityUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    icon: Optional[str] = Field(None, max_length=20)
    target_level: Optional[int] = Field(None, ge=1, le=5)


class QualityLevelOut(BaseModel):
    level: int
    name: str
    description: str
    threshold_score: int

    model_config = {"from_attributes": True}


class QualityOut(BaseModel):
    id: int
    name: str
    description: str
    icon: str
    target_level: int
    created_at: datetime.datetime
    is_active: bool

    model_config = {"from_attributes": True}


class QualityDetailOut(QualityOut):
    current_level: int = 1
    total_score: int = 0
    levels: list[QualityLevelOut] = []
    progress: list[dict] = []


# ── CategoryMapping ──
class MappingItem(BaseModel):
    category: str
    score_per_duration: float = 0.05
    score_per_completion: int = 5


class MappingUpdateRequest(BaseModel):
    mappings: list[MappingItem]


class MappingOut(BaseModel):
    id: int
    quality_id: int
    category: str
    score_per_duration: float
    score_per_completion: int

    model_config = {"from_attributes": True}


# ── Todo ──
class TodoParseRequest(BaseModel):
    text: str
    date: datetime.date


class TodoParsed(BaseModel):
    content: str
    category: str
    duration_minutes: int


class TodoParseResponse(BaseModel):
    parsed: list[TodoParsed]


class TodoCreate(BaseModel):
    content: str = Field(..., max_length=200)
    category: str = Field(default="其他", max_length=30)
    duration_minutes: int = Field(default=0, ge=0)


class TodoBatchCreate(BaseModel):
    date: datetime.date
    todos: list[TodoCreate]


class TodoUpdate(BaseModel):
    content: Optional[str] = Field(None, max_length=200)
    category: Optional[str] = Field(None, max_length=30)
    duration_minutes: Optional[int] = Field(None, ge=0)


class TodoCheckIn(BaseModel):
    actual_duration: int = Field(default=0, ge=0)


class TodoOut(BaseModel):
    id: int
    date: datetime.date
    content: str
    category: str
    duration_minutes: int
    actual_duration: int
    status: str
    completed_at: Optional[datetime.datetime]
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class TodoCheckInResult(BaseModel):
    todo: TodoOut
    score_earned: int


# ── Progress ──
class DashboardQuality(BaseModel):
    id: int
    name: str
    icon: str
    current_score: int
    current_level: int
    level_name: str
    next_level_name: str
    next_level_score: int
    progress_pct: float


class DashboardOut(BaseModel):
    date: datetime.date
    completion_rate: float
    total_duration: int
    total_score_today: int
    streak_days: int
    qualities: list[DashboardQuality]
    todos: list[TodoOut]


class HeatmapCell(BaseModel):
    date: datetime.date
    categories: dict[str, int]


class HeatmapOut(BaseModel):
    categories: list[str]
    data: list[dict]


class TrendPoint(BaseModel):
    date: datetime.date
    cumulative_score: int


class TrendOut(BaseModel):
    quality_name: str
    points: list[TrendPoint]
    level_thresholds: list[int]


# ── Report ──
class SummaryOut(BaseModel):
    period: str
    total_duration: int
    total_score: int
    streak_days: int
    top_quality: dict
    insight: str


# ── Common ──
class ApiResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[object] = None


# ── RoleModel ──
class SuggestedActivity(BaseModel):
    content: str
    category: str
    duration_minutes: int = 15
    frequency: str = "每日"
    reason: str = ""


class RoleModelQualityOut(BaseModel):
    id: int
    role_model_id: int
    quality_name: str
    description: str
    suggested_activities: list[SuggestedActivity]

    model_config = {"from_attributes": True}


class RoleModelOut(BaseModel):
    id: int
    name: str
    field: str
    avatar: str
    image_url: str = ""
    description: str
    qualities: list[RoleModelQualityOut] = []

    model_config = {"from_attributes": True}


class AdoptResult(BaseModel):
    quality_id: int
    quality_name: str
    role_model_name: str
    message: str


# ── Common ──
class ApiResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[object] = None


class PaginatedData(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
