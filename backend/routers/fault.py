from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import User, FaultRecord
from schemas import (FaultRecordRequest, FaultSearchRequest, FaultAnalyzeRequest, FaultUpdateRequest)
from security import get_current_user
from rag import add_fault_record, search_fault, fault_analyze
router = APIRouter()
@router.post("/record")
async def record(req: FaultRecordRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """轻量化录入：只需现象，根因/方案可后补（工单流转时补充）"""
    if not req.phenomenon.strip():
        raise HTTPException(status_code=400, detail="请描述故障现象")
    r = await add_fault_record(db, req.phenomenon,
                               req.root_cause or "待AI分析",
                               req.solution or "待补充",
                               user.username)
    return {"id": r.id, "message": "录入成功，已进入工单池"}

@router.post("/search")
async def search(req: FaultSearchRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await search_fault(db, req.query, req.top_k)
@router.post("/analyze")
async def analyze(req: FaultAnalyzeRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """★智能体入口：现象+日志 → 检索历史+SOP → LLM 输出根因/步骤/风险"""
    if not req.phenomenon.strip():
        raise HTTPException(status_code=400, detail="请描述故障现象")
    return await fault_analyze(db, req.phenomenon, req.extra_logs)
@router.get("/list")
async def list_records(status: str = "", user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(FaultRecord).order_by(FaultRecord.created_at.desc()).limit(300)
    if status:
        stmt = stmt.where(FaultRecord.status == status)
    result = await db.execute(stmt)
    return [{"id": r.id, "phenomenon": r.phenomenon, "root_cause": r.root_cause, "solution": r.solution,
             "status": r.status, "handler": r.handler,
             "occurrence_count": r.occurrence_count, "created_by": r.created_by,
             "created_at": r.created_at.strftime("%Y-%m-%d %H:%M"),
             "closed_at": r.closed_at.strftime("%Y-%m-%d %H:%M") if r.closed_at else None}
            for r in result.scalars().all()]
@router.post("/{fault_id}/update")
async def update(fault_id: int, req: FaultUpdateRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """工单流转：待处理→处理中→已关闭，记录处理人"""
    r = (await db.execute(select(FaultRecord).where(FaultRecord.id == fault_id))).scalars().first()
    if not r:
        raise HTTPException(status_code=404, detail="故障记录不存在")
    if req.status is not None:
        if req.status not in ("open", "processing", "closed"):
            raise HTTPException(status_code=400, detail="状态只能为 open/processing/closed")
        r.status = req.status
        if req.status == "closed":
            r.closed_at = datetime.now()
        elif req.status == "open":
            r.closed_at = None
    if req.handler is not None:
        r.handler = req.handler
    if req.solution is not None and req.solution.strip():
        r.solution = req.solution
    await db.commit()
    return {"message": "更新成功", "status": r.status, "handler": r.handler}
@router.post("/{fault_id}/reoccur")
async def reoccur(fault_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """重复发生计数（高频故障识别）"""
    r = (await db.execute(select(FaultRecord).where(FaultRecord.id == fault_id))).scalars().first()
    if not r:
        raise HTTPException(status_code=404, detail="故障记录不存在")
    r.occurrence_count += 1
    r.status = "open"
    r.closed_at = None
    await db.commit()
    return {"id": r.id, "occurrence_count": r.occurrence_count}
