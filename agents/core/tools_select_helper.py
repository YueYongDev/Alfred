from typing import List

from agents.core.qwen_agent_context_builder import AgentContext
from agents.core.qwen_base_tool import QwenBaseTool
from server.app import logger

# 工具实例列表
_all_qwen_tools = [
]
_tool_map_by_name = {tool.name: tool for tool in _all_qwen_tools}


def get_qwen_tool_by_name(name: str) -> QwenBaseTool:
    """根据工具名称获取工具实例"""
    return _tool_map_by_name.get(name)


def get_all_qwen_tools() -> List[QwenBaseTool]:
    """获取所有工具实例"""
    return _all_qwen_tools


def convert_tool_names_to_instances(selected_tool_names: List[str], context: AgentContext = None) -> List[QwenBaseTool]:
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
            # 创建带上下文的工具实例
            tool_class = tool_instance.__class__
            tool_instance = tool_class(context=context)
            selected_tools.append(tool_instance)
        else:
            logger.debug(f"Warning: Tool {tool_name} not found in tool collection")

    # OneLog.debug(f"Selected Tools: {[getattr(tool, 'name', str(tool)) for tool in selected_tools]}")
    return selected_tools
