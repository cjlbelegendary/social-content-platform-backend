from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from routes.user import get_db
from utils.auth import get_current_user
from utils.hotspot_helper import refresh_hotspots, get_hotspots_list, get_hotspot_detail
import logging

# 初始化路由
router = APIRouter(prefix="/hotspot", tags=["热点浏览接口"])

# 1. 获取热点列表
@router.get("/list")
async def get_hotspots(
    platform: str = Query(None, description="平台筛选，如：微博"),
    limit: int = Query(50, ge=1, le=100, description="返回数量限制"),
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """
    获取热点列表
    - **platform**: 可选，平台筛选
    - **limit**: 可选，返回数量限制，默认50，最大100
    """
    try:
        # 获取热点列表
        hotspots = get_hotspots_list(db, platform, limit)
        
        return {
            "code": 200,
            "msg": "获取热点列表成功",
            "data": hotspots
        }
    except Exception as e:
        logging.error(f"获取热点列表异常：{str(e)}")
        return {
            "code": 500,
            "msg": "获取热点列表失败，请稍后重试",
            "data": []
        }

# 2. 获取热点详情
@router.get("/detail/{hotspot_id}")
async def get_hotspot(
    hotspot_id: int,
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """
    获取热点详情
    - **hotspot_id**: 热点ID
    """
    try:
        # 获取热点详情
        hotspot = get_hotspot_detail(db, hotspot_id)
        
        if not hotspot:
            return {
                "code": 404,
                "msg": "热点不存在",
                "data": None
            }
        
        return {
            "code": 200,
            "msg": "获取热点详情成功",
            "data": hotspot
        }
    except Exception as e:
        logging.error(f"获取热点详情异常：{str(e)}")
        return {
            "code": 500,
            "msg": "获取热点详情失败，请稍后重试",
            "data": None
        }

# 3. 刷新热点数据
@router.post("/refresh")
async def refresh_hotspots_data(
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """
    刷新热点数据
    从各平台API获取最新热点数据
    """
    try:
        # 刷新热点数据
        success = refresh_hotspots(db)
        
        if success:
            return {
                "code": 200,
                "msg": "刷新热点数据成功"
            }
        else:
            return {
                "code": 500,
                "msg": "刷新热点数据失败，请稍后重试"
            }
    except Exception as e:
        logging.error(f"刷新热点数据异常：{str(e)}")
        return {
            "code": 500,
            "msg": "刷新热点数据失败，请稍后重试"
        }
