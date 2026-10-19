from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import User, DailyReport, MinuteBrief
from schemas import ReportGenerateRequest
from security import get_current_user
from scheduler import generate_and_save_report
router = APIRouter()
# ============ ★ 每分钟实时简报 ============
@router.get("/minute-brief/latest")
async def minute_brief_latest(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """前端 30 秒轮询一次：取最新一条简报"""
    r = (await db.execute(select(MinuteBrief).order_by(MinuteBrief.id.desc()).limit(1))).scalars().first()
    if not r:
        return {"brief": None, "message": "暂无简报，系统每分钟自动生成，请稍候"}
    return {"brief": {
        "time": r.brief_time.strftime("%Y-%m-%d %H:%M:%S"),
        "ai_brief": r.ai_brief,
        "metrics": r.metrics_summary,
        "logs": r.log_summary,
    }}
@router.get("/minute-brief/history")
async def minute_brief_history(limit: int = 30, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """历史简报列表（供展开查看）"""
    rows = (await db.execute(
        select(MinuteBrief).order_by(MinuteBrief.id.desc()).limit(min(limit, 100)))).scalars().all()
    return [{"time": r.brief_time.strftime("%H:%M:%S"), "ai_brief": r.ai_brief} for r in rows]
# ============ 每日巡检日报（保留） ============
@router.get("/detail")
async def detail(date: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    r = (await db.execute(select(DailyReport).where(DailyReport.report_date == date))).scalars().first()
    if not r:
        return {"report": None}
    return {"report": {
        "date": r.report_date,
        "ai_report": r.ai_report,
        "metrics_summary": r.metrics_summary,
        "log_summary": r.log_summary,
        "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    }}
@router.post("/generate")
async def generate(req: ReportGenerateRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    date = req.date or datetime.now().strftime("%Y-%m-%d")
    report_text = await generate_and_save_report(db, date)
    return {"message": "生成完成", "date": date, "report": report_text}
@router.get("/latest")
async def latest(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    r = (await db.execute(select(DailyReport).order_by(DailyReport.report_date.desc()).limit(1))).scalars().first()
    if not r:
        return {"report": None}
    return {"report": {"date": r.report_date, "ai_report": r.ai_report}}
