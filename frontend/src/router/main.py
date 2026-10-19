from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, select
from database import engine, Base, SessionLocal
from models import User
from security import hash_password
from routers import auth, sop, fault, report, monitor
from scheduler import scheduler

@asynccontextmanager
async def lifespan(app):
    # 启动时：建 pgvector 扩展 + 建表 + 初始化 admin 账号
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))  # pgvector 扩展
        await conn.run_sync(Base.metadata.create_all)                     # 建表（已存在则跳过）
    async with SessionLocal() as db:
        result = await db.execute(select(User).where(User.username == "admin"))
        if not result.scalars().first():
            db.add(User(username="admin", hashed_password=hash_password("Admin@123456"), is_active=1))
            await db.commit()
            print("=" * 50)
            print("已创建默认账号：admin / Admin@123456")
            print("登录后请通过数据库修改密码，生产环境勿用默认密码！")
            print("=" * 50)
    scheduler.start()   # 启动每日 2 点定时任务
    yield
    scheduler.shutdown()

app = FastAPI(title="AIOps 智能运维平台", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(sop.router, prefix="/api/sop", tags=["SOP知识库"])
app.include_router(fault.router, prefix="/api/fault", tags=["故障记录"])
app.include_router(report.router, prefix="/api/report", tags=["AI日报"])
app.include_router(monitor.router, prefix="/api/monitor", tags=["监控数据"])

@app.get("/health")
async def health():
    return {"status": "ok"}
