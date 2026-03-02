from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from models import Content
from routes.user import get_db
from utils.auth import get_current_user
from utils.ai_helper import generate_social_content  # 导入异步函数
import logging
import datetime

# 初始化路由
router = APIRouter(prefix="/content", tags=["内容接口"])

# 1. 生成并保存内容接口（改为异步，最小改动）
@router.post("/generate")
async def generate_content(  # 仅加async关键字
    prompt: str = Body(...),
    platform: str = Body(default="小红书"),
    title: str = Body(...),
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """生成社交内容（异步版，解决超时）"""
    try:
        # 1. 调用异步AI生成函数（60秒超时）
        ai_content = await generate_social_content(prompt, platform, timeout=60)
        
        # 2. 保存到数据库
        new_content = Content(
            user_id=user_id,
            title=title,
            content=ai_content,
            platform=platform,
            create_time=datetime.datetime.now()
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
    except Exception as e:
        logging.error(f"生成内容异常：{str(e)}")
        return {
            "code": 500,
            "msg": "生成失败，请稍后重试",
            "content": None
        }

# 2. 查询用户的所有内容
@router.get("/list")
async def get_content_list(  # 加async（可选，不影响功能）
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    contents = db.query(Content).filter(Content.user_id == user_id).order_by(Content.create_time.desc()).all()
    
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
async def delete_content(  # 加async（可选）
    content_id: int = Body(...),
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    content = db.query(Content).filter(Content.id == content_id, Content.user_id == user_id).first()
    if not content:
        raise HTTPException(status_code=400, detail="内容不存在或无权限删除")
    
    db.delete(content)
    db.commit()
    
    return {"code": 200, "msg": "删除成功"}