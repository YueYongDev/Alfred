from typing import Optional, List, Dict, Any

from pydantic import BaseModel, ConfigDict, Field


class Message(BaseModel):
    role: str
    content: Optional[Any] = None
    name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="ignore")


class ChatRequest(BaseModel):
    model: Optional[str] = None
    stream: Optional[bool] = True
    messages: List[Message] = Field(default_factory=list)
    req_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="ignore")
