from typing import Dict, Optional, Any, List

from qwen_agent.agents import FnCallAgent

from agents.core.base.agent import QwenBaseAgent
from server import config


class MainChatAgent(QwenBaseAgent):
    """基础对话助手"""

    def get_system_prompt(self) -> str:
        base_prompt = f'''
你是千问，默认对话助手。处理普通问答、闲聊和简单任务。
需要最新信息时使用 duckduckgo_search。
无法完成时给出简短兜底说明与可行替代建议。
不声称可长期保存或直接读取用户文件；回答时不暴露工具调用细节。
'''

        return base_prompt

    def get_tools(self) -> List[str]:
        """获取工具列表"""

        return ["duckduckgo_search"]

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
            "use_raw_api": False,
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
