from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool
from models import SopDocument, FaultRecord
from embedding import encode
from llm_client import chat_completion
from config import settings
# ============ 文本切片 ============
def chunk_text(text: str) -> list:
    size, overlap = settings.CHUNK_SIZE, settings.CHUNK_OVERLAP
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks or [text]
# ============ SOP 文档入库（默认待审批） ============
async def add_sop_document(db: AsyncSession, title: str, content: str, username: str, status: str = "pending", doc_key: str = "") -> int:
    import uuid as _uuid
    doc_key = doc_key or ("doc_" + _uuid.uuid4().hex[:16])
    chunks = chunk_text(content)
    vecs = await run_in_threadpool(encode, chunks)
    for chunk, vec in zip(chunks, vecs):
        db.add(SopDocument(title=title, content=content, chunk_text=chunk,
                           embedding=vec, created_by=username, status=status, doc_key=doc_key))
    await db.commit()
    return len(chunks)
# ============ SOP 语义检索（只查已审批） ============
async def sop_search(db: AsyncSession, question: str, top_k: int = 5):
    vec = await run_in_threadpool(encode, question)
    stmt = (select(SopDocument)
            .where(SopDocument.status == "approved")
            .order_by(SopDocument.embedding.cosine_distance(vec))
            .limit(top_k))
    result = await db.execute(stmt)
    return result.scalars().all()
# ============ SOP 语义检索（带相似度分数） ============
async def sop_search_scored(db: AsyncSession, question: str, top_k: int = 5):
    """返回 [(doc, similarity)]，供需要相似度阈值判断“是否命中”的场景使用"""
    vec = await run_in_threadpool(encode, question)
    stmt = (select(SopDocument, SopDocument.embedding.cosine_distance(vec).label("dist"))
            .where(SopDocument.status == "approved")
            .order_by("dist")
            .limit(top_k))
    result = await db.execute(stmt)
    return [(doc, round(max(0.0, 1 - float(dist)), 4)) for doc, dist in result.all()]
# ============ SOP 单库问答（供 /api/sop/chat 使用，未命中返回 AI 直答 + can_record） ============
async def sop_answer(db: AsyncSession, question: str, username: str) -> dict:
    docs = await sop_search(db, question)
    if docs:
        context = "\n\n".join(f"【文档：{d.title}】\n{d.chunk_text}" for d in docs)
        prompt = f"""你是资深运维专家。请严格依据以下知识库内容回答用户问题。
如果知识库中没有相关信息，请明确回答"知识库中暂无相关内容"。
知识库内容：
{context}
用户问题：{question}
"""
        answer = await chat_completion([
            {"role": "system", "content": "你是基于团队 SOP 知识库的运维问答助手，回答必须可溯源。"},
            {"role": "user", "content": prompt},
        ])
        return {"answer": answer, "sources": [{"id": d.id, "title": d.title} for d in docs], "can_record": False}
    ai_answer = await chat_completion([
        {"role": "system", "content": "你是资深运维专家。用户的问题在团队知识库中未检索到，请直接给出可操作的解决办法。要求：步骤清晰可执行、必要处给出命令、不确定的地方明确说明、不要编造。"},
        {"role": "user", "content": question},
    ], max_tokens=1024)
    return {"answer": ai_answer, "sources": [], "can_record": True, "record_question": question}
# ============ 故障录入 ============
async def add_fault_record(db: AsyncSession, phenomenon: str, root_cause: str, solution: str, username: str):
    text = f"故障现象：{phenomenon}\n根因分析：{root_cause or '未记录'}\n处理方案：{solution}"
    vec = await run_in_threadpool(encode, text)
    record = FaultRecord(phenomenon=phenomenon, root_cause=root_cause, solution=solution,
                         embedding=vec, created_by=username, status="open")
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record
# ============ 故障语义检索（返回相似度/发生次数） ============
async def search_fault(db: AsyncSession, query: str, top_k: int = 3) -> list:
    vec = await run_in_threadpool(encode, query)
    stmt = (select(FaultRecord, FaultRecord.embedding.cosine_distance(vec).label("dist"))
            .order_by("dist")
            .limit(top_k))
    result = await db.execute(stmt)
    items = []
    for r, dist in result.all():
        items.append({
            "id": r.id,
            "phenomenon": r.phenomenon,
            "root_cause": r.root_cause,
            "solution": r.solution,
            "status": r.status,
            "handler": r.handler,
            "occurrence_count": r.occurrence_count,
            "similarity": round(max(0.0, 1 - float(dist)), 4),
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M"),
        })
    return items
# ============ 故障智能辅助分析 ============
async def fault_analyze(db: AsyncSession, phenomenon: str, extra_logs: str = "") -> dict:
    related_faults = await search_fault(db, phenomenon, 3)
    sops = await sop_search(db, phenomenon, 3)
    fault_ctx = "\n".join(
        f"- 案例{i+1}（历史发生{f['occurrence_count']}次）：现象：{f['phenomenon']}；根因：{f['root_cause']}；方案：{f['solution']}"
        for i, f in enumerate(related_faults)) or "（无相似历史案例）"
    sop_ctx = "\n".join(f"- {s.title}：{s.chunk_text[:300]}" for s in sops) or "（无相关知识库条目）"
    prompt = f"""你是资深运维故障分析专家。请根据以下信息进行辅助分析，输出 Markdown 格式：
## 可能根因（按概率从高到低，最多3个）
1. ...
## 建议处置步骤（可执行、带命令）
1. ...
## 风险提示
- ...
【故障现象】
{phenomenon}
【补充日志/上下文】
{extra_logs or "（未提供）"}
【历史相似故障案例】
{fault_ctx}
【团队知识库相关条目】
{sop_ctx}
"""
    analysis = await chat_completion([
        {"role": "system", "content": "你是故障分析助手。基于给定资料分析，不确定的地方明确说明，禁止编造。"},
        {"role": "user", "content": prompt},
    ], max_tokens=1500)
    return {
        "analysis": analysis,
        "related_faults": related_faults,
        "related_sops": [{"id": s.id, "title": s.title, "chunk_text": s.chunk_text[:300]} for s in sops],
    }
# ============ 统一 RAG 问答（SOP + 故障案例联合检索，供 /api/rag/chat 使用） ============
async def rag_unified_answer(db: AsyncSession, question: str, username: str) -> dict:
    sops = await sop_search_scored(db, question, 3)   # [(doc, similarity)]
    faults = await search_fault(db, question, 3)
    # 相似度阈值：低于该值视为“未命中”，触发知识空白录入（can_record）
    THRESHOLD = 0.6
    sops = [(d, s) for d, s in sops if s >= THRESHOLD]
    faults = [f for f in faults if f["similarity"] >= THRESHOLD]
    if sops or faults:
        sop_ctx = "\n\n".join(f"【SOP文档：{d.title}】\n{d.chunk_text}" for d, _ in sops) or "（无）"
        fault_ctx = "\n".join(
            f"- 案例（历史发生 {f['occurrence_count']} 次，相似度 {f['similarity']}）：现象：{f['phenomenon']}；根因：{f['root_cause']}；方案：{f['solution']}"
            for f in faults) or "（无）"
        prompt = f"""你是资深运维专家。请依据以下团队知识库内容回答用户问题。
知识库包含 SOP 文档和历史故障案例，回答时可引用并说明来源。
【SOP 文档】
{sop_ctx}
【历史故障案例】
{fault_ctx}
用户问题：{question}
"""
        answer = await chat_completion([
            {"role": "system", "content": "你是团队知识库问答助手，回答必须基于给定资料，禁止编造。"},
            {"role": "user", "content": prompt},
        ])
        sources = ([{"type": "sop", "id": d.id, "title": d.title} for d, _ in sops] +
                   [{"type": "fault", "id": f["id"], "title": "案例：" + f["phenomenon"][:40]} for f in faults])
        return {"answer": answer, "sources": sources, "can_record": False}
    ai_answer = await chat_completion([
        {"role": "system", "content": "你是资深运维专家。用户的问题在团队知识库中未检索到，请直接给出可操作的解决办法。步骤清晰、可执行、不编造。"},
        {"role": "user", "content": question},
    ], max_tokens=1024)
    return {"answer": ai_answer, "sources": [], "can_record": True, "record_question": question}
