from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from models import ContentPackage, PackageItem, Content, Image
from routes.user import get_db
from utils.auth import get_current_user
import logging
import datetime

router = APIRouter(prefix="/package", tags=["内容包接口"])

# 1. 创建内容包
@router.post("/create")
async def create_package(
    title: str = Body(...),
    platform: str = Body(default=None),
    items: list = Body(default=[]),
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """创建内容包"""
    try:
        new_package = ContentPackage(
            user_id=user_id,
            title=title,
            platform=platform,
            status="completed",
            create_time=datetime.datetime.now()
        )
        db.add(new_package)
        db.commit()
        db.refresh(new_package)
        
        for index, item in enumerate(items):
            item_type = item.get("item_type")
            item_id = item.get("item_id")
            
            if item_type == "content":
                content = db.query(Content).filter(Content.id == item_id, Content.user_id == user_id).first()
                if not content:
                    raise HTTPException(status_code=400, detail=f"文案ID {item_id} 不存在或无权限访问")
            elif item_type == "image":
                image = db.query(Image).filter(Image.id == item_id, Image.user_id == user_id).first()
                if not image:
                    raise HTTPException(status_code=400, detail=f"图片ID {item_id} 不存在或无权限访问")
            else:
                raise HTTPException(status_code=400, detail=f"无效的类型：{item_type}")
            
            package_item = PackageItem(
                package_id=new_package.id,
                item_type=item_type,
                item_id=item_id,
                item_order=index,
                create_time=datetime.datetime.now()
            )
            db.add(package_item)
        
        db.commit()
        
        logging.info(f"创建内容包成功：{new_package.id}")
        
        return {
            "code": 200,
            "msg": "创建成功",
            "data": {
                "package_id": new_package.id
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"创建内容包异常：{str(e)}")
        raise HTTPException(status_code=500, detail="创建内容包失败，请稍后重试")

# 2. 获取内容包列表（放在 /{package_id} 之前）
@router.get("/list")
async def get_package_list(
    platform: str = Query(None),
    status: str = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """获取内容包列表"""
    try:
        query = db.query(ContentPackage).filter(ContentPackage.user_id == user_id)
        
        if platform:
            query = query.filter(ContentPackage.platform == platform)
        if status:
            query = query.filter(ContentPackage.status == status)
        
        query = query.order_by(ContentPackage.create_time.desc())
        
        total = query.count()
        
        offset = (page - 1) * size
        packages = query.offset(offset).limit(size).all()
        
        package_list = []
        for pkg in packages:
            items = db.query(PackageItem).filter(PackageItem.package_id == pkg.id).all()
            content_count = sum(1 for item in items if item.item_type == "content")
            image_count = sum(1 for item in items if item.item_type == "image")
            
            package_list.append({
                "id": pkg.id,
                "title": pkg.title,
                "platform": pkg.platform,
                "status": pkg.status,
                "content_count": content_count,
                "image_count": image_count,
                "create_time": pkg.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                "update_time": pkg.update_time.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return {
            "code": 200,
            "data": {
                "total": total,
                "list": package_list
            }
        }
    
    except Exception as e:
        logging.error(f"获取内容包列表异常：{str(e)}")
        raise HTTPException(status_code=500, detail="获取内容包列表失败，请稍后重试")

# 3. 获取内容包详情
@router.get("/{package_id}")
async def get_package_detail(
    package_id: int,
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """获取内容包详情"""
    try:
        package = db.query(ContentPackage).filter(
            ContentPackage.id == package_id,
            ContentPackage.user_id == user_id
        ).first()
        
        if not package:
            raise HTTPException(status_code=404, detail="内容包不存在或无权限访问")
        
        package_items = db.query(PackageItem).filter(
            PackageItem.package_id == package_id
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
                        "platform": content.platform,
                        "item_order": item.item_order
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
                        "style": image.style,
                        "item_order": item.item_order
                    })
        
        return {
            "code": 200,
            "data": {
                "id": package.id,
                "title": package.title,
                "platform": package.platform,
                "status": package.status,
                "items": items,
                "create_time": package.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                "update_time": package.update_time.strftime("%Y-%m-%d %H:%M:%S")
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"获取内容包详情异常：{str(e)}")
        raise HTTPException(status_code=500, detail="获取内容包详情失败，请稍后重试")

# 4. 更新内容包
@router.put("/{package_id}")
async def update_package(
    package_id: int,
    title: str = Body(default=None),
    platform: str = Body(default=None),
    items: list = Body(default=None),
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """更新内容包"""
    try:
        package = db.query(ContentPackage).filter(
            ContentPackage.id == package_id,
            ContentPackage.user_id == user_id
        ).first()
        
        if not package:
            raise HTTPException(status_code=404, detail="内容包不存在或无权限访问")
        
        if title:
            package.title = title
        if platform:
            package.platform = platform
        package.update_time = datetime.datetime.now()
        
        if items is not None:
            db.query(PackageItem).filter(PackageItem.package_id == package_id).delete()
            
            for index, item in enumerate(items):
                item_type = item.get("item_type")
                item_id = item.get("item_id")
                
                if item_type == "content":
                    content = db.query(Content).filter(Content.id == item_id, Content.user_id == user_id).first()
                    if not content:
                        raise HTTPException(status_code=400, detail=f"文案ID {item_id} 不存在或无权限访问")
                elif item_type == "image":
                    image = db.query(Image).filter(Image.id == item_id, Image.user_id == user_id).first()
                    if not image:
                        raise HTTPException(status_code=400, detail=f"图片ID {item_id} 不存在或无权限访问")
                else:
                    raise HTTPException(status_code=400, detail=f"无效的类型：{item_type}")
                
                package_item = PackageItem(
                    package_id=package_id,
                    item_type=item_type,
                    item_id=item_id,
                    item_order=index,
                    create_time=datetime.datetime.now()
                )
                db.add(package_item)
        
        db.commit()
        
        logging.info(f"更新内容包成功：{package_id}")
        
        return {
            "code": 200,
            "msg": "更新成功"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"更新内容包异常：{str(e)}")
        raise HTTPException(status_code=500, detail="更新内容包失败，请稍后重试")

# 5. 删除内容包
@router.delete("/{package_id}")
async def delete_package(
    package_id: int,
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """删除内容包"""
    try:
        package = db.query(ContentPackage).filter(
            ContentPackage.id == package_id,
            ContentPackage.user_id == user_id
        ).first()
        
        if not package:
            raise HTTPException(status_code=404, detail="内容包不存在或无权限访问")
        
        db.query(PackageItem).filter(PackageItem.package_id == package_id).delete()
        
        db.delete(package)
        db.commit()
        
        logging.info(f"删除内容包成功：{package_id}")
        
        return {
            "code": 200,
            "msg": "删除成功"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"删除内容包异常：{str(e)}")
        raise HTTPException(status_code=500, detail="删除内容包失败，请稍后重试")

# 6. 复制内容包
@router.post("/{package_id}/copy")
async def copy_package(
    package_id: int,
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """复制内容包"""
    try:
        original_package = db.query(ContentPackage).filter(
            ContentPackage.id == package_id,
            ContentPackage.user_id == user_id
        ).first()
        
        if not original_package:
            raise HTTPException(status_code=404, detail="内容包不存在或无权限访问")
        
        new_package = ContentPackage(
            user_id=user_id,
            title=f"{original_package.title}（副本）",
            platform=original_package.platform,
            status="completed",
            create_time=datetime.datetime.now()
        )
        db.add(new_package)
        db.commit()
        db.refresh(new_package)
        
        original_items = db.query(PackageItem).filter(PackageItem.package_id == package_id).all()
        for item in original_items:
            new_item = PackageItem(
                package_id=new_package.id,
                item_type=item.item_type,
                item_id=item.item_id,
                item_order=item.item_order,
                create_time=datetime.datetime.now()
            )
            db.add(new_item)
        
        db.commit()
        
        logging.info(f"复制内容包成功：{new_package.id}")
        
        return {
            "code": 200,
            "msg": "复制成功",
            "data": {
                "package_id": new_package.id,
                "title": new_package.title
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"复制内容包异常：{str(e)}")
        raise HTTPException(status_code=500, detail="复制内容包失败，请稍后重试")
