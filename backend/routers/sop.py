from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool
from database import get_db
from models import User, SopDocument
from schemas import SopChatRequest, RecordGapRequest, SopUpdateRequest
from security import get_current_user
from rag import add_sop_document, sop_answer, chunk_text
from embedding import encode
router = APIRouter()
def _can_manage(user: User, created_by: str) -> bool:
    """SOP 编辑/删除权限：管理员 或 上传者本人"""
    return user.role == "admin" or user.username == created_by
@router.get("/list")
async def list_docs(status: str = "", user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """文档级列表：按 doc_key 分组，返回分块数，不再一行一个切片"""
    stmt = (select(
                SopDocument.doc_key,
                SopDocument.title,
                SopDocument.status,
                SopDocument.created_by,
                SopDocument.reject_reason,
                func.max(SopDocument.created_at).label("created_at"),
                func.count(SopDocument.id).label("chunk_count"),
            )
            .group_by(SopDocument.doc_key, SopDocument.title, SopDocument.status,
                      SopDocument.created_by, SopDocument.reject_reason)
            .order_by(func.max(SopDocument.created_at).desc())
            .limit(300))
    if status:
        stmt = stmt.having(SopDocument.status == status)
    result = await db.execute(stmt)
    out = []
    for row in result.all():
        out.append({
            "doc_key": row.doc_key,
            "title": row.title,
            "status": row.status,
            "created_by": row.created_by,
            "reject_reason": row.reject_reason or "",
            "created_at": row.created_at.strftime("%Y-%m-%d %H:%M"),
            "chunk_count": row.chunk_count,
            "can_manage": _can_manage(user, row.created_by),   # 前端据此显隐按钮
        })
    return out
@router.get("/detail/{doc_key}")
async def get_doc(doc_key: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """查看文档原文（完整 content）"""
    r = (await db.execute(
        select(SopDocument).where(SopDocument.doc_key == doc_key).limit(1))).scalars().first()
    if not r:
        raise HTTPException(status_code=404, detail="文档不存在")
    return {"doc_key": doc_key, "title": r.title, "content": r.content,
            "status": r.status, "created_by": r.created_by,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M")}
@router.get("/download/{doc_key}")
async def download_doc(doc_key: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """下载文档原文（作为 .md 附件，支持中文文件名）"""
    from urllib.parse import quote
    from fastapi.responses import Response
    r = (await db.execute(
        select(SopDocument).where(SopDocument.doc_key == doc_key).limit(1))).scalars().first()
    if not r:
        raise HTTPException(status_code=404, detail="文档不存在")
    filename = (r.title or f"{doc_key}.md").strip() or f"{doc_key}.md"
    if not filename.lower().endswith((".md", ".txt")):
        filename += ".md"
    return Response(
        content=r.content.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )
@router.put("/update/{doc_key}")
async def update_doc(doc_key: str, req: SopUpdateRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """★ 在线编辑：删旧切片 → 重新切片+向量化 → 状态回到待审批（防止绕过审批改知识库）"""
    rows = (await db.execute(
        select(SopDocument).where(SopDocument.doc_key == doc_key))).scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail="文档不存在")
    if not _can_manage(user, rows[0].created_by):
        raise HTTPException(status_code=403, detail="仅管理员或上传者可编辑")
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="内容不能为空")
    # 1. 删旧切片
    await db.execute(delete(SopDocument).where(SopDocument.doc_key == doc_key))
    # 2. 重新切片 + 向量化 + 入库（同 doc_key，状态 pending 待重审）
    chunks = chunk_text(req.content)
    vecs = await run_in_threadpool(encode, chunks)
    for chunk, vec in zip(chunks, vecs):
        db.add(SopDocument(title=req.title, content=req.content, chunk_text=chunk,
                           embedding=vec, created_by=rows[0].created_by,
                           status="pending", doc_key=doc_key, reject_reason=""))
    await db.commit()
    return {"message": "已保存修改，重新进入待审批，管理员通过后生效", "chunks": len(chunks)}
@router.delete("/doc/{doc_key}")
async def delete_doc(doc_key: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """★ 删除文档（含所有切片）"""
    rows = (await db.execute(
        select(SopDocument).where(SopDocument.doc_key == doc_key))).scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail="文档不存在")
    if not _can_manage(user, rows[0].created_by):
        raise HTTPException(status_code=403, detail="仅管理员或上传者可删除")
    await db.execute(delete(SopDocument).where(SopDocument.doc_key == doc_key))
    await db.commit()
    return {"message": "文档已删除"}
@router.post("/upload")
async def upload(file: UploadFile = File(...), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    raw = await file.read()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件超过 10MB 限制")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = raw.decode("gbk")
        except Exception:
            raise HTTPException(status_code=400, detail="文件编码不支持，请转为 UTF-8")
    if not text.strip():
        raise HTTPException(status_code=400, detail="文件内容为空")
    count = await add_sop_document(db, file.filename, text, user.username, status="pending")
    return {"message": f"已提交，切片 {count} 块。等待管理员审批后生效。", "chunks": count}
@router.post("/chat")
async def chat(req: SopChatRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """旧入口保留（RagChat 已切到 /api/rag/chat，此处兼容）"""
    return await sop_answer(db, req.question, user.username)
@router.post("/record-gap")
async def record_gap(req: RecordGapRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from models import QaGap
    if not req.ai_answer.strip():
        raise HTTPException(status_code=400, detail="答案内容为空")
    db.add(QaGap(question=req.question, ai_draft=req.ai_answer,
                 status="pending", created_by=user.username))
    await db.commit()
    return {"message": "已提交审批，管理员通过后自动录入知识库"}
