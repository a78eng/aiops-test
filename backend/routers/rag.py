from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import User
from schemas import SopChatRequest
from security import get_current_user
from rag import rag_unified_answer

router = APIRouter()


@router.post("/chat")
async def chat(req: SopChatRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """统一 RAG 问答：检索已审批 SOP + 历史故障案例；未命中由 AI 直答"""
    return await rag_unified_answer(db, req.question, user.username)
