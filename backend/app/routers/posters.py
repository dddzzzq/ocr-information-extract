from fastapi import APIRouter, HTTPException, Depends, Body
from sqlalchemy.orm import Session
from typing import List
from app import crud, models
from app.schemas.poster import PosterResponse
from app.database import get_db

router = APIRouter()

@router.get("/posters/", response_model=List[PosterResponse], summary="查询海报列表(历史记录)")
def read_posters(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """
    获取所有海报的列表，按最新排序。
    用于前端的“提取历史”和“审核队列”。
    """
    posters = crud.get_posters(db, skip=skip, limit=limit)
    return posters

@router.put("/posters/{poster_id}", response_model=PosterResponse, summary="确认海报(更新状态)")
def confirm_poster(
    poster_id: int, 
    status_update: dict = Body(..., example={"status": "approved"}), # 接收 { "status": "approved" }
    db: Session = Depends(get_db)
):
    """
    用于前端的“确认”按钮，将海报状态从 'pending' 更新为 'approved'。
    """
    new_status = status_update.get("status")
    if new_status not in ["approved", "pending", "rejected"]: # 简单验证
        raise HTTPException(status_code=400, detail="无效的状态值")
        
    db_poster = crud.update_poster_status(db, poster_id=poster_id, status=new_status)
    if db_poster is None:
        raise HTTPException(status_code=404, detail="海报未找到")
    return db_poster

@router.delete("/posters/{poster_id}", response_model=PosterResponse, summary="删除海报")
def delete_poster(
    poster_id: int, 
    db: Session = Depends(get_db)
):
    """
    用于前端的“删除”按钮。
    """
    db_poster = crud.delete_poster(db, poster_id=poster_id)
    if db_poster is None:
        raise HTTPException(status_code=404, detail="海报未找到")
    return db_poster