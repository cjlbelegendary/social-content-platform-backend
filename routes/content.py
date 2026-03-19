from fastapi import APIRouter, Depends, HTTPException, Body, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from models import Content, Session as SessionModel
from routes.user import get_db
from utils.auth import get_current_user
from utils.ai_helper import generate_social_content, generate_social_content_stream  # 导入异步函数和流式函数
import logging
from typing import List
import datetime

# 初始化路由
router = APIRouter(prefix="/content", tags=["内容接口"])

# 1. 生成并保存内容接口（改为异步，最小改动）
@router.post("/generate")
async def generate_content(  # 仅加async关键字
    prompt: str = Body(...),
    platform: str = Body(default="小红书"),
    title: str = Body(...),
    session_id: int = Body(None, description="会话ID，不提供则创建新会话"),
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """生成社交内容（异步版，解决超时）"""
    try:
        # 1. 处理会话
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
        
        # 2. 获取会话历史
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
        
        # 3. 调用异步AI生成函数（60秒超时）
        ai_content = await generate_social_content(prompt, platform, timeout=60, session_history=session_history)
        
        # 3. 保存到数据库
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
        
        return {
            "code": 200,
            "msg": "生成成功",
            "content": {
                "id": new_content.id,
                "session_id": session.id,
                "title": new_content.title,
                "content": new_content.content,
                "platform": new_content.platform,
                "create_time": new_content.create_time.strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"生成内容异常：{str(e)}")
        return {
            "code": 500,
            "msg": "生成失败，请稍后重试",
            "content": None
        }

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
        
        # 查询会话下的所有内容
        contents = db.query(Content).filter(Content.session_id == session_id).order_by(Content.create_time.desc()).all()
        
        content_list = []
        for c in contents:
            content_list.append({
                "id": c.id,
                "title": c.title,
                "content": c.content,
                "platform": c.platform,
                "create_time": c.create_time.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return {
            "code": 200,
            "session": {
                "session_id": session.id,
                "session_title": session.title,
                "create_time": session.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                "update_time": session.update_time.strftime("%Y-%m-%d %H:%M:%S"),
                "contents": content_list
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
    platform: List[str] = Query(None),  # 平台筛选（支持多选）
    session_id: List[int] = Query(None),  # 会话ID筛选（支持多选）
    start_time: str = None,  # 开始时间（格式：2024-01-01）
    end_time: str = None,  # 结束时间（格式：2024-01-31）
    title: str = None,  # 标题关键词筛选
    content: str = None,  # 内容关键词筛选
    page: int = 1,  # 页码，默认1
    page_size: int = 10,  # 每页数量，默认10
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """
    获取所有生成内容（支持筛选和分页）
    用于内容管理页面
    """
    try:
        # 构建查询
        query = db.query(Content).filter(Content.user_id == user_id)
        
        # 应用筛选条件
        if platform:
            query = query.filter(Content.platform.in_(platform))
        
        if session_id:
            query = query.filter(Content.session_id.in_(session_id))
        
        if start_time:
            # 筛选开始时间之后的内容
            start_date = datetime.datetime.strptime(start_time, "%Y-%m-%d")
            query = query.filter(Content.create_time >= start_date)
        
        if end_time:
            # 筛选结束时间之前的内容
            end_date = datetime.datetime.strptime(end_time, "%Y-%m-%d")
            # 加上一天，使其包含结束日期的所有时间
            end_date = end_date + datetime.timedelta(days=1)
            query = query.filter(Content.create_time < end_date)
        
        if title:
            # 筛选标题包含关键词的内容
            query = query.filter(Content.title.contains(title))
        
        if content:
            # 筛选内容包含关键词的内容
            query = query.filter(Content.content.contains(content))
        
        # 计算总数
        total = query.count()
        
        # 计算分页
        offset = (page - 1) * page_size
        contents = query.order_by(Content.create_time.desc()).offset(offset).limit(page_size).all()
        
        # 构建响应数据
        content_list = []
        for content in contents:
            # 获取会话信息
            session = db.query(SessionModel).filter(SessionModel.id == content.session_id).first()
            session_title = session.title if session else ""
            
            content_list.append({
                "id": content.id,
                "session_id": content.session_id,
                "session_title": session_title,
                "title": content.title,
                "content": content.content,
                "platform": content.platform,
                "create_time": content.create_time.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return {
            "code": 200,
            "total": total,
            "page": page,
            "page_size": page_size,
            "content_list": content_list
        }
    except Exception as e:
        logging.error(f"获取内容列表异常：{str(e)}")
        return {
            "code": 500,
            "msg": "获取内容列表失败，请稍后重试",
            "total": 0,
            "page": 1,
            "page_size": 10,
            "content_list": []
        }

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
            for chunk in generate_social_content_stream(prompt, platform, session_history=session_history):
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