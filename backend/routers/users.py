from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import User, SopDocument, FaultRecord, ScriptTemplate
from schemas import UserCreateRequest, ResetPasswordRequest
from security import get_current_admin, get_current_user, hash_password
router = APIRouter()
@router.get("")
async def list_users(admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    """团队成员列表 + 每人贡献统计（谁、何时加入、录了多少内容）"""
    users = (await db.execute(select(User).order_by(User.created_at))).scalars().all()
    out = []
    for u in users:
        sop_cnt = (await db.execute(
            select(func.count()).select_from(SopDocument).where(SopDocument.created_by == u.username))).scalar()
        fault_cnt = (await db.execute(
            select(func.count()).select_from(FaultRecord).where(FaultRecord.created_by == u.username))).scalar()
        script_cnt = (await db.execute(
            select(func.count()).select_from(ScriptTemplate).where(ScriptTemplate.created_by == u.username))).scalar()
        out.append({
            "id": u.id, "username": u.username,
            "display_name": u.display_name or u.username,
            "role": u.role, "is_active": u.is_active,
            "created_at": u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "-",
            "last_login_at": u.last_login_at.strftime("%Y-%m-%d %H:%M") if u.last_login_at else "从未登录",
            "sop_count": sop_cnt, "fault_count": fault_cnt, "script_count": script_cnt,
        })
    return out
@router.post("")
async def create_user(req: UserCreateRequest, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    exists = (await db.execute(select(User).where(User.username == req.username))).scalars().first()
    if exists:
        raise HTTPException(status_code=400, detail="用户名已存在")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="密码至少 8 位")
    if req.role not in ("admin", "member"):
        raise HTTPException(status_code=400, detail="角色只能为 admin/member")
    u = User(username=req.username, hashed_password=hash_password(req.password),
             display_name=req.display_name, role=req.role, is_active=1)
    db.add(u)
    await db.commit()
    return {"message": f"成员 {req.username} 创建成功", "username": req.username}
@router.post("/{user_id}/reset_password")
async def reset_password(user_id: int, req: ResetPasswordRequest, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    u = (await db.execute(select(User).where(User.id == user_id))).scalars().first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="密码至少 8 位")
    u.hashed_password = hash_password(req.new_password)
    await db.commit()
    return {"message": "密码已重置"}
@router.post("/{user_id}/toggle")
async def toggle_user(user_id: int, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    u = (await db.execute(select(User).where(User.id == user_id))).scalars().first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    if u.username == "admin":
        raise HTTPException(status_code=400, detail="默认管理员不可停用")
    u.is_active = 0 if u.is_active else 1
    await db.commit()
    return {"message": "已启用" if u.is_active else "已停用"}
@router.get("/me/profile")
async def my_profile(user: User = Depends(get_current_user)):
    return {"username": user.username, "display_name": user.display_name, "role": user.role}
