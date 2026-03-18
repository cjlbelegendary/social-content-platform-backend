from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, Session, Content, Schedule
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取数据库连接字符串
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# 创建数据库引擎
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# 创建所有表
Base.metadata.create_all(bind=engine)

print("数据库表创建完成！")
print("创建的表：")
print("- users (用户表)")
print("- sessions (会话表)")
print("- contents (内容表)")
print("- schedules (排期表)")
