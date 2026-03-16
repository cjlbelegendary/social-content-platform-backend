from fastapi import APIRouter, Depends, HTTPException, Body, Header
from sqlalchemy.orm import Session
from models import User, Content
from routes.user import get_db
from utils.auth import verify_token, get_current_admin

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

# 4. 管理员身份校验接口
@router.get("/validate")
def validate_admin(
    db = Depends(get_db),
    Authorization: str = Header(None),
    raise_error: bool = True
):
    """
    管理员身份校验接口
    使用Authorization请求头进行身份验证
    
    :param raise_error: 是否在验证失败时抛出错误，默认True
    """
    # 验证管理员身份
    admin_id = get_current_admin(Authorization=Authorization, db=db, raise_error=raise_error)
    
    if not admin_id:
        # 验证失败且不抛出错误的情况
        return {
            "code": 403,
            "msg": "无管理员权限",
            "admin_info": None
        }
    
    # 获取管理员信息
    admin = db.query(User).filter(User.id == admin_id).first()
    
    return {
        "code": 200,
        "msg": "管理员身份验证成功",
        "admin_info": {
            "user_id": admin.id,
            "username": admin.username,
            "is_admin": admin.is_admin
        }
    }