from datetime import datetime, timedelta
from sqlalchemy import select, delete
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import SessionLocal
from models import DailyReport, MinuteBrief
from monitor import build_metrics_summary, get_recent_error_logs
from llm_client import chat_completion
# ============ 每日 AI 巡检日报（保留，每天凌晨 2 点） ============
async def generate_and_save_report(db, report_date: str) -> str:
    metrics = await build_metrics_summary()
    logs = await get_recent_error_logs(24, 50)
    log_text = "\n".join(logs) if logs else "（最近 24 小时无错误日志）"
    prompt = f"""你是一位资深运维工程师。请根据以下监控指标和错误日志，生成一份中文运维日报（Markdown 格式）。
要求：
1. 用自然语言总结系统整体健康状况（一句话结论）
2. 列出异常指标（判定标准：CPU>80%、内存>90%、磁盘>85%）
3. 归纳错误日志的类型和潜在影响
4. 给出 3 条以内可执行的处理建议
5. 篇幅控制在 400 字以内，不要编造数据
【监控指标（当前值）】
{metrics}
【最近 24 小时错误日志 Top 50】
{log_text}
"""
    report_text = await chat_completion([
        {"role": "system", "content": "你是运维日报生成助手，只基于给定数据生成报告，禁止编造。"},
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
async def scheduled_daily_report():
    async with SessionLocal() as db:
        date = datetime.now().strftime("%Y-%m-%d")
        try:
            await generate_and_save_report(db, date)
            print(f"[DailyReport] {date} 日报生成完成")
        except Exception as e:
            print(f"[DailyReport] {date} 日报生成失败: {e}")
# ============ ★ 每分钟实时简报（核心新功能） ============
async def generate_minute_brief():
    """每 60 秒：采集当前指标 + 最近 6 分钟错误日志 → LLM 生成 100 字内简短概况+建议"""
    async with SessionLocal() as db:
        try:
            # 第 1 步：采集指标（CPU/内存/磁盘/GPU）
            metrics = await build_metrics_summary()
            # 第 2 步：采集最近 6 分钟错误日志 Top10
            logs = await get_recent_error_logs(hours=0.1, limit=10)
            log_text = "\n".join(logs) if logs else "（最近 6 分钟无错误日志）"
            # 第 3 步：LLM 生成简短简报
            prompt = f"""你是运维值守助手。根据以下实时数据，用不超过100字输出当前系统概况。
格式要求：第一句给整体状态结论；如有异常指标或错误日志，点出最关键的1个；最后给1条简短建议。
没有异常就明确说"系统运行正常"。禁止编造数据。
【当前指标】
{metrics}
【最近6分钟错误日志 Top10】
{log_text}
"""
            brief = await chat_completion([
                {"role": "system", "content": "你是运维实时简报助手，输出必须简洁，100字以内。"},
                {"role": "user", "content": prompt},
            ], max_tokens=300, temperature=0.3)
            # 第 4 步：入库
            db.add(MinuteBrief(metrics_summary=metrics, log_summary=log_text[:1000], ai_brief=brief))
            # 第 5 步：只保留最近 24 小时（约1440条，控制表体积）
            await db.execute(delete(MinuteBrief).where(
                MinuteBrief.brief_time < datetime.now() - timedelta(hours=24)))
            await db.commit()
            print(f"[MinuteBrief] {datetime.now().strftime('%H:%M:%S')} 完成: {brief[:60]}")
        except Exception as e:
            print(f"[MinuteBrief] 生成失败: {e}")
scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
# ★ 每 60 秒执行一次实时简报（启动 10 秒后先跑第一次）
scheduler.add_job(generate_minute_brief, "interval", minutes=1, id="minute_brief",
                  next_run_time=datetime.now() + timedelta(seconds=10))
# 每日 2 点巡检日报
scheduler.add_job(scheduled_daily_report, "cron", hour=2, minute=0, id="daily_report")
