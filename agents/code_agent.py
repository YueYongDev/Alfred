from qwen_agent.agents import Assistant
from qwen_agent.tools import ImageSearch, PythonExecutor, CodeInterpreter

from server import config

CODE_AGENT_PROMPT = "你是视觉理解 Agent，负责分析用户提供的图片并回答与视觉内容相关的问题。"


def code_assistant() -> Assistant:
    code_llm_cfg = {
        "model": config.LLM_CODE_MODEL,
        "model_server": config.LLM_BASE_URL,
        "api_key": config.LLM_API_KEY,
        "generate_cfg": {
            "temperature": config.LLM_TEMPERATURE,
        },
    }

    tool_instances = [
        PythonExecutor(),
        CodeInterpreter()
    ]

    return Assistant(
        function_list=tool_instances,
        llm=code_llm_cfg,
        system_message=CODE_AGENT_PROMPT,
        name="code_agent",
        description="视觉理解助手，可处理包含图片的多模态提问。",
    )
