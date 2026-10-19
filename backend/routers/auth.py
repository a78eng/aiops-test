from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import User
from schemas import LoginRequest
from security import verify_password, create_access_token, get_current_user
router = APIRouter()
@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalars().first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已被停用，请联系管理员")
    # 记录最近登录时间（团队管理页可见）
    user.last_login_at = datetime.now()
    await db.commit()
    return {
        "access_token": create_access_token(user.username),
        "token_type": "bearer",
        "username": user.username,
        "display_name": user.display_name or user.username,
        "role": user.role,          # 前端据此控制菜单显隐
    }
@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"username": user.username, "display_name": user.display_name, "role": user.role}
