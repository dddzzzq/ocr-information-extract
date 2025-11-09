from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import extraction, posters
from app import models
from app.database import engine
from fastapi.staticfiles import StaticFiles # 导入静态文件
import os 

# 为上传的图片创建存储目录
UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="校园海报信息提取系统 API",
    description="V3.1 - 支持图片存储",
    version="3.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载(Mount)静态文件目录
# 这使得 /static/uploads/filename.jpg 可以通过 http://.../static/uploads/filename.jpg 访问
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(extraction.router, prefix="/api/v1", tags=["1. Extraction (提取)"])
app.include_router(posters.router, prefix="/api/v1", tags=["2. Posters CRUD (管理)"])

@app.get("/", summary="API 健康检查", tags=["Root"])
def read_root():
    return {"status": "ok", "message": "欢迎使用校园海报信息提取系统 API v3.1"}