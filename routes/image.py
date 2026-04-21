from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from models import Image, Session as SessionModel
from routes.user import get_db
from utils.auth import get_current_user
from utils.ai_helper import generate_image, generate_image_from_content
import logging
import datetime
import uuid

# 初始化路由
router = APIRouter(prefix="/image", tags=["图片接口"])

# 1. 图片生成接口
@router.post("/generate")
async def generate_image_api(
    prompt: str = Body(...),
    style: str = Body(default=None),
    size: str = Body(default="1:1"),
    platform: str = Body(default=None),
    session_id: int = Body(default=None),
    title: str = Body(default=None),
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """生成图片"""
    try:
        result = generate_image(prompt, style, size)
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "图片生成失败"))
        
        image_id = f"img_{uuid.uuid4().hex[:16]}"
        
        if session_id:
            session = db.query(SessionModel).filter(
                SessionModel.id == session_id,
                SessionModel.user_id == user_id
            ).first()
            if not session:
                raise HTTPException(status_code=400, detail="会话不存在或无权限访问")
        else:
            session = SessionModel(
                user_id=user_id,
                title=title or prompt[:30]
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            session_id = session.id
        
        new_image = Image(
            user_id=user_id,
            session_id=session_id,
            image_id=image_id,
            url=result["url"],
            width=result["width"],
            height=result["height"],
            prompt=prompt,
            style=style,
            size=size,
            platform=platform,
            create_time=datetime.datetime.now()
        )
        db.add(new_image)
        db.commit()
        db.refresh(new_image)
        
        logging.info(f"图片生成成功：{image_id}")
        
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "id": new_image.id,
                "image_id": image_id,
                "url": result["url"],
                "width": result["width"],
                "height": result["height"],
                "prompt": prompt,
                "style": style,
                "size": size,
                "session_id": session_id
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"图片生成异常：{str(e)}")
        raise HTTPException(status_code=500, detail="图片生成失败，请稍后重试")

# 2. 图片重新生成接口
@router.post("/regenerate")
async def regenerate_image_api(
    image_id: str = Body(default=None),
    prompt: str = Body(...),
    style: str = Body(default=None),
    size: str = Body(default="1:1"),
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """重新生成图片"""
    try:
        # 调用图片生成函数
        result = generate_image(prompt, style, size)
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "图片生成失败"))
        
        # 生成新的图片ID
        new_image_id = f"img_{uuid.uuid4().hex[:16]}"
        
        # 保存到数据库
        new_image = Image(
            user_id=user_id,
            session_id=None,
            image_id=new_image_id,
            url=result["url"],
            width=result["width"],
            height=result["height"],
            prompt=prompt,
            style=style,
            size=size,
            platform=None,
            create_time=datetime.datetime.now()
        )
        db.add(new_image)
        db.commit()
        db.refresh(new_image)
        
        logging.info(f"图片重新生成成功：{new_image_id}")
        
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "id": new_image.id,
                "image_id": new_image_id,
                "url": result["url"],
                "width": result["width"],
                "height": result["height"],
                "prompt": prompt,
                "style": style,
                "size": size
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"图片重新生成异常：{str(e)}")
        raise HTTPException(status_code=500, detail="图片重新生成失败，请稍后重试")

# 3. 文案生成配图接口
@router.post("/generate-from-content")
async def generate_image_from_content_api(
    content: str = Body(...),
    platform: str = Body(default=None),
    style: str = Body(default=None),
    size: str = Body(default="3:4"),
    session_id: int = Body(default=None),
    title: str = Body(default=None),
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """从文案生成配图"""
    try:
        result = generate_image_from_content(content, style, size)
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "图片生成失败"))
        
        image_id = f"img_{uuid.uuid4().hex[:16]}"
        
        if session_id:
            session = db.query(SessionModel).filter(
                SessionModel.id == session_id,
                SessionModel.user_id == user_id
            ).first()
            if not session:
                raise HTTPException(status_code=400, detail="会话不存在或无权限访问")
        else:
            session = SessionModel(
                user_id=user_id,
                title=title or content[:30]
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            session_id = session.id
        
        new_image = Image(
            user_id=user_id,
            session_id=session_id,
            image_id=image_id,
            url=result["url"],
            width=result["width"],
            height=result["height"],
            prompt=content[:100],
            style=style,
            size=size,
            platform=platform,
            create_time=datetime.datetime.now()
        )
        db.add(new_image)
        db.commit()
        db.refresh(new_image)
        
        logging.info(f"文案配图生成成功：{image_id}")
        
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "id": new_image.id,
                "image_id": image_id,
                "url": result["url"],
                "width": result["width"],
                "height": result["height"],
                "prompt": content[:100],
                "style": style,
                "size": size,
                "session_id": session_id
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"文案配图生成异常：{str(e)}")
        raise HTTPException(status_code=500, detail="文案配图生成失败，请稍后重试")

# 4. 图片历史记录接口
@router.get("/history")
async def get_image_history(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    session_id: int = Query(default=None),
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """获取图片历史记录"""
    try:
        # 构建查询
        query = db.query(Image).filter(Image.user_id == user_id)
        
        # 如果指定了session_id，筛选特定会话的图片
        if session_id:
            query = query.filter(Image.session_id == session_id)
        
        # 按创建时间倒序排序
        query = query.order_by(Image.create_time.desc())
        
        # 计算总数
        total = query.count()
        
        # 分页
        offset = (page - 1) * size
        images = query.offset(offset).limit(size).all()
        
        # 构建返回列表
        image_list = []
        for img in images:
            image_list.append({
                "image_id": img.image_id,
                "url": img.url,
                "prompt": img.prompt,
                "style": img.style,
                "size": img.size,
                "create_time": img.create_time.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return {
            "code": 200,
            "data": {
                "total": total,
                "list": image_list
            }
        }
    
    except Exception as e:
        logging.error(f"获取图片历史记录异常：{str(e)}")
        raise HTTPException(status_code=500, detail="获取图片历史记录失败，请稍后重试")
