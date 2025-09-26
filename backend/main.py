import uvicorn
# 导入在 app/main.py 中创建的 FastAPI 实例
from app.main import app

# 这个文件是项目的入口点，用于启动 uvicorn 服务
# 这样可以保持项目根目录的整洁
if __name__ == "__main__":
    # uvicorn.run() 的第一个参数是一个字符串 "module_name:app_instance_name"
    # 在这里，它指向 app/main.py 文件中的 app 对象
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)