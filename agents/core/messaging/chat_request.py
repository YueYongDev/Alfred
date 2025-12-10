from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class Message(BaseModel):
    role: str
    content: Optional[Any] = None
    msgId: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

class SystemParams(BaseModel):
    userId: Optional[str] = None
    userIp: Optional[str] = None
    utdId: Optional[str] = None

class Header(BaseModel):
    reqId: str
    sessionId: str
    parentMsgId: Optional[str] = None
    systemParams: Optional[SystemParams] = None

class Body(BaseModel):
    stream: Optional[bool] = True
    messages: List[Message]

class Parameters(BaseModel):
    agentCode: Optional[str] = None
    resultFormat: Optional[str] = "message"
    enableSearch: Optional[bool] = True
    enableThinking: Optional[bool] = True
    # 保留原有的其他参数
    extra: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ChatRequest(BaseModel):
    model: Optional[str] = None
    parameters: Optional[Parameters] = None
    header: Header
    body: Body

    # 保留旧字段以兼容现有代码
    @property
    def session(self):
        """兼容旧代码的 session 属性"""
        from .chat_request import Session
        return Session(
            reqId=self.header.reqId,
            sessionId=self.header.sessionId,
            userId=self.header.systemParams.userId if self.header.systemParams else "user"
        )

    @property
    def data(self):
        """兼容旧代码的 data 属性"""
        from .chat_request import Data
        return Data(
            stream=self.body.stream,
            messages=self.body.messages
        )

# 保留旧类定义以兼容现有代码
class Session(BaseModel):
    reqId: str
    sessionId: str
    userId: str

class Data(BaseModel):
    stream: Optional[bool] = True
    messages: List[Message]