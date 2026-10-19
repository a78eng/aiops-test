from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, select
from database import engine, Base, SessionLocal
from models import User
from security import hash_password
from routers import auth, sop, fault, report, monitor, users, approval, scripts, rag
from scheduler import scheduler
@asynccontextmanager
async def lifespan(app):
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as db:
        result = await db.execute(select(User).where(User.username == "admin"))
        if not result.scalars().first():
            db.add(User(username="admin", hashed_password=hash_password("Admin@123456"),
                        display_name="管理员", role="admin", is_active=1))
            await db.commit()
            print("已创建默认管理员：admin / Admin@123456（请尽快改密）")
    scheduler.start()
    yield
    scheduler.shutdown()
app = FastAPI(title="轻量化 AIOps 运维分析平台", version="2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(sop.router, prefix="/api/sop", tags=["SOP知识库"])
app.include_router(fault.router, prefix="/api/fault", tags=["故障中心"])
app.include_router(report.router, prefix="/api/report", tags=["AI日报"])
app.include_router(monitor.router, prefix="/api/monitor", tags=["监控数据"])
app.include_router(users.router, prefix="/api/users", tags=["团队管理"])
app.include_router(approval.router, prefix="/api/approval", tags=["审批中心"])
app.include_router(rag.router, prefix="/api/rag", tags=["RAG问答"])
app.include_router(scripts.router, prefix="/api/scripts", tags=["脚本模板"])
@app.get("/health")
async def health():
    return {"status": "ok"}
