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
    enable_thinking: bool = False
    enable_search: Optional[bool] = None

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

        # 获取并转换enable_thinking参数为布尔值
        deep_think_param = (request.parameters or {}).get("custom", {}).get("deep_think")
        if deep_think_param is not None:
            if isinstance(deep_think_param, bool):
                enable_thinking = deep_think_param
            elif isinstance(deep_think_param, str):
                enable_thinking = deep_think_param.lower() in ('true', '1', 'yes', 'on')
            elif isinstance(deep_think_param, (int, float)):
                enable_thinking = bool(deep_think_param)
            else:
                # 对于其他类型，默认为False
                enable_thinking = False
        else:
            # 当deep_think_param为None时，设置默认值为False
            enable_thinking = False

        # enable_search_param = (request.parameters or {}).get("enable_search", True)
        depth_search_param = (request.parameters or {}).get("custom", {}).get("depth_search")
        force_unsearch_param = (request.parameters or {}).get("custom", {}).get("force_unsearch")

        enable_search = None
        if force_unsearch_param is not None and force_unsearch_param:
            enable_search = False
        if depth_search_param is not None and depth_search_param:
            enable_search = True

        # 组装服务端上下文（不要放进 system 消息）
        system_params = (request.parameters or {}).get("systemParams", {}) or {}
        ctx = AgentContext(
            effective_model="qwen3-max",
            user_id=system_params.get("userId"),
            session_id=system_params.get("sessionId"),
            security_level=system_params.get("securityLevel"),
            terminal_type=system_params.get("terminalType"),
            os_group=system_params.get("osGroup"),
            files=extracted_file_urls,
            file_ids=[f.get("file_id") for f in file_list if isinstance(f, dict) and f.get("file_id")],
            images=image_list,
            enable_thinking=enable_thinking,
            enable_search=enable_search
        )
        return ctx
