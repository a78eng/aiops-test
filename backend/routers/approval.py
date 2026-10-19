from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool
from database import get_db
from models import User, SopDocument, QaGap
from schemas import ApproveRequest
from security import get_current_admin
from rag import chunk_text
from embedding import encode
router = APIRouter()
@router.get("/docs")
async def pending_docs(status: str = "pending", admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SopDocument).where(SopDocument.status == status).order_by(SopDocument.created_at.desc()))
    return [{"id": d.id, "title": d.title, "content": d.content[:2000],
             "created_by": d.created_by, "reject_reason": d.reject_reason,
             "created_at": d.created_at.strftime("%Y-%m-%d %H:%M")}
            for d in result.scalars().all()]
@router.post("/docs/{doc_id}")
async def review_doc(doc_id: int, req: ApproveRequest, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    doc = (await db.execute(select(SopDocument).where(SopDocument.id == doc_id))).scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    if req.action == "approve":
        doc.status = "approved"
    elif req.action == "reject":
        doc.status = "rejected"
        doc.reject_reason = req.reason or "未说明原因"
    else:
        raise HTTPException(status_code=400, detail="action 只能为 approve/reject")
    await db.commit()
    return {"message": "已通过" if req.action == "approve" else "已驳回", "id": doc.id}
@router.get("/gaps")
async def list_gaps(status: str = "pending", admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(QaGap).where(QaGap.status == status).order_by(QaGap.created_at.desc()))
    return [{"id": g.id, "question": g.question, "ai_draft": g.ai_draft[:3000],
             "created_by": g.created_by,
             "created_at": g.created_at.strftime("%Y-%m-%d %H:%M")}
            for g in result.scalars().all()]
@router.post("/gaps/{gap_id}")
async def review_gap(gap_id: int, req: ApproveRequest, admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    """空白录用：通过 → AI草稿自动向量化录入知识库；驳回 → 标记 rejected"""
    gap = (await db.execute(select(QaGap).where(QaGap.id == gap_id))).scalars().first()
    if not gap:
        raise HTTPException(status_code=404, detail="记录不存在")
    if req.action == "approve":
        # 自动录用：AI 草稿切片 + 向量化 + 入库（status=approved，直接可检索）
        import uuid as _uuid
        content = gap.ai_draft or gap.question
        doc_key = "doc_" + _uuid.uuid4().hex[:16]   # ★ 必须生成 doc_key，否则前端无法查看/编辑/下载
        chunks = chunk_text(content)
        vecs = await run_in_threadpool(encode, chunks)
        for chunk, vec in zip(chunks, vecs):
            db.add(SopDocument(title=f"AI补录：{gap.question[:40]}", content=content,
                               chunk_text=chunk, embedding=vec, doc_key=doc_key,
                               status="approved", created_by=admin.username))
        gap.status = "approved"
        gap.approved_by = admin.username
        gap.resolved_at = datetime.now()
        await db.commit()
        return {"message": "已录用并自动入库，可被检索", "chunks": len(chunks)}
    elif req.action == "reject":
        gap.status = "rejected"
        gap.resolved_at = datetime.now()
        await db.commit()
        return {"message": "已驳回"}
    raise HTTPException(status_code=400, detail="action 只能为 approve/reject")
