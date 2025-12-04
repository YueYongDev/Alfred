from typing import List, Dict, Any

from qwen_agent.agents import FnCallAgent

from agents.core.qwen_agent_context_builder import AgentContext
from agents.core.qwen_base_agent import QwenBaseAgent
from agents.core.tools_select_helper import convert_tool_names_to_instances


class CodeAgent(QwenBaseAgent):
    """代码助手类，专注于帮助用户进行代码分析、执行和问题解决"""

    SYSTEM_PROMPT = '''
你是一个专业的代码助手，专注于帮助用户进行代码分析、执行和问题解决。

## 核心能力

1. **代码执行**：运行Python代码并提供结果
   - 支持各种Python库和框架的使用
   - 提供代码执行环境，可以运行用户提供的代码片段
   - 能够处理数据分析、计算、算法实现等任务

2. **代码分析**：分析代码逻辑和结构
   - 代码审查和优化建议
   - 错误诊断和修复建议
   - 代码风格和最佳实践指导
   - 性能分析和优化建议

3. **代码生成**：根据需求生成代码
   - 根据用户描述生成Python代码
   - 提供多种实现方案和选择
   - 生成注释完整、结构清晰的代码

4. **问题解决**：协助解决编程相关问题
   - 算法设计和实现
   - 数据处理和分析
   - 编程概念解释和教学
   - 调试和故障排除

## 工作原则

1. **安全执行**：确保代码执行的安全性，避免危险操作
2. **清晰解释**：对代码逻辑和执行结果进行清晰的解释
3. **最佳实践**：提供符合Python最佳实践的代码建议
4. **教育性**：在解决问题的同时，帮助用户学习和理解
5. **结果导向**：专注于解决用户的实际问题和需求

## 使用场景

- 数据分析和可视化
- 算法实现和验证
- 代码调试和优化
- 学习编程概念和技术
- 自动化脚本开发
- 数学计算和建模

当用户提出代码相关需求时，我会根据具体情况选择合适的工具来帮助解决问题。
'''

    def __init__(self, context: AgentContext = None):
        """
        初始化代码助手

        Args:
            context: Agent上下文对象
        """
        super().__init__(context)
        self.context = context

    def get_tools(self) -> List[str]:
        """获取工具列表"""
        return ["code_interpreter", "python_executor"]

    def get_name(self) -> str:
        """获取Agent名称"""
        return '代码助手'

    def get_description(self) -> str:
        """获取Agent描述"""
        return (
            '专门处理所有代码相关任务，包括：1) 代码执行和运行；2) 代码分析和审查；'
            '3) 代码生成和优化；4) 编程问题解决。能够帮助用户进行Python编程、数据分析、'
            '算法实现、调试等各种编程相关活动。'
        )

    def get_llm_config(self) -> Dict[str, Any]:
        """获取LLM配置"""
        generate_cfg = {
            "enable_thinking": False,
            "temperature": 0.1  # 代码相关任务使用较低的温度以确保准确性
        }

        return {
            "model": "qwen3-code-plus",
            "model_type": "oai",
            "generate_cfg": generate_cfg
        }

    def create_agent(self) -> FnCallAgent:
        """
        创建并返回FnCallAgent实例

        Returns:
            FnCallAgent: 配置好的代码助手实例
        """
        return FnCallAgent(
            system_message=self.SYSTEM_PROMPT,
            llm=self.get_llm_config(),
            function_list=convert_tool_names_to_instances(self.get_tools(), self.context),
            name=self.get_name(),
            description=self.get_description()
        )
