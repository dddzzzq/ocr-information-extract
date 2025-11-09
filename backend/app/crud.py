from sqlalchemy.orm import Session
from . import models
from .schemas.poster import PosterBase
import os

def get_poster(db: Session, poster_id: int):
    """根据ID获取单个海报"""
    return db.query(models.Poster).filter(models.Poster.id == poster_id).first()

def get_posters(db: Session, skip: int = 0, limit: int = 100, search: str = None):
    """
    (更新) 获取海报列表，支持搜索
    按创建时间倒序排列，最新的在最前面
    """
    query = db.query(models.Poster)
    
    # (新增) 如果提供了搜索词，则在 'title' 字段中进行模糊匹配
    if search:
        query = query.filter(models.Poster.title.ilike(f"%{search}%"))
        
    return query.order_by(models.Poster.id.desc()).offset(skip).limit(limit).all()

def create_poster(db: Session, poster_data: PosterBase, raw_text: str, image_url: str):
    """
    创建新的海报记录
    poster_data 是 LLM 返回的 Pydantic 对象
    raw_text 是 OCR 识别的原始文本
    image_url 是保存的图片路径
    """
    # **poster_data.dict() 将 Pydantic 模型解包为字典
    db_poster = models.Poster(
        **poster_data.model_dump(), 
        raw_ocr_text=raw_text,
        image_url=image_url, 
        status="pending"  
    )
    db.add(db_poster)
    db.commit()
    db.refresh(db_poster)
    return db_poster

def update_poster_status(db: Session, poster_id: int, status: str):
    """更新海报状态（例如：从 'pending' 到 'approved'）"""
    db_poster = get_poster(db, poster_id)
    if db_poster:
        db_poster.status = status
        db.commit()
        db.refresh(db_poster)
    return db_poster

def delete_poster(db: Session, poster_id: int):
    """删除海报"""
    db_poster = get_poster(db, poster_id)
    if db_poster:
        # 在删除数据库记录前，先删除关联的图片文件
        if db_poster.image_url:
            file_path = db_poster.image_url.lstrip('/') # 移除开头的 '/'
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"已删除关联图片: {file_path}")
                except Exception as e:
                    print(f"删除图片 {file_path} 时出错: {e}")
            else:
                print(f"警告: 未找到要删除的图片文件 {file_path}")
        
        db.delete(db_poster)
        db.commit()
    return db_poster

