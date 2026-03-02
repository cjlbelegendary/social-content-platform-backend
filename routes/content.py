from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from models import Content
from routes.user import get_db
from utils.auth import verify_token
from utils.ai_helper import generate_social_content
from utils.auth import get_current_user  # 导入新增的函数

# 初始化路由
router = APIRouter(prefix="/content", tags=["内容接口"])

# 1. 生成并保存内容接口
@router.post("/generate")
def generate_content(
    prompt: str = Body(...),  # 用户创作需求
    platform: str = Body(default="小红书"),  # 目标平台
    title: str = Body(...),  # 内容标题
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)  # 自动获取并验证token
):

    # 调用AI生成内容
    ai_content = generate_social_content(prompt, platform)
    
    # 保存到数据库
    new_content = Content(
        user_id=user_id,
        title=title,
        content=ai_content,
        platform=platform
    )
    db.add(new_content)
    db.commit()
    db.refresh(new_content)
    
    return {
        "code": 200,
        "msg": "生成成功",
        "content": {
            "id": new_content.id,
            "title": new_content.title,
            "content": new_content.content,
            "platform": new_content.platform,
            "create_time": new_content.create_time.strftime("%Y-%m-%d %H:%M:%S")
        }
    }

# 2. 查询用户的所有内容
@router.post("/list")
def get_content_list(
    token: str = Body(...),
    db = Depends(get_db)
):
    # 验证token
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="token无效或过期")
    
    # 查询该用户的所有内容（按时间倒序）
    contents = db.query(Content).filter(Content.user_id == user_id).order_by(Content.create_time.desc()).all()
    
    # 格式化返回
    content_list = []
    for c in contents:
        content_list.append({
            "id": c.id,
            "title": c.title,
            "content": c.content,
            "platform": c.platform,
            "create_time": c.create_time.strftime("%Y-%m-%d %H:%M:%S")
        })
    
    return {"code": 200, "content_list": content_list}

# 3. 删除指定内容
@router.post("/delete")
def delete_content(
    token: str = Body(...),
    content_id: int = Body(...),
    db = Depends(get_db)
):
    # 验证token
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="token无效或过期")
    
    # 查询内容是否存在，且属于该用户
    content = db.query(Content).filter(Content.id == content_id, Content.user_id == user_id).first()
    if not content:
        raise HTTPException(status_code=400, detail="内容不存在或无权限删除")
    
    # 删除
    db.delete(content)
    db.commit()
    
    return {"code": 200, "msg": "删除成功"}