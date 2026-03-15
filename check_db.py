from sqlalchemy.orm import Session
from models import Content
from routes.user import get_db

# 查询数据库中的内容记录
def check_content_records():
    db = next(get_db())
    try:
        # 查询所有内容记录
        contents = db.query(Content).order_by(Content.create_time.desc()).all()
        print(f"数据库中共有 {len(contents)} 条内容记录")
        
        # 打印最近的5条记录
        print("\n最近的5条记录：")
        for i, content in enumerate(contents[:5]):
            print(f"\n记录 {i+1}:")
            print(f"ID: {content.id}")
            print(f"标题: {content.title}")
            print(f"内容: {content.content[:100]}...")  # 只显示前100个字符
            print(f"平台: {content.platform}")
            print(f"创建时间: {content.create_time}")
            print(f"用户ID: {content.user_id}")
    finally:
        db.close()

if __name__ == "__main__":
    check_content_records()
