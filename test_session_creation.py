from sqlalchemy import create_engine
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

# 创建会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

try:
    # 检查是否有用户
    users = db.query(User).all()
    if not users:
        print("数据库中没有用户，请先创建用户")
    else:
        user = users[0]
        print(f"使用用户：ID={user.id}, 用户名={user.username}")
        
        # 创建测试会话
        test_session = Session(
            user_id=user.id,
            title="测试会话"
        )
        db.add(test_session)
        db.commit()
        db.refresh(test_session)
        print(f"创建会话成功：ID={test_session.id}, 标题={test_session.title}")
        
        # 查询会话
        sessions = db.query(Session).filter(Session.user_id == user.id).all()
        print("\n查询到的会话：")
        for session in sessions:
            print(f"ID: {session.id}, 标题: {session.title}, 用户ID: {session.user_id}")
        
        # 测试会话详情查询
        if sessions:
            test_session_id = sessions[0].id
            print(f"\n测试查询会话ID={test_session_id}的详情：")
            session_detail = db.query(Session).filter(Session.id == test_session_id, Session.user_id == user.id).first()
            if session_detail:
                print(f"会话详情：ID={session_detail.id}, 标题={session_detail.title}")
                # 查询会话下的内容
                contents = db.query(Content).filter(Content.session_id == test_session_id).all()
                print(f"会话下的内容数量：{len(contents)}")
            else:
                print("未找到会话详情")
finally:
    db.close()
