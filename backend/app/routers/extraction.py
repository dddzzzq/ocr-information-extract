from fastapi import APIRouter, File, UploadFile, HTTPException
from app.services import extraction_service
from app.schemas.poster import PosterResponse

# 创建一个 API 路由实例
router = APIRouter()

# 定义端点
# 这个端点的完整路径将是 /api/v1/extract (前缀在 app/main.py 中定义)
@router.post("/extract", response_model=PosterResponse, summary="从图片中提取海报信息")
async def extract_information(file: UploadFile = File(...)):
    """
    接收上传的图片文件，处理并返回结构化的信息。
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="上传的文件不是有效的图片格式。")

    try:
        # 读取文件内容
        image_bytes = await file.read()
        
        # 步骤 1: 调用 OCR 服务
        recognized_text = extraction_service.ocr_processing(image_bytes)
        
        # 步骤 2: 调用 LLM 服务进行信息提取
        structured_info = extraction_service.llm_summarization(recognized_text)
        
        return structured_info

    except Exception as e:
        print(f"处理图片时发生错误: {e}")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {e}")
