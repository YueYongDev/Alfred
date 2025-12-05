from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class Message(BaseModel):
    role: str
    content: Optional[Any] = None
    msgId: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

class Session(BaseModel):
    reqId: str
    sessionId: str
    userId: str

class Data(BaseModel):
    stream: Optional[bool] = True
    messages: List[Message]

class ChatRequest(BaseModel):
    model: Optional[str] = None
    task: Optional[str] = None
    session: Optional[Session] = None
    data: Data
    parameters: Optional[Dict[str, Any]] = None