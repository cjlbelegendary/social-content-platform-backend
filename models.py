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