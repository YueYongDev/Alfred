from typing import Any, Dict, List, Optional

from qwen_agent import Agent as QwenAgent
from qwen_agent.agents import FnCallAgent

from agents.core.base.agent import QwenBaseAgent
from agents.core.context.builder import AgentContext
from server import config
from tools.orchestration.agent_call import AgentCallTool


class PlanningAgent(QwenBaseAgent):
    """总协调助手类，负责根据用户需求，合理调用不同的子Agent完成复杂任务"""

    SYSTEM_PROMPT = """
你是「总协调助手」（Planning），只处理需要多步骤、可能涉及多个子Agent的复杂任务。
用 call_sub_agent 调用子Agent（target 必须匹配名称）：
- 基础对话助手：通用文本任务
- 多文件智能助手：文档阅读/总结/检索
- 多模态助手：图像生成/理解/编辑

工作方式：
1) 判断是否复杂任务；复杂则拆分子任务并选择合适的 target。
2) 可多次调用 call_sub_agent 形成流程，读懂工具结果后再决定下一步。
3) 若任务很简单，直接交给基础对话助手。
4) 若无法完成，交给基础对话助手兜底说明并给出替代建议。
"""

    def __init__(
            self,
            bot_basic_chat: QwenAgent,
            bot_image: QwenAgent,
            bot_doc: Optional[QwenAgent] = None,
            context: AgentContext = None,
    ):
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
        self.bot_image = bot_image
        self.bot_doc = bot_doc

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
        return {
            "model": config.LLM_MODEL,
            "model_type": config.LLM_PROVIDER,
            "model_server": config.LLM_BASE_URL,
            "api_key": config.LLM_API_KEY,
        }

    def create_agent(self) -> FnCallAgent:
        """
        重写创建Agent方法，处理特殊的AgentCallTool

        Returns:
            FnCallAgent: 配置好的总协调助手实例
        """
        # 收集子Agent，key 用它们的 name
        sub_agents: Dict[str, QwenAgent] = {
            self.bot_basic_chat.name: self.bot_basic_chat,
            self.bot_image.name: self.bot_image,
        }
        if self.bot_doc:
            sub_agents[self.bot_doc.name] = self.bot_doc

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
