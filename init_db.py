from sqlalchemy import create_engine
from models import Base, User, Session, Content, Schedule, UserPersona, Hotspot, Image, ContentPackage, PackageItem
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "social_content_db")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

print(f"正在连接数据库：{DB_HOST}:{DB_PORT}/{DB_NAME}")

engine = create_engine(DATABASE_URL, echo=True)

Base.metadata.create_all(bind=engine)

print("\n数据库表创建完成！")
print("创建的表：")
print("- users (用户表)")
print("- sessions (会话表)")
print("- contents (内容表)")
print("- images (图片表)")
print("- content_packages (内容包表)")
print("- package_items (内容包关联表)")
print("- schedules (排期表)")
print("- user_persona (用户人设配置表)")
print("- hotspots (热点表)")
