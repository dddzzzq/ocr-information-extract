from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from .database import Base

class Poster(Base):
    """
    定义 Poster 数据模型 (即数据库中的 'posters' 表)
    """
    __tablename__ = "posters"

    id = Column(Integer, primary_key=True, index=True)
    
    # 结构化信息
    title = Column(String(255), default="未能识别")
    date = Column(String(100), default="未能识别")
    time = Column(String(100), default="未能识别")
    location = Column(String(255), default="未能识别")
    organizer = Column(String(255), default="未能识别")
    summary = Column(Text, default="未能识别")
    speaker = Column(String(255), default="未能识别")
    event_type = Column(String(100), default="未能识别")
    target_audience = Column(String(255), default="未能识别")
    contact_info = Column(String(255), default="未能识别")
    registration_info = Column(String(255), default="未能识别")
    image_url = Column(String(500), nullable=True)
    raw_ocr_text = Column(Text, nullable=True)
    status = Column(String(50), default="pending", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())