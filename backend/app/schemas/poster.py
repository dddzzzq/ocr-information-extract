from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

# 这个 Pydantic 模型用于定义 LLM 返回的数据结构
class PosterBase(BaseModel):
    title: Optional[str] = "未能识别"
    date: Optional[str] = "未能识别"
    time: Optional[str] = "未能识别"
    location: Optional[str] = "未能识别"
    organizer: Optional[str] = "未能识别"
    summary: Optional[str] = "未能识别"
    
    # (新增) 扩展字段
    speaker: Optional[str] = "未能识别"
    event_type: Optional[str] = "未能识别"
    target_audience: Optional[str] = "未能识别"
    contact_info: Optional[str] = "未能识别"
    registration_info: Optional[str] = "未能识别"

# 这个模型用于创建新海报时，额外包含原始 OCR 文本
class PosterCreate(PosterBase):
    raw_ocr_text: Optional[str] = None
    image_url: Optional[str] = None

# 这个模型用于从数据库读取数据时（包含 id, status 等）
class PosterResponse(PosterBase):
    id: int
    raw_ocr_text: Optional[str] = None
    image_url: Optional[str] = None 
    status: str
    created_at: datetime

    # (修改) Pydantic v2 的正确配置
    model_config = ConfigDict(from_attributes=True)