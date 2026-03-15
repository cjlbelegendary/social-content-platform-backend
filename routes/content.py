from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from models import Content
from routes.user import get_db
from utils.auth import get_current_user
from utils.ai_helper import generate_social_content, generate_social_content_stream  # 导入异步函数和流式函数
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

# 4. 流式生成内容接口
@router.post("/generate/stream")
async def generate_content_stream(
    prompt: str = Body(...),
    platform: str = Body(default="小红书"),
    title: str = Body(...),
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """流式生成社交内容"""
    print("====================================")
    print(f"流式接口被调用：prompt={prompt}, platform={platform}, user_id={user_id}")
    print("====================================")
    try:
        # 用于收集完整的生成内容
        full_content = []
        
        # 定义流式响应生成器
        def content_generator():
            nonlocal full_content
            print("开始生成内容...")
            # 调用流式生成函数
            print("调用generate_social_content_stream函数...")
            for chunk in generate_social_content_stream(prompt, platform):
                print(f"生成内容块：{chunk}")
                # 收集内容块
                full_content.append(chunk)
                # 以SSE格式返回数据，确保每个块都以data:前缀开头
                yield f"data: {chunk}\n\n"
            print("生成完成")
            
            # 生成完成后，保存到数据库
            try:
                # 拼接完整内容
                ai_content = ''.join(full_content)
                print(f"完整内容：{ai_content}")
                
                # 保存到数据库
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
                print(f"内容已保存到数据库，ID：{new_content.id}")
            except Exception as db_error:
                logging.error(f"保存内容到数据库异常：{str(db_error)}")
        
        # 返回StreamingResponse
        print("返回StreamingResponse")
        response = StreamingResponse(
            content_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
        )
        print(f"StreamingResponse创建成功：{response}")
        return response
    except Exception as e:
        logging.error(f"流式生成内容异常：{str(e)}")
        # 出错时返回错误信息
        def error_generator():
            yield f"data: 生成失败，请稍后重试\n\n"
        return StreamingResponse(
            error_generator(),
            media_type="text/event-stream"
        )