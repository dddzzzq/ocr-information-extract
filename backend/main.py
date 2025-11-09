import uvicorn
# 导入在 app/main.py 中创建的 FastAPI 实例
from app.main import app

# 项目的入口点，用于启动 uvicorn 服务
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)