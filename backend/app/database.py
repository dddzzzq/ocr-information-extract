from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. 为简单起见，我们使用 SQLite 数据库。
SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"
# 修改为PostgreSQL:
# SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost/dbname"

# 2. 创建 SQLAlchemy 引擎
# check_same_thread=False 仅在 SQLite 时需要。
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 3. 创建数据库会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. 创建一个 Base 类，我们的 ORM 模型将继承这个类
Base = declarative_base()

# 5. 依赖项：为每个请求提供一个数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()