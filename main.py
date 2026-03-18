from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # 解决跨域问题
from routes import user, content, admin, schedule

# 创建FastAPI应用
app = FastAPI(
    title="智能体社交内容生成平台API",
    description="毕设项目 - 后端API接口",
    version="1.0.0"
)

# 解决跨域问题（前端能正常调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有前端域名（毕设用，生产环境指定具体域名）
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有请求方法（GET/POST等）
    allow_headers=["*"],  # 允许所有请求头
)

# 注册路由
app.include_router(user.router, prefix="/api")
app.include_router(content.router, prefix="/api")
app.include_router(schedule.router, prefix="/api")
app.include_router(admin.router, prefix="/api")

# 测试接口（验证服务是否启动）
@app.get("/")
def root():
    return {"message": "后端服务启动成功！访问 /docs 查看接口文档"}

# 启动服务（直接运行main.py即可）
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # 允许外部访问
        port=8000,       # 端口
        reload=True      # 热重载（修改代码自动重启）
    )