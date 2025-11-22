from qwen_agent.agents import Assistant
from qwen_agent.tools import ImageZoomInToolQwen3VL

from server import config
from tools.image_gen import MyImageGen

VISION_PROMPT = "你是图像创建Agent，可以根据要求实现文生图，或者根据已有图片进行图生图或者图片修改。"


def image_gen_assistant() -> Assistant:
    vl_llm_cfg = {
        "model": config.LLM_VL_MODEL,
        "model_server": config.LLM_BASE_URL,
        'model_type': 'qwenvl_oai',
        "api_key": config.LLM_API_KEY,
        "generate_cfg": {
            "temperature": config.LLM_TEMPERATURE,
        },
    }

    tool_instances = [
        MyImageGen(),
        ImageZoomInToolQwen3VL(),
    ]

    return Assistant(
        function_list=tool_instances,
        llm=vl_llm_cfg,
        system_message=VISION_PROMPT,
        name="image_gen_assistant",
        description="图像创建Agent，可以根据要求实现文生图，或者根据已有图片进行图生图或者图片修改。",
    )
