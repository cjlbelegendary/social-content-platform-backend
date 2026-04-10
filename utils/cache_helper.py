import json
import logging
from datetime import timedelta

try:
    import redis
except ImportError:
    redis = None

# 缓存键前缀
HOTSPOTS_LIST_KEY = "hotspots:list:{platform}"
HOTSPOT_DETAIL_KEY = "hotspot:detail:{id}"

# 缓存过期时间（秒）
HOTSPOTS_LIST_EXPIRE = 300  # 5分钟
HOTSPOT_DETAIL_EXPIRE = 600  # 10分钟

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Redis连接配置
if redis:
    try:
        redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )
        # 测试连接
        redis_client.ping()
        logger.info("Redis连接成功")
    except Exception as e:
        logger.warning(f"Redis连接失败：{str(e)}，将使用内存缓存")
        # 如果Redis连接失败，使用内存缓存作为备选
        class MemoryCache:
            def __init__(self):
                self.cache = {}
            def get(self, key):
                return self.cache.get(key)
            def set(self, key, value, ex=None):
                self.cache[key] = value
            def delete(self, key):
                if key in self.cache:
                    del self.cache[key]
            def delete_pattern(self, pattern):
                keys_to_delete = [k for k in self.cache.keys() if pattern in k]
                for key in keys_to_delete:
                    del self.cache[key]
        redis_client = MemoryCache()
else:
    logger.warning("Redis模块不存在，将使用内存缓存")
    # 如果Redis模块不存在，使用内存缓存
    class MemoryCache:
        def __init__(self):
            self.cache = {}
        def get(self, key):
            return self.cache.get(key)
        def set(self, key, value, ex=None):
            self.cache[key] = value
        def delete(self, key):
            if key in self.cache:
                del self.cache[key]
        def delete_pattern(self, pattern):
            keys_to_delete = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self.cache[key]
    redis_client = MemoryCache()

# 获取热点列表缓存
def get_hotspots_list_cache(platform=None):
    """
    获取热点列表缓存
    """
    try:
        key = HOTSPOTS_LIST_KEY.format(platform=platform or "all")
        data = redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.error(f"获取热点列表缓存异常：{str(e)}")
        return None

# 设置热点列表缓存
def set_hotspots_list_cache(hotspots, platform=None):
    """
    设置热点列表缓存
    """
    try:
        key = HOTSPOTS_LIST_KEY.format(platform=platform or "all")
        redis_client.set(key, json.dumps(hotspots), ex=HOTSPOTS_LIST_EXPIRE)
        return True
    except Exception as e:
        logger.error(f"设置热点列表缓存异常：{str(e)}")
        return False

# 获取热点详情缓存
def get_hotspot_detail_cache(hotspot_id):
    """
    获取热点详情缓存
    """
    try:
        key = HOTSPOT_DETAIL_KEY.format(id=hotspot_id)
        data = redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.error(f"获取热点详情缓存异常：{str(e)}")
        return None

# 设置热点详情缓存
def set_hotspot_detail_cache(hotspot_detail):
    """
    设置热点详情缓存
    """
    try:
        if not hotspot_detail or "id" not in hotspot_detail:
            return False
        key = HOTSPOT_DETAIL_KEY.format(id=hotspot_detail["id"])
        redis_client.set(key, json.dumps(hotspot_detail), ex=HOTSPOT_DETAIL_EXPIRE)
        return True
    except Exception as e:
        logger.error(f"设置热点详情缓存异常：{str(e)}")
        return False

# 清除热点缓存
def clear_hotspots_cache():
    """
    清除所有热点缓存
    """
    try:
        # 清除热点列表缓存
        redis_client.delete_pattern("hotspots:list:")
        # 清除热点详情缓存
        redis_client.delete_pattern("hotspot:detail:")
        logger.info("热点缓存已清除")
        return True
    except Exception as e:
        logger.error(f"清除热点缓存异常：{str(e)}")
        return False
