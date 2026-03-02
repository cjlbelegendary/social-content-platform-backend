项目目录结构
social-content-backend/
├── venv/              # 虚拟环境（自动生成）
├── .env               # 环境变量（存储敏感信息）
├── main.py            # 后端入口文件
├── models.py          # 数据库模型（用户、内容）
├── utils/             # 工具函数（认证、AI调用）
│   ├── __init__.py
│   ├── auth.py        # JWT认证、密码加密
│   └── ai_helper.py   # AI内容生成封装
└── routes/            # 接口路由
    ├── __init__.py
    ├── user.py        # 用户接口（登录/注册）
    ├── content.py     # 内容接口（增删改查）
    └── admin.py       # 管理员接口（简单版）

启动命令
uvicorn main:app --reload