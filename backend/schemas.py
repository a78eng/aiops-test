from typing import Optional
from pydantic import BaseModel
class LoginRequest(BaseModel):
    username: str
    password: str
class SopChatRequest(BaseModel):
    question: str
class RecordGapRequest(BaseModel):
    """用户主动选择把 AI 答案录入知识库"""
    question: str
    ai_answer: str
class FaultRecordRequest(BaseModel):
    phenomenon: str
    root_cause: Optional[str] = ""
    solution: Optional[str] = ""          # 改为可选：录入时只需现象，方案可后补
class FaultSearchRequest(BaseModel):
    query: str
    top_k: int = 3
class FaultAnalyzeRequest(BaseModel):
    phenomenon: str
    extra_logs: str = ""
class FaultUpdateRequest(BaseModel):
    status: Optional[str] = None
    handler: Optional[str] = None
    solution: Optional[str] = None
class ReportGenerateRequest(BaseModel):
    date: Optional[str] = None
class UserCreateRequest(BaseModel):
    username: str
    password: str
    display_name: str = ""
    role: str = "member"
class ResetPasswordRequest(BaseModel):
    new_password: str
class ApproveRequest(BaseModel):
    action: str = "approve"
    reason: str = ""
class ScriptCreateRequest(BaseModel):
    name: str
    category: str = "通用"
    description: str = ""
    content: str
    params: list = []
class ScriptRenderRequest(BaseModel):
    params: dict = {}
class AiScriptRequest(BaseModel):
    requirement: str
class SopUpdateRequest(BaseModel):
    """SOP 在线编辑"""
    title: str
    content: str
