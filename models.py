from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# 基础模型类，所有表都继承这个
Base = declarative_base()

# 用户表模型
class User(Base):
    __tablename__ = "users"  # 表名
    id = Column(Integer, primary_key=True, index=True)  # 主键
    username = Column(String(50), unique=True, nullable=False, comment="用户名")  # 唯一
    password = Column(String(100), nullable=False, comment="加密后的密码")
    is_admin = Column(Boolean, default=False, comment="是否是管理员")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")

# 会话表模型
class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="关联用户ID")
    title = Column(String(100), nullable=False, comment="会话标题")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

# 生成内容表模型
class Content(Base):
    __tablename__ = "contents"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="关联用户ID")
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, comment="关联会话ID")
    title = Column(String(100), nullable=False, comment="内容标题")
    content = Column(Text, nullable=False, comment="生成的内容")
    platform = Column(String(20), comment="适配平台：小红书/微博/朋友圈")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")

# 排期表模型
class Schedule(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True, index=True, comment="排期唯一标识")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="关联用户ID，排期所属用户")
    content_id = Column(Integer, ForeignKey("contents.id"), nullable=False, comment="内容ID")
    platform = Column(String(20), nullable=False, comment="平台")
    publish_time = Column(DateTime, nullable=False, comment="发布时间")
    status = Column(String(20), default="pending", comment="发布状态：pending（待发布）、published（已发布）、failed（发布失败）、expired（已过期）")
    schedule_note = Column(Text, comment="排期备注")
    publish_note = Column(Text, comment="发布备注")
    create_time = Column(DateTime, default=datetime.now, comment="排期创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="排期更新时间")

# 用户人设配置表模型
class UserPersona(Base):
    __tablename__ = "user_persona"
    id = Column(Integer, primary_key=True, index=True, comment="主键")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID，关联现有用户")
    domain = Column(String(50), nullable=False, comment="领域")
    style = Column(String(50), nullable=False, comment="风格")
    tone = Column(String(50), nullable=False, comment="语气")
    is_default = Column(Integer, default=0, comment="是否默认 0/1")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

# 热点表模型
class Hotspot(Base):
    __tablename__ = "hotspots"
    id = Column(Integer, primary_key=True, index=True, comment="主键")
    platform = Column(String(50), nullable=False, comment="平台：微博、抖音、小红书等")
    title = Column(String(255), nullable=False, comment="热点标题")
    keywords = Column(String(255), comment="关键词")
    url = Column(String(500), comment="原始链接")
    heat_value = Column(Integer, comment="热度值")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")