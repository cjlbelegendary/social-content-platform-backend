from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from models import User, Content
from routes.user import get_db
from utils.auth import verify_token

# 初始化路由
router = APIRouter(prefix="/admin", tags=["管理员接口"])

# 1. 验证是否是管理员
def is_admin(token: str, db: Session):
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="token无效或过期")
    # 查询用户是否是管理员
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="无管理员权限")
    return user_id

# 2. 查看所有用户
@router.post("/user_list")
def get_all_users(
    token: str = Body(...),
    db = Depends(get_db)
):
    # 验证管理员权限
    is_admin(token, db)
    
    # 查询所有用户
    users = db.query(User).all()
    user_list = []
    for u in users:
        user_list.append({
            "id": u.id,
            "username": u.username,
            "is_admin": u.is_admin,
            "create_time": u.create_time.strftime("%Y-%m-%d %H:%M:%S")
        })
    
    return {"code": 200, "user_list": user_list}

# 3. 查看所有内容（审核用）
@router.post("/content_list")
def get_all_contents(
    token: str = Body(...),
    db = Depends(get_db)
):
    # 验证管理员权限
    is_admin(token, db)
    
    # 查询所有内容
    contents = db.query(Content).join(User, Content.user_id == User.id).all()
    content_list = []
    for c in contents:
        content_list.append({
            "id": c.id,
            "username": db.query(User).filter(User.id == c.user_id).first().username,
            "title": c.title,
            "platform": c.platform,
            "create_time": c.create_time.strftime("%Y-%m-%d %H:%M:%S")
        })
    
    return {"code": 200, "content_list": content_list}