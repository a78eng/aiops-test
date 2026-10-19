from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import settings

# 异步引擎：asyncpg 驱动，连接池 5（单机足够）
engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_size=5)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

# FastAPI 依赖注入：每个请求独立 session
async def get_db():
    async with SessionLocal() as session:
        yield session
