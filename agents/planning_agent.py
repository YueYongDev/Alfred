from typing import Dict, List, Any

from qwen_agent import Agent as QwenAgent
from qwen_agent.agents import FnCallAgent

from agents.core.qwen_agent_context_builder import AgentContext
from agents.core.qwen_base_agent import QwenBaseAgent
from tools.agent_call_tool import AgentCallTool


class PlanningAgent(QwenBaseAgent):
    """总协调助手类，负责根据用户需求，合理调用不同的子Agent完成复杂任务"""

    SYSTEM_PROMPT = """
你的名字是千问，你是一个「总协调助手」（Planning）。
系统只会在用户需求**比较复杂**、需要拆解为多个步骤、并可能同时用到多个子Agent时才会把请求交给你。

你可以使用工具 call_sub_agent 来调用以下子Agent（target 参数必须与下面名称完全一致）：
- 基础对话助手：适合一般问答、代码、数学、逻辑推理等通用文本任务
- 多文件智能助手：适合阅读 / 检索 / 总结文档、网页等
- 多模态助手：适合生成图片、理解图片、编辑图片

【你的工作方式】

1. 先理解用户的整体目标，判断这是一个需要多步骤解决的复杂任务，
   再把任务拆分成若干清晰的子任务（子目标）。
2. 对每个子任务，选择合适的 target，并调用 call_sub_agent：
   - 当需要理解 / 总结 / 结构化文档时，调用 target = "多文件智能助手"
   - 当需要生成图片（包括思维导图、配图）时，调用 target = "多模态助手"
   - 当是一般纯文本子任务时，可以直接调用 target = "基础对话助手"
3. 你可以多次调用 call_sub_agent，形成一个「工作流」：
   - 例如：先用 多文件智能助手 提取文档大纲，
     再把这个大纲作为 extra_context，调用 多模态助手 生成思维导图图片。
4. 工具调用返回的结果会出现在对话上下文中，你需要阅读这些结果，
   再决定下一步是否继续调用其他子Agent，最后给出一个清晰的综合回答。
5. 如果你发现当前用户需求其实是一个非常简单、可以一次性回答的问题，
   不要过度规划，直接使用「基础对话助手」完成回答即可，无需拆分过多子任务。
6. 如果你判断所有子Agent和现有工具都无法完成用户的目标，
   可以通过「基础对话助手」进行兜底回答，向用户解释当前系统能力边界，并给出替代建议。

特别说明：
- 当用户说「根据这篇文章画思维导图/脑图」时，典型步骤是：
  1）调用 多文件智能助手，要求它输出适合画思维导图的 JSON 大纲；
  2）再调用 多模态助手，要求它根据该 JSON 生成一张思维导图风格的图片；
  3）最后告诉用户图片信息，并简单说明结构。
- 当用户提出新的、你没见过的工作流需求时，你可以自行设计合理的步骤，
  通过合适地调用子Agent来完成任务。
"""

    def __init__(self, bot_basic_chat: QwenAgent, bot_doc: QwenAgent, bot_image: QwenAgent,
                 context: AgentContext = None):
        """
        初始化总协调助手

        Args:
            bot_basic_chat: 基础对话助手
            bot_doc: 多文件智能助手
            bot_image: 多模态助手
            context: Agent上下文对象
        """
        # 保存子Agent引用
        self.bot_basic_chat = bot_basic_chat
        self.bot_doc = bot_doc
        self.bot_image = bot_image

        # 调用父类构造函数
        super().__init__(context)

    def get_tools(self) -> List[str]:
        """获取工具列表 - PlanningAgent使用特殊的AgentCallTool"""
        return ["call_sub_agent"]  # 返回工具名称用于日志记录

    def get_name(self) -> str:
        """获取Agent名称"""
        return "总协调助手"

    def get_description(self) -> str:
        """获取Agent描述"""
        return (
            "用于处理明显复杂、需要拆解为多步并协调多个子Agent的任务。"
            "例如：根据文档生成思维导图、读文章后生成配图、先分析再绘图等多阶段工作流。"
        )

    def get_llm_config(self) -> Dict[str, Any]:
        """获取LLM配置"""
        return {"model": "qwen3-max"}

    def create_agent(self) -> FnCallAgent:
        """
        重写创建Agent方法，处理特殊的AgentCallTool

        Returns:
            FnCallAgent: 配置好的总协调助手实例
        """
        # 收集子Agent，key 用它们的 name
        sub_agents: Dict[str, QwenAgent] = {
            self.bot_basic_chat.name: self.bot_basic_chat,
            self.bot_doc.name: self.bot_doc,
            self.bot_image.name: self.bot_image,
        }

        # 创建AgentCallTool实例
        agent_call_tool = AgentCallTool(sub_agents)

        # 记录创建日志（调用父类的日志方法）
        llm_config = self.get_llm_config()
        self.log_agent_response(f"Creating {self.__class__.__name__} with sub-agents: {list(sub_agents.keys())}")

        return FnCallAgent(
            llm=llm_config,
            system_message=self.SYSTEM_PROMPT,
            function_list=[agent_call_tool],
            name=self.get_name(),
            description=self.get_description()
        )
