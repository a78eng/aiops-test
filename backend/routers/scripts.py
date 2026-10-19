import re
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import User, ScriptTemplate
from schemas import ScriptCreateRequest, ScriptRenderRequest, AiScriptRequest
from security import get_current_user, get_current_admin
from llm_client import chat_completion
router = APIRouter()
@router.get("")
async def list_scripts(category: str = "", user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(ScriptTemplate).order_by(ScriptTemplate.usage_count.desc())
    if category:
        stmt = stmt.where(ScriptTemplate.category == category)
    result = await db.execute(stmt)
    return [{"id": s.id, "name": s.name, "category": s.category, "description": s.description,
             "params": json.loads(s.params or "[]"), "usage_count": s.usage_count,
             "created_by": s.created_by,
             "created_at": s.created_at.strftime("%Y-%m-%d %H:%M")}
            for s in result.scalars().all()]
@router.get("/{script_id}")
async def get_script(script_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    s = (await db.execute(select(ScriptTemplate).where(ScriptTemplate.id == script_id))).scalars().first()
    if not s:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"id": s.id, "name": s.name, "category": s.category, "description": s.description,
            "content": s.content, "params": json.loads(s.params or "[]"), "usage_count": s.usage_count}
@router.post("")
async def create_script(req: ScriptCreateRequest, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    s = ScriptTemplate(name=req.name, category=req.category, description=req.description,
                       content=req.content, params=json.dumps(req.params, ensure_ascii=False),
                       created_by=admin.username)
    db.add(s)
    await db.commit()
    return {"message": "模板创建成功", "id": s.id}
@router.put("/{script_id}")
async def update_script(script_id: int, req: ScriptCreateRequest, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    """★ 编辑模板（仅管理员）"""
    s = (await db.execute(select(ScriptTemplate).where(ScriptTemplate.id == script_id))).scalars().first()
    if not s:
        raise HTTPException(status_code=404, detail="模板不存在")
    s.name = req.name
    s.category = req.category
    s.description = req.description
    s.content = req.content
    s.params = json.dumps(req.params, ensure_ascii=False)
    await db.commit()
    return {"message": "模板已更新"}
@router.delete("/{script_id}")
async def delete_script(script_id: int, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    """★ 删除模板（仅管理员）"""
    s = (await db.execute(select(ScriptTemplate).where(ScriptTemplate.id == script_id))).scalars().first()
    if not s:
        raise HTTPException(status_code=404, detail="模板不存在")
    await db.execute(delete(ScriptTemplate).where(ScriptTemplate.id == script_id))
    await db.commit()
    return {"message": "模板已删除"}
@router.post("/{script_id}/render")
async def render_script(script_id: int, req: ScriptRenderRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    s = (await db.execute(select(ScriptTemplate).where(ScriptTemplate.id == script_id))).scalars().first()
    if not s:
        raise HTTPException(status_code=404, detail="模板不存在")
    def sub(m):
        k = m.group(1).strip()
        v = req.params.get(k)
        return str(v) if v is not None and v != "" else m.group(0)
    rendered = re.sub(r"\{\{\s*([\w.]+)\s*\}\}", sub, s.content)
    s.usage_count += 1
    await db.commit()
    return {"name": s.name, "script": rendered, "usage_count": s.usage_count}
@router.post("/ai/generate")
async def ai_generate(req: AiScriptRequest, user: User = Depends(get_current_user)):
    prompt = f"""你是资深运维脚本专家。请根据需求生成一个可直接执行的 Shell 脚本。
要求：带完整注释、参数校验、错误处理（set -euo pipefail）、dry-run 支持。
需要外部填写的变量用 {{{{变量名}}}} 占位符表示，并在脚本头部注释列出所有变量含义。
需求：{req.requirement}
"""
    draft = await chat_completion([
        {"role": "system", "content": "你是运维脚本生成助手，只输出脚本和注释，不输出多余解释。"},
        {"role": "user", "content": prompt},
    ], max_tokens=2000)
    return {"script": draft, "hint": "请管理员审阅后通过【新增模板】入库，参数列表填写 {{}} 中出现的变量名"}
