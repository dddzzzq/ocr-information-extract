from pydantic import BaseModel
from typing import Optional

# 使用 Pydantic 定义 API 的响应数据结构
# 这有助于数据验证、自动生成 API 文档，并提供代码提示
class PosterResponse(BaseModel):
    title: Optional[str] = "未能识别"
    date: Optional[str] = "未能识别"
    time: Optional[str] = "未能识别"
    location: Optional[str] = "未能识别"
    organizer: Optional[str] = "未能识别"
    summary: Optional[str] = "未能识别"
