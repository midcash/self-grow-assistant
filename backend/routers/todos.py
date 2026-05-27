from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import (
    TodoParseRequest, TodoParseResponse, TodoBatchCreate,
    TodoOut, TodoUpdate, TodoCheckIn, TodoCheckInResult, ApiResponse,
)
from backend.services import todo_service

router = APIRouter(prefix="/api/v1/todos", tags=["todos"])


@router.post("/parse")
def parse_todos(data: TodoParseRequest):
    parsed = todo_service.parse_todo_text(data.text)
    return ApiResponse(data={"parsed": parsed})


@router.post("/batch")
def batch_create(data: TodoBatchCreate, db: Session = Depends(get_db)):
    items = todo_service.batch_create_todos(db, data)
    return ApiResponse(data={"items": [TodoOut.model_validate(i) for i in items]})


@router.get("")
def get_by_date(date: str, db: Session = Depends(get_db)):
    from datetime import date as date_type
    try:
        d = date_type.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为 YYYY-MM-DD")
    items = todo_service.get_todos_by_date(db, d)
    return ApiResponse(data={"items": [TodoOut.model_validate(i) for i in items]})


@router.put("/{todo_id}")
def update(todo_id: int, data: TodoUpdate, db: Session = Depends(get_db)):
    todo = todo_service.update_todo(db, todo_id, data)
    if not todo:
        raise HTTPException(status_code=404, detail="TODO 不存在")
    return ApiResponse(data=TodoOut.model_validate(todo))


@router.delete("/{todo_id}")
def delete(todo_id: int, db: Session = Depends(get_db)):
    ok = todo_service.delete_todo(db, todo_id)
    if not ok:
        raise HTTPException(status_code=404, detail="TODO 不存在")
    return ApiResponse(message="已删除")


@router.patch("/{todo_id}/checkin")
def checkin(todo_id: int, data: TodoCheckIn, db: Session = Depends(get_db)):
    result = todo_service.checkin_todo(db, todo_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="TODO 不存在")
    return ApiResponse(data={
        "todo": TodoOut.model_validate(result["todo"]),
        "score_earned": result["score_earned"],
    })


@router.patch("/{todo_id}/skip")
def skip(todo_id: int, db: Session = Depends(get_db)):
    todo = todo_service.skip_todo(db, todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail="TODO 不存在")
    return ApiResponse(data=TodoOut.model_validate(todo))
