from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
from app.services import extraction_service
from app.schemas.poster import PosterResponse, PosterBase
from app import crud
from app.database import get_db

import aiofiles 
import os
import uuid 

router = APIRouter()
UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/extract", response_model=PosterResponse, summary="从图片中提取海报信息并保存")
async def extract_information(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    """
    (更新)
    1. 接收图片
    2. 保存图片
    3. 调用 OCR
    4. (新) 调用多模态 LLM (传入 OCR文本 + 图片字节)
    5. 存入数据库
    """
    
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="上传的文件不是有效的图片格式。")

    try:
        # (修改) 保持文件名不变，因为前端已转为 .jpg
        unique_filename = f"{uuid.uuid4()}.jpg"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # 异步读取文件内容
        image_bytes = await file.read() # (重要) image_bytes 在这里被读取
        
        # 异步写入磁盘
        async with aiofiles.open(file_path, 'wb') as out_file:
            await out_file.write(image_bytes)
            
        image_url = f"/static/uploads/{unique_filename}"
        print(f"图片已保存到: {file_path}")

    except Exception as e:
        print(f"保存图片时发生错误: {e}")
        raise HTTPException(status_code=500, detail=f"保存上传文件失败: {e}")

    try:
        # 步骤 1: 调用 OCR 服务
        recognized_text = extraction_service.ocr_processing(image_bytes)
        
        # 步骤 2: (重大更新) 调用多模态 LLM 服务
        # (新增) 将 image_bytes 传递给 LLM
        structured_info_dict: dict = extraction_service.llm_summarization(
            text=recognized_text, 
            image_bytes=image_bytes
        )
        
        # 步骤 3: 转换为 Pydantic 模型
        try:
            poster_data_obj = PosterBase(**structured_info_dict)
        except Exception as e:
            print(f"LLM 返回的字典无法匹配 Pydantic 模型: {e}")
            raise HTTPException(status_code=500, detail=f"LLM数据结构验证失败: {e}")

        # 步骤 4: 保存到数据库
        db_poster = crud.create_poster(
            db=db, 
            poster_data=poster_data_obj, 
            raw_text=recognized_text,
            image_url=image_url 
        )
        
        return db_poster

    except Exception as e:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
            print(f"因处理失败，已删除图片: {file_path}")
            
        print(f"处理图片时发生错误: {e}")
        # (修改) 将原始错误 e 传递给 HTTPException，以便在日志中看到更详细的信息
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")