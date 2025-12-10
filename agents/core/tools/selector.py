import logging
from inspect import signature
from typing import List, Optional

from agents.core.context.builder import AgentContext
from tools.core.base import QwenAgentBaseTool
from tools.search.duckduckgo import DuckDuckGoSearch
from tools.search.google import GoogleWebSearch

logger = logging.getLogger(__name__)

# 工具实例列表
_all_qwen_tools = [
    DuckDuckGoSearch(),
    GoogleWebSearch(),
]
_tool_map_by_name = {tool.name: tool for tool in _all_qwen_tools}


def get_qwen_tool_by_name(name: str) -> Optional[QwenAgentBaseTool]:
    """根据工具名称获取工具实例"""
    return _tool_map_by_name.get(name)


def get_all_qwen_tools() -> List[QwenAgentBaseTool]:
    """获取所有工具实例"""
    return _all_qwen_tools


def convert_tool_names_to_instances(selected_tool_names: List[str], context: AgentContext = None) -> List[
    QwenAgentBaseTool]:
    """
    将工具名称转换为工具实例

    Args:
        selected_tool_names: 工具名称列表
        context: 上下文信息

    Returns:
        工具实例列表
    """
    selected_tools = []
    for tool_name in selected_tool_names:
        tool_instance = get_qwen_tool_by_name(tool_name)
        if tool_instance:
            tool_class = tool_instance.__class__
            try:
                init_params = signature(tool_class.__init__).parameters
                if "context" in init_params and len(init_params) > 1:
                    tool_instance = tool_class(context=context)
                else:
                    tool_instance = tool_class()
                selected_tools.append(tool_instance)
            except TypeError as exc:
                logger.error(exc, f"Failed to initialize tool {tool_name}")
                continue
        else:
            logger.debug(f"Warning: Tool {tool_name} not found in tool collection")

    # OneLog.debug(f"Selected Tools: {[getattr(tool, 'name', str(tool)) for tool in selected_tools]}")
    return selected_tools
