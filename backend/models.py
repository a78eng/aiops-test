from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from pgvector.sqlalchemy import Vector
from database import Base
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(64), default="")
    role = Column(String(16), default="member")
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.now)
    last_login_at = Column(DateTime, nullable=True)
class SopDocument(Base):
    __tablename__ = "sop_documents"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(Vector(1024), nullable=False)
    doc_key = Column(String(32), default="", index=True)   # ★ 文档分组键：同文档所有切片共享
    status = Column(String(16), default="pending")
    reject_reason = Column(String(255), default="")
    created_by = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
class QaGap(Base):
    __tablename__ = "qa_gaps"
    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    ai_draft = Column(Text, default="")
    status = Column(String(16), default="pending")
    approved_by = Column(String(64), default="")
    created_by = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    resolved_at = Column(DateTime, nullable=True)
class FaultRecord(Base):
    __tablename__ = "fault_records"
    id = Column(Integer, primary_key=True, index=True)
    phenomenon = Column(Text, nullable=False)
    root_cause = Column(Text, default="")
    solution = Column(Text, nullable=False)
    embedding = Column(Vector(1024), nullable=False)
    status = Column(String(16), default="open")
    handler = Column(String(64), default="")
    closed_at = Column(DateTime, nullable=True)
    created_by = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    occurrence_count = Column(Integer, default=1)
class ScriptTemplate(Base):
    __tablename__ = "script_templates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    category = Column(String(64), default="通用")
    description = Column(Text, default="")
    content = Column(Text, nullable=False)
    params = Column(Text, default="[]")
    usage_count = Column(Integer, default=0)
    created_by = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
class DailyReport(Base):
    __tablename__ = "daily_reports"
    id = Column(Integer, primary_key=True, index=True)
    report_date = Column(String(10), unique=True, index=True, nullable=False)
    metrics_summary = Column(Text, default="")
    log_summary = Column(Text, default="")
    ai_report = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)
class MinuteBrief(Base):
    __tablename__ = "minute_briefs"
    id = Column(Integer, primary_key=True, index=True)
    brief_time = Column(DateTime, default=datetime.now, index=True)
    metrics_summary = Column(Text, default="")
    log_summary = Column(Text, default="")
    ai_brief = Column(Text, default="")
