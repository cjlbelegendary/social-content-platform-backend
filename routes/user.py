from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os
from models import User, Base
from utils.auth import hash_password, verify_password, create_access_token

# 加载.env
load_dotenv()

# 初始化路由
router = APIRouter(prefix="/user", tags=["用户接口"])

# 数据库连接（从.env读取）
DB_URL = f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_engine(DB_URL)
# 创建数据库会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建所有表（首次运行时执行）
Base.metadata.create_all(bind=engine)

# 获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. 用户注册接口
@router.post("/register")
def user_register(
    username: str = Body(...),
    password: str = Body(...),
    db = Depends(get_db)
):
    # 检查用户名是否已存在
    db_user = db.query(User).filter(User.username == username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # 密码加密
    hashed_pwd = hash_password(password)
    
    # 创建新用户
    new_user = User(
        username=username,
        password=hashed_pwd,
        is_admin=False  # 默认普通用户
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"code": 200, "msg": "注册成功", "user_id": new_user.id}

# 2. 用户登录接口
@router.post("/login")
def user_login(
    username: str = Body(...),
    password: str = Body(...),
    db = Depends(get_db)
):
    # 检查用户是否存在
    db_user = db.query(User).filter(User.username == username).first()
    if not db_user:
        # 改：不抛HTTPException，返回统一JSON格式（code≠200）
        return {
            "code": 400,
            "msg": "用户名或密码错误",
            "access_token": "",
            "token_type": "",
            "user_info": {}
        }
    
    # 验证密码
    if not verify_password(password, db_user.password):
        # 改：不抛HTTPException，返回统一JSON格式
        return {
            "code": 400,
            "msg": "用户名或密码错误",
            "access_token": "",
            "token_type": "",
            "user_info": {}
        }
    
    # 生成token
    access_token = create_access_token(user_id=db_user.id)
    
    # 原返回格式不变（前端已适配根层级的access_token）
    return {
        "code": 200,
        "msg": "登录成功",
        "access_token": access_token,
        "token_type": "bearer",
        "user_info": {
            "user_id": db_user.id,
            "username": db_user.username,
            "is_admin": db_user.is_admin
        }
    }