from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import extraction

# 创建 FastAPI 应用实例
app = FastAPI(
    title="校园海报信息提取系统 API",
    description="一个使用 OCR 和 LLM 技术从图片中提取信息的 API (重构版)",
    version="1.0.0"
)

# 配置 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含（注册）来自 routers 目录的路由
# 所有 extraction.py 中的路由都会被加上 /api/v1 的前缀
app.include_router(extraction.router, prefix="/api/v1", tags=["Extraction"])

@app.get("/", summary="API 健康检查", tags=["Root"])
def read_root():
    """
    根路径，用于简单的健康检查。
    """
    return {"status": "ok", "message": "欢迎使用校园海报信息提取系统 API"}
