import json
from typing import Dict

from qwen_agent import Agent
from qwen_agent.tools.base import register_tool

from tools.core.base import QwenAgentBaseTool


@register_tool("call_sub_agent")
class AgentCallTool(QwenAgentBaseTool):
    # name = "call_sub_agent"
    description = """
    调用下游子Agent来完成一个子任务。

    参数：
    - target: 子Agent名称，可选值包括：基础工具助手、多文件智能助手、多模态助手 等
    - instruction: 给该子Agent的具体指令（自然语言），例如：
      "总结当前文档形成思维导图的大纲（用JSON输出）"
      "根据下面的大纲生成一张思维导图图片"
    - extra_context: （可选）附加的上下文字符串，会一起发给子Agent
    返回：子Agent的完整回复文本（包含其工具调用结果的最终自然语言输出）。
    """

    def __init__(self, agents: Dict[str, Agent]):
        super().__init__()
        # 这里用 dict 存所有子 agent，key 用 agent.name
        self.agents = agents

    def _execute_tool(self, params: str, **kwargs) -> str:
        try:
            # 解析参数
            params_dict = json.loads(params)
            target = params_dict.get("target", "")
            instruction = params_dict.get("instruction", "")
            extra_context = params_dict.get("extra_context", "")

            if not target:
                return json.dumps({"error": "缺少必需参数 target"}, ensure_ascii=False)
            if not instruction:
                return json.dumps({"error": "缺少必需参数 instruction"}, ensure_ascii=False)

        except (json.JSONDecodeError, TypeError) as e:
            return json.dumps({"error": f"参数解析失败: {str(e)}"}, ensure_ascii=False)

        if target not in self.agents:
            return json.dumps({
                "error": f"未找到名为 {target} 的子Agent，请检查 target 参数。可用的Agent: {list(self.agents.keys())}"
            }, ensure_ascii=False)

        sub_agent = self.agents[target]

        # 构造发给子Agent的消息
        content = instruction
        if extra_context:
            content += "\n\n[补充上下文]\n" + extra_context

        messages = [
            {"role": "user", "content": content}
        ]

        try:
            # 修复流式输出处理：每个chunk的content是累积内容，只需要取最后一个
            result_text = ""
            for chunks in sub_agent.run(messages=messages, stream=False):
                for msg in chunks:
                    if msg["role"] == "assistant":
                        # 直接使用最新的完整内容，而不是累加
                        current_content = msg.get("content", "")
                        if current_content:  # 只有当内容不为空时才更新
                            result_text = current_content

            return json.dumps({"result": result_text}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": f"调用子Agent失败: {str(e)}"}, ensure_ascii=False)
