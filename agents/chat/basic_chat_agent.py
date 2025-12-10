from typing import Dict, Optional, Any, List

from qwen_agent.agents import FnCallAgent

from agents.core.base.agent import QwenBaseAgent
from server import config


class BasicChatAgent(QwenBaseAgent):
    """基础对话助手"""

    def get_system_prompt(self) -> str:
        base_prompt = f'''
你的名字是千问

你的职责：
1. 作为默认助手，处理绝大多数普通对话、知识问答和简单任务。
2. 在需要获取最新信息、搜索网络内容时，可以调用 搜索 工具
   进行联网搜索，获取实时信息和网络资源。
3. 当上游路由或其他 Agent 无法处理用户需求时，你需要进行兜底回复，
   用自然语言向用户解释情况，并尽可能给出有帮助的建议或替代方案。

注意：
- 不要主动声称自己可以直接读取和长期保存用户上传的文件，
  与复杂文档/图片相关的任务通常会由其他专门的 Agent 来处理。
- 当你无法完成某些需求时，你需要进行兜底回复。
- 当用户询问需要最新信息或网络搜索的问题时，主动使用 duckduckgo_search 工具。
- 在回答用户问题时，不要告诉用户你选择了什么工具或调用了哪些工具，
  应该直接给出结果和答案，让交互体验更加自然流畅。
'''

        return base_prompt

    def get_tools(self) -> List[str]:
        """获取工具列表"""

        return ["google_web_search"]

    def get_name(self) -> str:
        """获取Agent名称"""
        return '基础对话助手'

    def get_description(self) -> str:
        """获取Agent描述"""
        return (
            '通用基础对话助手，负责大部分普通问答、闲聊和简单任务；'
            '在需要时可以调用代码执行等工具完成数学计算、代码运行等；'
            '当其他 Agent 或工具不适合时，由我以自然语言进行兜底回复。'
        )

    def get_llm_config(self) -> Dict[str, Any]:
        """重写父类方法，提供复杂的LLM配置逻辑"""
        return self._build_llm_cfg(generate_cfg=self._build_generate_cfg())

    def create_agent(self) -> FnCallAgent:
        """重写创建Agent方法，添加额外的工具配置逻辑"""
        # 处理工具动态配置
        self.tools = self.get_tools().copy()  # 复制一份避免修改原始列表

        # 调用父类方法创建Agent
        return super().create_agent()

    def _build_generate_cfg(self) -> Dict[str, bool]:
        """
        根据请求参数创建生成配置

        Returns:
            包含生成配置的字典
        """

        return {
            "use_raw_api": True,
            "max_input_tokens": 60000
        }

    def _build_llm_cfg(self,
                       generate_cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        构建LLM配置，如果model为空则使用兜底逻辑

        Args:
            model: 指定的模型名称
            generate_cfg: 生成配置
        """

        # 根据模型名称确定模型类型
        cfg: Dict[str, Any] = {
            "model": config.LLM_MODEL,
            "model_type": config.LLM_PROVIDER,
            "model_server": config.LLM_BASE_URL,
            "api_key": config.LLM_API_KEY,
            "generate_cfg": generate_cfg or {}
        }
        return cfg
