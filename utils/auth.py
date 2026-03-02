# --------------- 完全替换成这个版本，无 bcrypt、不报错 ---------------
import jwt
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
# 新增：导入FastAPI的Header和HTTPException（用于从请求头获取token）
from fastapi import Header, HTTPException

load_dotenv()

# ==================== 不用 bcrypt！直接明文 ====================
def hash_password(plain_password: str) -> str:
    return plain_password  # 不加密

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return plain_password == hashed_password

# ===================== JWT 正常用 =====================
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# 2. 生成Token时强制存储字符串类型的user_id
def create_access_token(user_id: int):  # 直接传user_id，不是dict，避免传错
    to_encode = {
        "sub": str(user_id),  # 强制转字符串，避免类型问题
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logging.info(f"生成Token：user_id={user_id}, token={encoded_jwt[:20]}...")
    return encoded_jwt

# 3. 验证Token时细化异常，加日志，校验user_id
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if not user_id_str:
            logging.error("Token验证失败：payload中无sub字段")
            return None
        # 转换为int返回（确保是有效用户ID）
        user_id = int(user_id_str)
        logging.info(f"Token验证成功：user_id={user_id}")
        return user_id
    except jwt.ExpiredSignatureError:
        logging.error("Token验证失败：Token已过期")
        return None
    except jwt.InvalidSignatureError:
        logging.error("Token验证失败：签名错误（SECRET_KEY不匹配）")
        return None
    except jwt.JWTError as e:
        logging.error(f"Token验证失败：JWT解码错误 - {str(e)}")
        return None
    except ValueError as e:
        logging.error(f"Token验证失败：user_id转换错误 - {str(e)}")
        return None
    except Exception as e:
        logging.error(f"Token验证失败：未知错误 - {str(e)}")
        return None

# ===================== 新增：从请求头获取并验证Token =====================
def get_current_user(Authorization: str = Header(None)) -> int:
    """
    从请求头的 Authorization 字段提取Token（格式：Bearer xxx），验证后返回用户ID
    :param Authorization: 请求头中的Authorization字段
    :return: 验证成功返回user_id，失败抛出HTTPException
    """
    # 1. 校验Authorization是否存在且格式正确
    if not Authorization:
        logging.error("Token验证失败：请求头无Authorization字段")
        raise HTTPException(
            status_code=401,
            detail="请先登录（未检测到登录状态）"
        )
    
    if not Authorization.startswith("Bearer "):
        logging.error(f"Token验证失败：Authorization格式错误 - {Authorization}")
        raise HTTPException(
            status_code=401,
            detail="登录状态格式错误，请重新登录"
        )
    
    # 2. 提取纯Token字符串（去掉Bearer前缀）
    token = Authorization.replace("Bearer ", "").strip()
    if not token:
        logging.error("Token验证失败：提取的Token为空")
        raise HTTPException(
            status_code=401,
            detail="登录状态无效，请重新登录"
        )
    
    # 3. 调用原有verify_token函数验证
    user_id = verify_token(token)
    if not user_id:
        logging.error(f"Token验证失败：无效Token - {token[:20]}...")
        raise HTTPException(
            status_code=401,
            detail="登录已过期或无效，请重新登录"
        )
    
    # 4. 验证成功，返回用户ID
    logging.info(f"请求头Token验证成功：user_id={user_id}")
    return user_id