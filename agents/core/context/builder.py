from typing import List, Optional, Dict, Any

from pydantic import BaseModel, field_validator

from agents.core.messaging.chat_request import ChatRequest
from agents.core.messaging.request_helper import extract_files_from_request, extract_images_from_request


class AgentContext(BaseModel):
    """智能体上下文对象"""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    security_level: Optional[str] = None
    terminal_type: Optional[str] = None
    os_group: Optional[str] = None
    files: List[str] = []
    file_ids: List[str] = []
    images: List = []
    effective_model: Optional[str] = None

    @field_validator('user_id', 'session_id', 'security_level', 'terminal_type', 'os_group', mode='before')
    @classmethod
    def convert_to_string(cls, v):
        """将字段值转换为字符串，如果不为 None"""
        if v is not None and not isinstance(v, str):
            return str(v)
        return v


class QwenAgentContextBuilder:
    """Qwen智能体上下文构建器"""

    @staticmethod
    def buildContext(request: ChatRequest, qa_messages: List[Dict[str, Any]]) -> AgentContext:
        """构建智能体上下文
        """
        # 从 file_list 中提取 URL 列表

        # 2) 组装服务端上下文
        file_list = extract_files_from_request(request)
        image_list = extract_images_from_request(request)

        extracted_file_urls = []
        if file_list and isinstance(file_list, list) and len(file_list) > 0 and isinstance(file_list[0], dict):
            extracted_file_urls = [f["file"] for f in file_list if "file" in f]
        elif file_list:
            extracted_file_urls = file_list

        # 组装服务端上下文（从 header.systemParams 获取）
        system_params = {}
        if request.header and request.header.systemParams:
            system_params = {
                "userId": request.header.systemParams.userId,
                "sessionId": request.header.sessionId,
                "securityLevel": getattr(request.header.systemParams, 'securityLevel', None),
                "terminalType": getattr(request.header.systemParams, 'terminalType', None),
                "osGroup": getattr(request.header.systemParams, 'osGroup', None),
            }
        # 向后兼容旧格式
        elif request.session:
            system_params = {
                "userId": request.session.userId,
                "sessionId": request.session.sessionId,
            }
        ctx = AgentContext(
            effective_model="qwen3-max",
            user_id=system_params.get("userId"),
            session_id=system_params.get("sessionId"),
            security_level=system_params.get("securityLevel"),
            terminal_type=system_params.get("terminalType"),
            os_group=system_params.get("osGroup"),
            files=extracted_file_urls,
            file_ids=[f.get("file_id") for f in file_list if isinstance(f, dict) and f.get("file_id")],
            images=image_list
        )
        return ctx
