from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from models import Base, User, Session, Content
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取数据库连接字符串
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# 创建数据库引擎
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# 检查数据库表结构
inspector = inspect(engine)
tables = inspector.get_table_names()
print("数据库中的表：")
for table in tables:
    print(f"- {table}")
    # 查看表结构
    columns = inspector.get_columns(table)
    print("  字段：")
    for column in columns:
        print(f"    {column['name']}: {column['type']}")

# 创建会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

try:
    # 查询所有会话
    sessions = db.query(Session).all()
    print("\n数据库中的会话：")
    if sessions:
        for session in sessions:
            print(f"ID: {session.id}, 标题: {session.title}, 用户ID: {session.user_id}")
    else:
        print("  无会话记录")
    
    # 查询所有内容
    contents = db.query(Content).all()
    print("\n数据库中的内容：")
    if contents:
        for content in contents:
            print(f"ID: {content.id}, 标题: {content.title}, 会话ID: {content.session_id}, 用户ID: {content.user_id}")
    else:
        print("  无内容记录")
finally:
    db.close()
