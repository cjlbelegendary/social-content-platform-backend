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

# 2. 查询排期列表接口
@router.get("/list")
async def get_schedule_list(
    status: List[str] = Query(None),
    platform: List[str] = Query(None),
    start_time: str = None,
    end_time: str = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """查询排期列表"""
    try:
        # 构建查询
        query = db.query(Schedule).filter(Schedule.user_id == user_id)
        
        # 应用筛选条件
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
        
        # 计算总数
        total = query.count()
        
        # 计算分页
        offset = (page - 1) * page_size
        schedules = query.order_by(Schedule.publish_time.asc()).offset(offset).limit(page_size).all()
        
        # 构建响应数据
        schedule_list = []
        for schedule in schedules:
            # 检查并更新过期状态
            if schedule.status == "pending" and schedule.publish_time < datetime.datetime.now():
                schedule.status = "expired"
                db.commit()
                db.refresh(schedule)
            
            # 获取内容包信息
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
