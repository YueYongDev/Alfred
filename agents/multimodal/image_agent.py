from typing import List, Dict, Any

from qwen_agent.agents import FnCallAgent

from agents.core.base.agent import QwenBaseAgent
from agents.core.context.builder import AgentContext
from agents.core.tools.selector import convert_tool_names_to_instances
from server import config


class ImageAgent(QwenBaseAgent):
    """多模态视觉助手类，专注于帮助用户生成、理解和编辑图像"""

    SYSTEM_PROMPT = '''
你是多模态视觉助手，负责图像生成、理解与编辑。
生成新图使用 wanx；编辑已有图使用 image_edit；理解图像要客观描述，不虚构。
仅当用户明确指代已有图片时才执行编辑；多轮对话注意“继续编辑”与“全新生成”的切换。
'''

    def __init__(self, context: AgentContext = None):
        """
        初始化多模态视觉助手

        Args:
            context: Agent上下文对象
        """
        super().__init__(context)
        self.context = context

    def get_tools(self) -> List[str]:
        """获取工具列表"""
        return []

    def get_name(self) -> str:
        """获取Agent名称"""
        return '多模态助手'

    def get_description(self) -> str:
        """获取Agent描述"""
        return (
            '专门处理所有图片相关任务，包括：1) 图片理解和分析（识别图片内容、回答图片相关问题）；2) 图片生成（根据文字描述创建新图片）；3) 图片编辑（修改现有图片，如换背景、调整颜色、添加/删除元素等）。在多轮对话中，如果用户继续讨论图片相关的话题（使用"这张图"、"再画一个"等指代），应继续使用本助手')

    def get_llm_config(self) -> Dict[str, Any]:
        generate_cfg = {}

        return {
            "model": config.LLM_VL_MODEL,
            "model_type": config.LLM_PROVIDER,
            "model_server": config.LLM_BASE_URL,
            "api_key": config.LLM_API_KEY,
            "generate_cfg": generate_cfg
        }

    def create_agent(self) -> FnCallAgent:
        """
        创建并返回FnCallAgent实例

        Returns:
            FnCallAgent: 配置好的多模态视觉助手实例
        """
        return FnCallAgent(
            system_message=self.SYSTEM_PROMPT,
            llm=self.get_llm_config(),
            function_list=convert_tool_names_to_instances(self.get_tools(), self.context),
            name=self.get_name(),
            description=self.get_description()
        )
