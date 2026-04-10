from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from models import UserPersona
from routes.user import get_db
from utils.auth import get_current_user
import logging

# 初始化路由
router = APIRouter(prefix="/persona", tags=["人设配置接口"])

# 1. 获取当前用户人设
@router.get("/info")
async def get_persona_info(
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """
    获取当前用户的人设配置
    """
    try:
        # 查询用户的人设配置
        persona = db.query(UserPersona).filter(UserPersona.user_id == user_id).first()
        
        if not persona:
            # 如果用户没有人设配置，返回默认值
            return {
                "code": 200,
                "msg": "获取人设配置成功",
                "persona": {
                    "domain": "通用",
                    "style": "标准",
                    "tone": "中性"
                }
            }
        
        return {
            "code": 200,
            "msg": "获取人设配置成功",
            "persona": {
                "domain": persona.domain,
                "style": persona.style,
                "tone": persona.tone,
                "is_default": persona.is_default
            }
        }
    except Exception as e:
        logging.error(f"获取人设配置异常：{str(e)}")
        return {
            "code": 500,
            "msg": "获取人设配置失败，请稍后重试",
            "persona": None
        }

# 2. 保存/更新人设
@router.post("/save")
async def save_persona(
    domain: str = Body(...),  # 领域
    style: str = Body(...),  # 风格
    tone: str = Body(...),  # 语气
    is_default: int = Body(0),  # 是否默认
    db = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    """
    保存或更新用户的人设配置
    """
    try:
        # 查询用户是否已有人设配置
        persona = db.query(UserPersona).filter(UserPersona.user_id == user_id).first()
        
        if persona:
            # 更新现有配置
            persona.domain = domain
            persona.style = style
            persona.tone = tone
            persona.is_default = is_default
        else:
            # 创建新配置
            persona = UserPersona(
                user_id=user_id,
                domain=domain,
                style=style,
                tone=tone,
                is_default=is_default
            )
            db.add(persona)
        
        db.commit()
        db.refresh(persona)
        
        return {
            "code": 200,
            "msg": "保存人设配置成功",
            "persona": {
                "domain": persona.domain,
                "style": persona.style,
                "tone": persona.tone,
                "is_default": persona.is_default
            }
        }
    except Exception as e:
        logging.error(f"保存人设配置异常：{str(e)}")
        return {
            "code": 500,
            "msg": "保存人设配置失败，请稍后重试",
            "persona": None
        }
