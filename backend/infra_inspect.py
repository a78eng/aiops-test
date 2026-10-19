"""全局巡检报告：主机负载 + Docker/K8s 架构概况 + 错误日志 → LLM 综合巡检报告"""
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool
from models import DailyReport
from monitor import build_metrics_summary, get_system_snapshot, get_recent_error_logs
from llm_client import chat_completion
async def build_inspect_report(db, report_date: str) -> str:
    metrics = await build_metrics_summary()
    snapshot = await run_in_threadpool(get_system_snapshot)
    logs = await get_recent_error_logs(24, 30)
    log_text = "\n".join(logs) if logs else "（最近 24 小时无错误日志）"
    prompt = f"""你是资深运维架构师。请根据以下数据生成一份【系统全局巡检报告】（Markdown 格式）。
要求：
1. 先用一句话给系统整体负载健康度结论（健康/亚健康/需处理）
2. 分块分析：主机负载（CPU/内存/磁盘/GPU）、容器化业务（Docker 容器运行状态）、K8s 集群（如有）
3. 指出异常项（CPU>80%、内存>90%、磁盘>85%、容器非运行状态、Pod 异常、错误日志）
4. 给出 3 条以内按优先级排序的处理建议
5. 全文 500 字以内，只基于给定数据，禁止编造
【主机负载】
{metrics}
【容器与集群架构】
{snapshot}
【最近 24 小时错误日志 Top30】
{log_text}
"""
    report_text = await chat_completion([
        {"role": "system", "content": "你是运维巡检报告助手，只基于给定数据生成，禁止编造。"},
        {"role": "user", "content": prompt},
    ], max_tokens=1500)
    existing = (await db.execute(
        select(DailyReport).where(DailyReport.report_date == report_date))).scalars().first()
    if existing:
        existing.metrics_summary = metrics
        existing.log_summary = log_text[:2000]
        existing.ai_report = report_text
    else:
        db.add(DailyReport(report_date=report_date, metrics_summary=metrics,
                           log_summary=log_text[:2000], ai_report=report_text))
    await db.commit()
    return report_text
