from qwen_agent.agents import Assistant

from server import config

VISION_PROMPT = "你是视觉理解 Agent，负责分析用户提供的图片并回答与视觉内容相关的问题。"


def vision_assistant() -> Assistant:
    vl_llm_cfg = {
        "model": config.LLM_VL_MODEL,
        "model_server": config.LLM_BASE_URL,
        'model_type': 'qwenvl_oai',
        "api_key": config.LLM_API_KEY,
        "generate_cfg": {
            "temperature": config.LLM_TEMPERATURE,
        },
    }

    return Assistant(
        function_list=None,
        llm=vl_llm_cfg,
        system_message=VISION_PROMPT,
        name="vision",
        description="视觉理解助手，可处理包含图片的多模态提问。",
    )
