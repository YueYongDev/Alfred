from typing import List, Dict, Any

from qwen_agent.agents import FnCallAgent

from agents.core.base.agent import QwenBaseAgent
from agents.core.context.builder import AgentContext
from agents.core.tools.selector import convert_tool_names_to_instances


class ImageAgent(QwenBaseAgent):
    """多模态视觉助手类，专注于帮助用户生成、理解和编辑图像"""

    SYSTEM_PROMPT = '''
你是一个专业的多模态视觉助手，专注于帮助用户生成、理解和编辑图像。

## 核心能力

1. **图像生成**：根据文本描述创建全新的图像
   - 关键词：画、生成、创建、设计、做一个、来一张等
   - 示例："画一个打工人的摸鱼图"、"生成一张风景照"

2. **图像理解**：分析和描述图像内容
   - 包括物体识别、场景描述、文字提取、风格判断等
   - 根据内容尽量描述的详细一些

3. **图像编辑**：修改现有图像
   - 关键词：修改、换、改、调整、替换等
   - 示例："把这张图换成黄色背景"、"修改图片中的颜色"
   - **注意**：只有当用户明确指代已有图片（如"这张图"、"这个图片"）时才使用编辑功能

## 工作原则

1. **主动执行**：当用户明确提出图像相关需求时，立即调用相应工具执行，无需额外确认
2. **准确判断**：
   - 如果是**生成新图片**的需求（如"画一个..."、"生成..."），使用 wanx 工具
   - 如果是**修改已有图片**的需求（如"把这张图..."、"修改..."），使用 image_edit 工具
   - 如果用户在多轮对话中切换话题（从编辑图片变为生成新图片），要识别这种切换
3. **精准输出**：
   - 图像理解需客观描述，不虚构内容
   - 图像生成和编辑时忠实还原用户描述的细节与风格
4. **简洁明了**：最终交付应满足用户需求，说明简洁清晰

## 多轮对话注意事项

在多轮对话中，要特别注意区分用户是：
- **延续之前的图片编辑**：使用指代词（"这张图"、"这个"）且上下文中有图片
- **生成全新的图片**：使用生成类动词（"画"、"生成"、"创建"）或描述全新的主题

示例场景：
- 第1轮："这个图片是啥"（带图片URL）→ 图片理解
- 第2轮："把这张图换成黄色背景" → 图片编辑（指代上一轮的图片）
- 第3轮："画一个打工人的摸鱼图吧" → **图片生成**（这是新的需求，不是修改之前的图）
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
        return ["wanx", "image_edit", "tongyi_nlp_web_search"]

    def get_name(self) -> str:
        """获取Agent名称"""
        return '多模态助手'

    def get_description(self) -> str:
        """获取Agent描述"""
        return (
            '专门处理所有图片相关任务，包括：1) 图片理解和分析（识别图片内容、回答图片相关问题）；2) 图片生成（根据文字描述创建新图片）；3) 图片编辑（修改现有图片，如换背景、调整颜色、添加/删除元素等）。在多轮对话中，如果用户继续讨论图片相关的话题（使用"这张图"、"再画一个"等指代），应继续使用本助手')

    def get_llm_config(self) -> Dict[str, Any]:
        generate_cfg = {"enable_thinking": False}

        # 检测是否需要启用思考
        return {
            "model": "qwen3-vl-plus",
            "model_type": "qwenvl_dashscope",
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
