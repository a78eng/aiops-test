from fastapi import APIRouter, Depends
from models import User
from security import get_current_user
from monitor import get_current_metrics, get_metric_range

router = APIRouter()

@router.get("/metrics")
async def metrics(user: User = Depends(get_current_user)):
    """仪表盘 4 张指标卡片（CPU/内存/磁盘/GPU），前端每 30 秒轮询一次"""
    return await get_current_metrics()

@router.get("/range")
async def metric_range(hours: int = 1, user: User = Depends(get_current_user)):
    """ECharts 趋势图数据：{cpu:[{time,value}], mem:[...]}"""
    return await get_metric_range(hours)
# ============ ★ 全局巡检 ============
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool
from database import get_db
from monitor import get_docker_summary, get_k8s_summary
from schemas import ReportGenerateRequest
from infra_inspect import build_inspect_report
@router.get("/inspect")
async def system_inspect(user: User = Depends(get_current_user)):
    """全局巡检原始数据：主机指标 + Docker 容器列表 + K8s 概况（前端展示用）"""
    metrics = await get_current_metrics()
    docker = await run_in_threadpool(get_docker_summary)
    k8s = await run_in_threadpool(get_k8s_summary)
    return {"metrics": metrics, "docker": docker, "k8s": k8s}
@router.post("/inspect-report")
async def generate_inspect_report(req: ReportGenerateRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """触发 AI 全局巡检报告（采集 → LLM 分析 → 入库），P40 上约 1-3 分钟"""
    from datetime import datetime as _dt
    date = req.date or _dt.now().strftime("%Y-%m-%d")
    report_text = await build_inspect_report(db, date)
    return {"message": "巡检报告生成完成", "date": date, "report": report_text}

