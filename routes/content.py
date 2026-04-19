from fastapi import APIRouter, Depends, HTTPException, Body, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from models import Content, Session as SessionModel, Image, ContentPackage, PackageItem
from routes.user import get_db
from utils.auth import get_current_user
from utils.ai_helper import generate_social_content_stream
import logging
from typing import List
import datetime

# 初始化路由
router = APIRouter(prefix="/content", tags=["内容接口"])

# 2. 查询用户的所有会话（只返回会话基本信息）
@router.get("/list")
async def get_content_list(  # 加async（可选，不影响功能）
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    try:
        # 查询用户的所有会话
        sessions = db.query(SessionModel).filter(SessionModel.user_id == user_id).order_by(SessionModel.update_time.desc()).all()
        
        session_list = []
        for session in sessions:
            # 只返回会话基本信息
            session_list.append({
                "session_id": session.id,
                "session_title": session.title,
                "create_time": session.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                "update_time": session.update_time.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return {"code": 200, "session_list": session_list}
    except Exception as e:
        logging.error(f"获取会话列表异常：{str(e)}")
        return {
            "code": 500,
            "msg": "获取会话列表失败，请稍后重试",
            "session_list": []
        }

# 3. 查询指定会话的详细信息（包含会话下的所有内容）
@router.get("/session/{session_id}")
async def get_session_detail(
    session_id: int,
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    try:
        # 验证会话是否存在且属于当前用户
        session = db.query(SessionModel).filter(SessionModel.id == session_id, SessionModel.user_id == user_id).first()
        if not session:
            raise HTTPException(status_code=400, detail="会话不存在或无权限访问")
        
        # 查询会话下的所有文案内容
        contents = db.query(Content).filter(Content.session_id == session_id).all()
        
        # 查询会话下的所有图片
        images = db.query(Image).filter(Image.session_id == session_id).all()
        
        # 合并文案和图片，并按时间排序
        all_items = []
        
        # 添加文案
        for c in contents:
            all_items.append({
                "type": "content",
                "id": c.id,
                "title": c.title,
                "content": c.content,
                "platform": c.platform,
                "create_time": c.create_time,
                "create_time_str": c.create_time.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        # 添加图片
        for img in images:
            all_items.append({
                "type": "image",
                "id": img.id,
                "image_id": img.image_id,
                "url": img.url,
                "width": img.width,
                "height": img.height,
                "prompt": img.prompt,
                "style": img.style,
                "size": img.size,
                "platform": img.platform,
                "create_time": img.create_time,
                "create_time_str": img.create_time.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        # 按创建时间排序（升序，最早的在前）
        all_items.sort(key=lambda x: x["create_time"])
        
        # 移除create_time字段（只保留字符串格式）
        for item in all_items:
            del item["create_time"]
        
        return {
            "code": 200,
            "session": {
                "session_id": session.id,
                "session_title": session.title,
                "create_time": session.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                "update_time": session.update_time.strftime("%Y-%m-%d %H:%M:%S"),
                "contents": all_items
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"获取会话详情异常：{str(e)}")
        return {
            "code": 500,
            "msg": "获取会话详情失败，请稍后重试",
            "session": None
        }

# 4. 删除指定内容
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

# 6. 获取所有生成内容（支持筛选和分页）
@router.get("/contents")
async def get_all_contents(
    type: str = Query(default="all"),
    platform: List[str] = Query(None),
    start_time: str = None,
    end_time: str = None,
    keyword: str = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """获取所有内容（文案+图片）"""
    try:
        all_items = []
        
        # 查询文案
        if type in ["all", "content"]:
            content_query = db.query(Content).filter(Content.user_id == user_id)
            
            if platform:
                content_query = content_query.filter(Content.platform.in_(platform))
            
            if start_time:
                start_date = datetime.datetime.strptime(start_time, "%Y-%m-%d")
                content_query = content_query.filter(Content.create_time >= start_date)
            
            if end_time:
                end_date = datetime.datetime.strptime(end_time, "%Y-%m-%d")
                end_date = end_date + datetime.timedelta(days=1)
                content_query = content_query.filter(Content.create_time < end_date)
            
            if keyword:
                content_query = content_query.filter(
                    (Content.title.contains(keyword)) | (Content.content.contains(keyword))
                )
            
            contents = content_query.all()
            
            for content in contents:
                package_items = db.query(PackageItem).filter(
                    PackageItem.item_type == "content",
                    PackageItem.item_id == content.id
                ).all()
                
                package_ids = [item.package_id for item in package_items]
                
                session_info = None
                if content.session_id:
                    session = db.query(SessionModel).filter(SessionModel.id == content.session_id).first()
                    if session:
                        session_info = {
                            "session_id": session.id,
                            "session_title": session.title
                        }
                
                all_items.append({
                    "type": "content",
                    "id": content.id,
                    "title": content.title,
                    "content": content.content,
                    "platform": content.platform,
                    "create_time": content.create_time,
                    "create_time_str": content.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "is_in_package": len(package_ids) > 0,
                    "package_ids": package_ids,
                    "session": session_info
                })
        
        # 查询图片
        if type in ["all", "image"]:
            image_query = db.query(Image).filter(Image.user_id == user_id)
            
            if platform:
                image_query = image_query.filter(Image.platform.in_(platform))
            
            if start_time:
                start_date = datetime.datetime.strptime(start_time, "%Y-%m-%d")
                image_query = image_query.filter(Image.create_time >= start_date)
            
            if end_time:
                end_date = datetime.datetime.strptime(end_time, "%Y-%m-%d")
                end_date = end_date + datetime.timedelta(days=1)
                image_query = image_query.filter(Image.create_time < end_date)
            
            if keyword:
                image_query = image_query.filter(Image.prompt.contains(keyword))
            
            images = image_query.all()
            
            for image in images:
                package_items = db.query(PackageItem).filter(
                    PackageItem.item_type == "image",
                    PackageItem.item_id == image.id
                ).all()
                
                package_ids = [item.package_id for item in package_items]
                
                session_info = None
                if image.session_id:
                    session = db.query(SessionModel).filter(SessionModel.id == image.session_id).first()
                    if session:
                        session_info = {
                            "session_id": session.id,
                            "session_title": session.title
                        }
                
                all_items.append({
                    "type": "image",
                    "id": image.id,
                    "url": image.url,
                    "width": image.width,
                    "height": image.height,
                    "prompt": image.prompt,
                    "style": image.style,
                    "platform": image.platform,
                    "create_time": image.create_time,
                    "create_time_str": image.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "is_in_package": len(package_ids) > 0,
                    "package_ids": package_ids,
                    "session": session_info
                })
        
        # 按创建时间倒序排序
        all_items.sort(key=lambda x: x["create_time"], reverse=True)
        
        # 计算总数
        total = len(all_items)
        
        # 分页
        offset = (page - 1) * page_size
        paginated_items = all_items[offset:offset + page_size]
        
        # 移除create_time字段
        for item in paginated_items:
            del item["create_time"]
        
        return {
            "code": 200,
            "data": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "list": paginated_items
            }
        }
    except Exception as e:
        logging.error(f"获取内容列表异常：{str(e)}")
        raise HTTPException(status_code=500, detail="获取内容列表失败，请稍后重试")

# 9. 流式生成内容接口
@router.post("/generate/stream")
async def generate_content_stream(
    prompt: str = Body(...),
    platform: str = Body(default="小红书"),
    title: str = Body(...),
    session_id: int = Body(None, description="会话ID，不提供则创建新会话"),
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """流式生成社交内容"""
    print("====================================")
    print(f"流式接口被调用：prompt={prompt}, platform={platform}, user_id={user_id}")
    print("====================================")
    try:
        # 处理会话
        if session_id:
            # 验证会话是否存在且属于当前用户
            session = db.query(SessionModel).filter(SessionModel.id == session_id, SessionModel.user_id == user_id).first()
            if not session:
                raise HTTPException(status_code=400, detail="会话不存在或无权限访问")
        else:
            # 创建新会话
            session = SessionModel(
                user_id=user_id,
                title=title
            )
            db.add(session)
            db.commit()
            db.refresh(session)
        
        # 获取会话历史
        session_history = []
        if session_id:
            # 查询会话下的所有内容，按创建时间排序
            contents = db.query(Content).filter(Content.session_id == session_id).order_by(Content.create_time.desc()).limit(5).all()
            # 反转顺序，使最早的消息在前
            contents.reverse()
            for content in contents:
                # 每个内容作为一条助手消息
                session_history.append({
                    "role": "assistant",
                    "content": content.content
                })
        
        # 用于收集完整的生成内容
        full_content = []
        
        # 定义流式响应生成器
        def content_generator():
            nonlocal full_content
            print("开始生成内容...")
            # 调用流式生成函数
            print("调用generate_social_content_stream函数...")
            for chunk in generate_social_content_stream(prompt, platform, session_history=session_history, db=db, user_id=user_id):
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
                    session_id=session.id,
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
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"流式生成内容异常：{str(e)}")
        # 出错时返回错误信息
        def error_generator():
            yield f"data: 生成失败，请稍后重试\n\n"
        return StreamingResponse(
            error_generator(),
            media_type="text/event-stream"
        )