from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from models import Schedule, Content
from routes.user import get_db
from utils.auth import get_current_user
import logging
import datetime

# 初始化路由
router = APIRouter(prefix="/schedule", tags=["排期接口"])

# 1. 创建排期接口
@router.post("/create")
async def create_schedule(
    content_id: int = Body(...),  # 内容ID
    platform: str = Body(...),  # 平台
    publish_time: str = Body(...),  # 发布时间（格式：2024-03-19 12:00:00）
    schedule_note: str = Body(None),  # 排期备注
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """
    创建排期
    用于排期管理模块
    """
    try:
        # 验证内容是否存在且属于当前用户
        content = db.query(Content).filter(Content.id == content_id, Content.user_id == user_id).first()
        if not content:
            raise HTTPException(status_code=400, detail="内容不存在或无权限操作")
        
        # 解析发布时间
        try:
            publish_datetime = datetime.datetime.strptime(publish_time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise HTTPException(status_code=400, detail="发布时间格式错误，正确格式：2024-03-19 12:00:00")
        
        # 创建排期记录
        new_schedule = Schedule(
            user_id=user_id,
            content_id=content_id,
            platform=platform,
            publish_time=publish_datetime,
            status="pending",  # 初始状态为待发布
            schedule_note=schedule_note
        )
        
        db.add(new_schedule)
        db.commit()
        db.refresh(new_schedule)
        
        return {
            "code": 200,
            "msg": "排期创建成功",
            "schedule": {
                "id": new_schedule.id,
                "content_id": new_schedule.content_id,
                "platform": new_schedule.platform,
                "publish_time": new_schedule.publish_time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": new_schedule.status,
                "schedule_note": new_schedule.schedule_note,
                "create_time": new_schedule.create_time.strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"创建排期异常：{str(e)}")
        return {
            "code": 500,
            "msg": "创建排期失败，请稍后重试",
            "schedule": None
        }

# 1.1 批量创建排期接口
@router.post("/batch-create")
async def batch_create_schedules(
    request_data: dict = Body(...),  # 请求数据
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """
    批量创建排期
    用于排期管理模块
    """
    try:
        # 提取schedules字段
        schedules = request_data.get("schedules", [])
        
        if not schedules or not isinstance(schedules, list):
            raise HTTPException(status_code=400, detail="排期列表不能为空且必须是数组格式")
        
        created_schedules = []
        errors = []
        
        for idx, item in enumerate(schedules):
            try:
                # 提取排期信息
                content_id = item.get("content_id")
                platform = item.get("platform")
                publish_time = item.get("publish_time")
                schedule_note = item.get("schedule_note")
                
                # 验证必填字段
                if not content_id or not platform or not publish_time:
                    errors.append({
                        "index": idx,
                        "error": "缺少必填字段：content_id、platform、publish_time"
                    })
                    continue
                
                # 验证内容是否存在且属于当前用户
                content = db.query(Content).filter(Content.id == content_id, Content.user_id == user_id).first()
                if not content:
                    errors.append({
                        "index": idx,
                        "error": f"内容ID {content_id} 不存在或无权限操作"
                    })
                    continue
                
                # 解析发布时间
                try:
                    publish_datetime = datetime.datetime.strptime(publish_time, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    errors.append({
                        "index": idx,
                        "error": f"发布时间格式错误，正确格式：2024-03-19 12:00:00"
                    })
                    continue
                
                # 创建排期记录
                new_schedule = Schedule(
                    user_id=user_id,
                    content_id=content_id,
                    platform=platform,
                    publish_time=publish_datetime,
                    status="pending",  # 初始状态为待发布
                    schedule_note=schedule_note
                )
                
                db.add(new_schedule)
                created_schedules.append(new_schedule)
                
            except Exception as e:
                errors.append({
                    "index": idx,
                    "error": f"处理排期时出错：{str(e)}"
                })
        
        # 提交事务
        db.commit()
        
        # 刷新并构建响应数据
        result_schedules = []
        for schedule in created_schedules:
            db.refresh(schedule)
            # 获取内容信息
            content = db.query(Content).filter(Content.id == schedule.content_id).first()
            content_title = content.title if content else ""
            
            result_schedules.append({
                "id": schedule.id,
                "content_id": schedule.content_id,
                "content_title": content_title,
                "platform": schedule.platform,
                "publish_time": schedule.publish_time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": schedule.status,
                "schedule_note": schedule.schedule_note,
                "create_time": schedule.create_time.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        # 构建响应
        response = {
            "code": 200,
            "msg": f"批量创建排期成功，成功 {len(result_schedules)} 个，失败 {len(errors)} 个",
            "success_count": len(result_schedules),
            "error_count": len(errors),
            "schedules": result_schedules
        }
        
        if errors:
            response["errors"] = errors
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"批量创建排期异常：{str(e)}")
        return {
            "code": 500,
            "msg": "批量创建排期失败，请稍后重试",
            "success_count": 0,
            "error_count": 0,
            "schedules": [],
            "errors": [{
                "index": 0,
                "error": f"系统错误：{str(e)}"
            }]
        }

# 1.2 批量更新排期接口
@router.post("/batch-update")
async def batch_update_schedules(
    request_data: dict = Body(...),  # 请求数据
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """
    批量更新排期
    用于排期管理模块
    """
    try:
        # 提取updates字段
        updates = request_data.get("updates", [])
        
        if not updates or not isinstance(updates, list):
            raise HTTPException(status_code=400, detail="更新列表不能为空且必须是数组格式")
        
        updated_schedules = []
        errors = []
        
        for idx, item in enumerate(updates):
            try:
                # 提取排期ID
                schedule_id = item.get("schedule_id")
                if not schedule_id:
                    errors.append({
                        "index": idx,
                        "error": "缺少排期ID"
                    })
                    continue
                
                # 验证排期是否存在且属于当前用户
                schedule = db.query(Schedule).filter(Schedule.id == schedule_id, Schedule.user_id == user_id).first()
                if not schedule:
                    errors.append({
                        "index": idx,
                        "error": f"排期ID {schedule_id} 不存在或无权限操作"
                    })
                    continue
                
                # 更新状态
                status = item.get("status")
                if status:
                    valid_statuses = ["pending", "published", "failed"]
                    if status not in valid_statuses:
                        errors.append({
                            "index": idx,
                            "error": "状态值不合法，支持的状态：pending/published/failed"
                        })
                        continue
                    schedule.status = status
                
                # 更新平台
                platform = item.get("platform")
                if platform:
                    schedule.platform = platform
                
                # 更新发布时间
                publish_time = item.get("publish_time")
                if publish_time:
                    try:
                        publish_datetime = datetime.datetime.strptime(publish_time, "%Y-%m-%d %H:%M:%S")
                        schedule.publish_time = publish_datetime
                    except ValueError:
                        errors.append({
                            "index": idx,
                            "error": "发布时间格式错误，正确格式：2024-03-19 12:00:00"
                        })
                        continue
                
                # 更新发布备注
                publish_note = item.get("publish_note")
                if publish_note is not None:
                    schedule.publish_note = publish_note
                
                updated_schedules.append(schedule)
                
            except Exception as e:
                errors.append({
                    "index": idx,
                    "error": f"处理排期更新时出错：{str(e)}"
                })
        
        # 提交事务
        db.commit()
        
        # 刷新并构建响应数据
        result_schedules = []
        for schedule in updated_schedules:
            db.refresh(schedule)
            # 获取内容信息
            content = db.query(Content).filter(Content.id == schedule.content_id).first()
            content_title = content.title if content else ""
            
            result_schedules.append({
                "id": schedule.id,
                "content_id": schedule.content_id,
                "content_title": content_title,
                "platform": schedule.platform,
                "publish_time": schedule.publish_time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": schedule.status,
                "schedule_note": schedule.schedule_note,
                "publish_note": schedule.publish_note,
                "create_time": schedule.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                "update_time": schedule.update_time.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        # 构建响应
        response = {
            "code": 200,
            "msg": f"批量更新排期成功，成功 {len(result_schedules)} 个，失败 {len(errors)} 个",
            "success_count": len(result_schedules),
            "error_count": len(errors),
            "schedules": result_schedules
        }
        
        if errors:
            response["errors"] = errors
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"批量更新排期异常：{str(e)}")
        return {
            "code": 500,
            "msg": "批量更新排期失败，请稍后重试",
            "success_count": 0,
            "error_count": 0,
            "schedules": [],
            "errors": [{
                "index": 0,
                "error": f"系统错误：{str(e)}"
            }]
        }

# 2. 查询排期列表接口
@router.get("/list")
async def get_schedule_list(
    status: str = None,  # 状态筛选
    platform: str = None,  # 平台筛选
    start_time: str = None,  # 开始时间（格式：2024-03-01）
    end_time: str = None,  # 结束时间（格式：2024-03-31）
    content_title: str = None,  # 内容标题筛选
    schedule_note: str = None,  # 排期备注筛选
    publish_note: str = None,  # 发布备注筛选
    page: int = 1,  # 页码，默认1
    page_size: int = 10,  # 每页数量，默认10
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """
    查询排期列表（支持筛选和分页）
    用于排期管理模块
    """
    try:
        # 构建查询
        query = db.query(Schedule).filter(Schedule.user_id == user_id)
        
        # 应用筛选条件
        if status:
            query = query.filter(Schedule.status == status)
        
        if platform:
            query = query.filter(Schedule.platform == platform)
        
        if start_time:
            # 筛选开始时间之后的排期
            start_date = datetime.datetime.strptime(start_time, "%Y-%m-%d")
            query = query.filter(Schedule.publish_time >= start_date)
        
        if end_time:
            # 筛选结束时间之前的排期
            end_date = datetime.datetime.strptime(end_time, "%Y-%m-%d")
            # 加上一天，使其包含结束日期的所有时间
            end_date = end_date + datetime.timedelta(days=1)
            query = query.filter(Schedule.publish_time < end_date)
        
        if schedule_note:
            # 筛选排期备注包含关键词的排期
            query = query.filter(Schedule.schedule_note.contains(schedule_note))
        
        if publish_note:
            # 筛选发布备注包含关键词的排期
            query = query.filter(Schedule.publish_note.contains(publish_note))
        
        if content_title:
            # 筛选内容标题包含关键词的排期（通过关联查询）
            from sqlalchemy import or_
            # 子查询：查找内容标题包含关键词的内容ID
            content_subquery = db.query(Content.id).filter(
                Content.title.contains(content_title)
            ).subquery()
            # 主查询：筛选排期的content_id在子查询结果中
            query = query.filter(Schedule.content_id.in_(content_subquery))
        
        # 计算总数
        total = query.count()
        
        # 计算分页
        offset = (page - 1) * page_size
        schedules = query.order_by(Schedule.publish_time.asc()).offset(offset).limit(page_size).all()
        
        # 构建响应数据
        schedule_list = []
        for schedule in schedules:
            # 获取内容信息
            content = db.query(Content).filter(Content.id == schedule.content_id).first()
            content_title = content.title if content else ""
            
            schedule_list.append({
                "id": schedule.id,
                "content_id": schedule.content_id,
                "content_title": content_title,
                "platform": schedule.platform,
                "publish_time": schedule.publish_time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": schedule.status,
                "schedule_note": schedule.schedule_note,
                "publish_note": schedule.publish_note,
                "create_time": schedule.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                "update_time": schedule.update_time.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return {
            "code": 200,
            "total": total,
            "page": page,
            "page_size": page_size,
            "schedule_list": schedule_list
        }
    except Exception as e:
        logging.error(f"获取排期列表异常：{str(e)}")
        return {
            "code": 500,
            "msg": "获取排期列表失败，请稍后重试",
            "total": 0,
            "page": 1,
            "page_size": 10,
            "schedule_list": []
        }

# 3. 更新排期接口
@router.post("/update")
async def update_schedule(
    schedule_id: int = Body(...),  # 排期ID
    status: str = Body(None),  # 新状态（pending/published/failed）
    platform: str = Body(None),  # 平台
    publish_time: str = Body(None),  # 发布时间（格式：2024-03-19 12:00:00）
    publish_note: str = Body(None),  # 发布备注
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """
    更新排期
    用于排期管理模块
    """
    try:
        # 验证排期是否存在且属于当前用户
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id, Schedule.user_id == user_id).first()
        if not schedule:
            raise HTTPException(status_code=400, detail="排期不存在或无权限操作")
        
        # 验证并更新状态
        if status:
            valid_statuses = ["pending", "published", "failed"]
            if status not in valid_statuses:
                raise HTTPException(status_code=400, detail="状态值不合法，支持的状态：pending/published/failed")
            schedule.status = status
        
        # 更新平台
        if platform:
            schedule.platform = platform
        
        # 更新发布时间
        if publish_time:
            try:
                publish_datetime = datetime.datetime.strptime(publish_time, "%Y-%m-%d %H:%M:%S")
                schedule.publish_time = publish_datetime
            except ValueError:
                raise HTTPException(status_code=400, detail="发布时间格式错误，正确格式：2024-03-19 12:00:00")
        
        # 更新发布备注
        if publish_note is not None:
            schedule.publish_note = publish_note
        
        db.commit()
        db.refresh(schedule)
        
        # 获取内容信息
        content = db.query(Content).filter(Content.id == schedule.content_id).first()
        content_title = content.title if content else ""
        
        return {
            "code": 200,
            "msg": "排期更新成功",
            "schedule": {
                "id": schedule.id,
                "content_id": schedule.content_id,
                "content_title": content_title,
                "platform": schedule.platform,
                "publish_time": schedule.publish_time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": schedule.status,
                "schedule_note": schedule.schedule_note,
                "publish_note": schedule.publish_note,
                "create_time": schedule.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                "update_time": schedule.update_time.strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"更新排期异常：{str(e)}")
        return {
            "code": 500,
            "msg": "更新排期失败，请稍后重试",
            "schedule": None
        }
