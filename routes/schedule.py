from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from models import Schedule, ContentPackage, PackageItem, Content, Image
from routes.user import get_db
from utils.auth import get_current_user
import logging
import datetime
from typing import List

# 初始化路由
router = APIRouter(prefix="/schedule", tags=["排期接口"])

# 1. 创建排期接口
@router.post("/create")
async def create_schedule(
    package_id: int = Body(...),
    platform: str = Body(...),
    publish_time: str = Body(...),
    schedule_note: str = Body(None),
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """创建排期"""
    try:
        # 验证内容包是否存在且属于当前用户
        package = db.query(ContentPackage).filter(
            ContentPackage.id == package_id,
            ContentPackage.user_id == user_id
        ).first()
        if not package:
            raise HTTPException(status_code=400, detail="内容包不存在或无权限操作")
        
        # 解析发布时间
        try:
            publish_datetime = datetime.datetime.strptime(publish_time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise HTTPException(status_code=400, detail="发布时间格式错误，正确格式：2024-03-19 12:00:00")
        
        # 检查是否已过期
        status = "pending"
        if publish_datetime < datetime.datetime.now():
            status = "expired"
        
        # 创建排期
        new_schedule = Schedule(
            user_id=user_id,
            package_id=package_id,
            platform=platform,
            publish_time=publish_datetime,
            status=status,
            schedule_note=schedule_note
        )
        db.add(new_schedule)
        db.commit()
        db.refresh(new_schedule)
        
        # 更新内容包状态
        package.status = "scheduled"
        db.commit()
        
        return {
            "code": 200,
            "msg": "排期创建成功",
            "data": {
                "schedule_id": new_schedule.id,
                "package_id": new_schedule.package_id,
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
        raise HTTPException(status_code=500, detail="创建排期失败，请稍后重试")

# 1.1 批量创建排期接口
@router.post("/batch-create")
async def batch_create_schedules(
    schedules: list = Body(...),
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """批量创建排期"""
    try:
        if not schedules:
            raise HTTPException(status_code=400, detail="排期列表不能为空")
        
        created_schedules = []
        errors = []
        
        for idx, item in enumerate(schedules):
            try:
                package_id = item.get("package_id")
                platform = item.get("platform")
                publish_time = item.get("publish_time")
                schedule_note = item.get("schedule_note")
                
                if not package_id or not platform or not publish_time:
                    errors.append({
                        "index": idx,
                        "error": "缺少必填字段：package_id、platform、publish_time"
                    })
                    continue
                
                package = db.query(ContentPackage).filter(
                    ContentPackage.id == package_id,
                    ContentPackage.user_id == user_id
                ).first()
                if not package:
                    errors.append({
                        "index": idx,
                        "error": f"内容包ID {package_id} 不存在或无权限操作"
                    })
                    continue
                
                try:
                    publish_datetime = datetime.datetime.strptime(publish_time, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    errors.append({
                        "index": idx,
                        "error": "发布时间格式错误，正确格式：2024-03-19 12:00:00"
                    })
                    continue
                
                status = "pending"
                if publish_datetime < datetime.datetime.now():
                    status = "expired"
                
                new_schedule = Schedule(
                    user_id=user_id,
                    package_id=package_id,
                    platform=platform,
                    publish_time=publish_datetime,
                    status=status,
                    schedule_note=schedule_note
                )
                db.add(new_schedule)
                created_schedules.append(new_schedule)
                
                package.status = "scheduled"
                
            except Exception as e:
                errors.append({
                    "index": idx,
                    "error": f"处理排期时出错：{str(e)}"
                })
        
        db.commit()
        
        result_schedules = []
        for schedule in created_schedules:
            db.refresh(schedule)
            result_schedules.append({
                "schedule_id": schedule.id,
                "package_id": schedule.package_id,
                "platform": schedule.platform,
                "publish_time": schedule.publish_time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": schedule.status,
                "schedule_note": schedule.schedule_note,
                "create_time": schedule.create_time.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return {
            "code": 200,
            "msg": f"批量创建排期成功，成功 {len(result_schedules)} 个，失败 {len(errors)} 个",
            "data": {
                "success_count": len(result_schedules),
                "error_count": len(errors),
                "schedules": result_schedules,
                "errors": errors if errors else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"批量创建排期异常：{str(e)}")
        raise HTTPException(status_code=500, detail="批量创建排期失败，请稍后重试")

# 2. 查询排期列表接口
@router.get("/list")
async def get_schedule_list(
    status: List[str] = Query(None),
    platform: List[str] = Query(None),
    start_time: str = None,
    end_time: str = None,
    package_title: str = Query(None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """查询排期列表"""
    try:
        query = db.query(Schedule).filter(Schedule.user_id == user_id)
        
        if status:
            query = query.filter(Schedule.status.in_(status))
        
        if platform:
            query = query.filter(Schedule.platform.in_(platform))
        
        if start_time:
            start_date = datetime.datetime.strptime(start_time, "%Y-%m-%d")
            query = query.filter(Schedule.publish_time >= start_date)
        
        if end_time:
            end_date = datetime.datetime.strptime(end_time, "%Y-%m-%d")
            end_date = end_date + datetime.timedelta(days=1)
            query = query.filter(Schedule.publish_time < end_date)
        
        if package_title:
            package_ids = db.query(ContentPackage.id).filter(
                ContentPackage.title.contains(package_title)
            ).all()
            package_id_list = [pid[0] for pid in package_ids]
            query = query.filter(Schedule.package_id.in_(package_id_list))
        
        total = query.count()
        
        offset = (page - 1) * page_size
        schedules = query.order_by(Schedule.publish_time.asc()).offset(offset).limit(page_size).all()
        
        schedule_list = []
        for schedule in schedules:
            if schedule.status == "pending" and schedule.publish_time < datetime.datetime.now():
                schedule.status = "expired"
                db.commit()
                db.refresh(schedule)
            
            package = db.query(ContentPackage).filter(ContentPackage.id == schedule.package_id).first()
            
            if package:
                # 获取内容包的items
                package_items = db.query(PackageItem).filter(
                    PackageItem.package_id == package.id
                ).order_by(PackageItem.item_order).all()
                
                items = []
                for item in package_items:
                    if item.item_type == "content":
                        content = db.query(Content).filter(Content.id == item.item_id).first()
                        if content:
                            items.append({
                                "item_type": "content",
                                "item_id": content.id,
                                "content": content.content,
                                "platform": content.platform
                            })
                    elif item.item_type == "image":
                        image = db.query(Image).filter(Image.id == item.item_id).first()
                        if image:
                            items.append({
                                "item_type": "image",
                                "item_id": image.id,
                                "url": image.url,
                                "width": image.width,
                                "height": image.height,
                                "prompt": image.prompt,
                                "style": image.style
                            })
                
                schedule_list.append({
                    "id": schedule.id,
                    "package": {
                        "id": package.id,
                        "title": package.title,
                        "platform": package.platform,
                        "status": package.status,
                        "items": items
                    },
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
            "data": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "list": schedule_list
            }
        }
    except Exception as e:
        logging.error(f"获取排期列表异常：{str(e)}")
        raise HTTPException(status_code=500, detail="获取排期列表失败，请稍后重试")

# 3. 更新排期接口
@router.put("/{schedule_id}")
async def update_schedule(
    schedule_id: int,
    status: str = Body(default=None),
    platform: str = Body(default=None),
    publish_time: str = Body(default=None),
    publish_note: str = Body(default=None),
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """更新排期"""
    try:
        # 验证排期是否存在且属于当前用户
        schedule = db.query(Schedule).filter(
            Schedule.id == schedule_id,
            Schedule.user_id == user_id
        ).first()
        if not schedule:
            raise HTTPException(status_code=404, detail="排期不存在或无权限操作")
        
        # 验证并更新状态
        if status:
            valid_statuses = ["pending", "published", "failed", "expired"]
            if status not in valid_statuses:
                raise HTTPException(status_code=400, detail="状态值不合法")
            schedule.status = status
            
            # 如果状态变为published，更新内容包状态
            if status == "published":
                package = db.query(ContentPackage).filter(ContentPackage.id == schedule.package_id).first()
                if package:
                    package.status = "published"
        
        # 更新平台
        if platform:
            schedule.platform = platform
        
        # 更新发布时间
        if publish_time:
            try:
                publish_datetime = datetime.datetime.strptime(publish_time, "%Y-%m-%d %H:%M:%S")
                schedule.publish_time = publish_datetime
            except ValueError:
                raise HTTPException(status_code=400, detail="发布时间格式错误")
        
        # 更新发布备注
        if publish_note is not None:
            schedule.publish_note = publish_note
        
        db.commit()
        db.refresh(schedule)
        
        return {
            "code": 200,
            "msg": "排期更新成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"更新排期异常：{str(e)}")
        raise HTTPException(status_code=500, detail="更新排期失败，请稍后重试")

# 4. 删除排期接口
@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """删除排期"""
    try:
        # 验证排期是否存在且属于当前用户
        schedule = db.query(Schedule).filter(
            Schedule.id == schedule_id,
            Schedule.user_id == user_id
        ).first()
        if not schedule:
            raise HTTPException(status_code=404, detail="排期不存在或无权限操作")
        
        # 更新内容包状态
        package = db.query(ContentPackage).filter(ContentPackage.id == schedule.package_id).first()
        if package and package.status == "scheduled":
            package.status = "completed"
        
        # 删除排期
        db.delete(schedule)
        db.commit()
        
        return {
            "code": 200,
            "msg": "排期删除成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"删除排期异常：{str(e)}")
        raise HTTPException(status_code=500, detail="删除排期失败，请稍后重试")

# 5. 获取排期详情接口
@router.get("/{schedule_id}")
async def get_schedule_detail(
    schedule_id: int,
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """获取排期详情"""
    try:
        # 查询排期
        schedule = db.query(Schedule).filter(
            Schedule.id == schedule_id,
            Schedule.user_id == user_id
        ).first()
        
        if not schedule:
            raise HTTPException(status_code=404, detail="排期不存在或无权限访问")
        
        # 获取内容包信息
        package = db.query(ContentPackage).filter(ContentPackage.id == schedule.package_id).first()
        
        if not package:
            raise HTTPException(status_code=404, detail="内容包不存在")
        
        # 获取内容包的items
        package_items = db.query(PackageItem).filter(
            PackageItem.package_id == package.id
        ).order_by(PackageItem.item_order).all()
        
        items = []
        for item in package_items:
            if item.item_type == "content":
                content = db.query(Content).filter(Content.id == item.item_id).first()
                if content:
                    items.append({
                        "item_type": "content",
                        "item_id": content.id,
                        "content": content.content,
                        "platform": content.platform
                    })
            elif item.item_type == "image":
                image = db.query(Image).filter(Image.id == item.item_id).first()
                if image:
                    items.append({
                        "item_type": "image",
                        "item_id": image.id,
                        "url": image.url,
                        "width": image.width,
                        "height": image.height,
                        "prompt": image.prompt,
                        "style": image.style
                    })
        
        return {
            "code": 200,
            "data": {
                "id": schedule.id,
                "package": {
                    "id": package.id,
                    "title": package.title,
                    "platform": package.platform,
                    "status": package.status,
                    "items": items,
                    "create_time": package.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "update_time": package.update_time.strftime("%Y-%m-%d %H:%M:%S")
                },
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
        logging.error(f"获取排期详情异常：{str(e)}")
        raise HTTPException(status_code=500, detail="获取排期详情失败，请稍后重试")
