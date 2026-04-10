import requests
import logging
import re
from datetime import datetime
from sqlalchemy.orm import Session
from models import Hotspot
from utils.cache_helper import (
    get_hotspots_list_cache, set_hotspots_list_cache,
    get_hotspot_detail_cache, set_hotspot_detail_cache,
    clear_hotspots_cache
)

# 微博热搜API地址
WEIBO_HOT_API = "https://v2.xxapi.cn/api/weibohot"

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 从热度字符串中提取数字
def extract_heat_value(heat_str):
    """
    从热度字符串中提取数字
    例如："109万" -> 1090000
    """
    if not heat_str:
        return 0
    
    # 移除单位并转换为数字
    heat_str = heat_str.replace('万', '0000')
    heat_str = re.sub(r'[^0-9]', '', heat_str)
    
    try:
        return int(heat_str)
    except ValueError:
        return 0

# 从标题中提取关键词
def extract_keywords(title):
    """
    从标题中提取关键词
    简单实现：返回标题的主要词汇
    """
    if not title:
        return ""
    
    # 简单的关键词提取，实际项目中可以使用更复杂的NLP方法
    # 这里只是一个示例
    keywords = title.split(' ')
    # 过滤掉短词和常见词
    keywords = [word for word in keywords if len(word) > 1]
    return ",".join(keywords[:3])  # 取前3个作为关键词

# 获取微博热搜数据
def get_weibo_hotspots():
    """
    调用微博热搜API获取数据
    """
    try:
        response = requests.get(WEIBO_HOT_API, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('code') == 200:
            return data.get('data', [])
        else:
            logger.error(f"获取微博热搜失败：{data.get('msg')}")
            return []
    except Exception as e:
        logger.error(f"获取微博热搜异常：{str(e)}")
        return []

# 保存热点数据到数据库
def save_hotspots_to_db(db: Session, hotspots_data, platform="微博"):
    """
    将热点数据保存到数据库
    """
    try:
        for item in hotspots_data:
            # 检查是否已存在相同标题的热点
            existing_hotspot = db.query(Hotspot).filter(
                Hotspot.platform == platform,
                Hotspot.title == item.get('title')
            ).first()
            
            if existing_hotspot:
                # 更新现有热点
                existing_hotspot.heat_value = extract_heat_value(item.get('hot'))
                existing_hotspot.url = item.get('url')
                existing_hotspot.update_time = datetime.now()
            else:
                # 创建新热点
                new_hotspot = Hotspot(
                    platform=platform,
                    title=item.get('title'),
                    keywords=extract_keywords(item.get('title')),
                    url=item.get('url'),
                    heat_value=extract_heat_value(item.get('hot'))
                )
                db.add(new_hotspot)
        
        db.commit()
        logger.info(f"成功保存 {len(hotspots_data)} 条热点数据")
        return True
    except Exception as e:
        logger.error(f"保存热点数据异常：{str(e)}")
        db.rollback()
        return False

# 刷新热点数据
def refresh_hotspots(db: Session):
    """
    刷新热点数据
    """
    # 获取微博热搜数据
    weibo_hotspots = get_weibo_hotspots()
    if weibo_hotspots:
        save_hotspots_to_db(db, weibo_hotspots, "微博")
    
    # 可以在这里添加其他平台的热点获取
    # 例如：抖音、小红书等
    
    # 清除缓存，确保下次获取的是最新数据
    clear_hotspots_cache()
    
    return True

# 获取热点列表
def get_hotspots_list(db: Session, platform=None, limit=50):
    """
    获取热点列表
    """
    try:
        # 先尝试从缓存获取
        cached_data = get_hotspots_list_cache(platform)
        if cached_data:
            logger.info("从缓存获取热点列表")
            return cached_data[:limit]  # 限制返回数量
        
        # 从数据库获取
        query = db.query(Hotspot)
        
        if platform:
            query = query.filter(Hotspot.platform == platform)
        
        # 按热度值降序排序
        hotspots = query.order_by(Hotspot.heat_value.desc()).limit(limit).all()
        
        # 转换为字典列表
        result = []
        for hotspot in hotspots:
            result.append({
                "id": hotspot.id,
                "platform": hotspot.platform,
                "title": hotspot.title,
                "keywords": hotspot.keywords,
                "url": hotspot.url,
                "heat_value": hotspot.heat_value,
                "create_time": hotspot.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                "update_time": hotspot.update_time.strftime("%Y-%m-%d %H:%M:%S")
            })
        
        # 设置缓存
        set_hotspots_list_cache(result, platform)
        
        return result
    except Exception as e:
        logger.error(f"获取热点列表异常：{str(e)}")
        return []

# 获取热点详情
def get_hotspot_detail(db: Session, hotspot_id):
    """
    获取热点详情
    """
    try:
        # 先尝试从缓存获取
        cached_data = get_hotspot_detail_cache(hotspot_id)
        if cached_data:
            logger.info(f"从缓存获取热点详情：{hotspot_id}")
            return cached_data
        
        # 从数据库获取
        hotspot = db.query(Hotspot).filter(Hotspot.id == hotspot_id).first()
        if not hotspot:
            return None
        
        result = {
            "id": hotspot.id,
            "platform": hotspot.platform,
            "title": hotspot.title,
            "keywords": hotspot.keywords,
            "url": hotspot.url,
            "heat_value": hotspot.heat_value,
            "create_time": hotspot.create_time.strftime("%Y-%m-%d %H:%M:%S"),
            "update_time": hotspot.update_time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 设置缓存
        set_hotspot_detail_cache(result)
        
        return result
    except Exception as e:
        logger.error(f"获取热点详情异常：{str(e)}")
        return None
