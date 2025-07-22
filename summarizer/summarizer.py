import json
from typing import Tuple, List

from llama_index.core.llms import ChatMessage
from llama_index.core.llms import TextBlock, ImageBlock

from llm.providers import get_vision_llm, get_summarize_llm


def analyze_text(text: str) -> dict:
    llm = get_summarize_llm()

    prompt_txt = (
        "请对以下文本内容进行分析，总结其主要内容，并提取2-5个相关标签。内容用中文回复"
        "请返回严格的JSON格式，格式如下：\n"
        '{"description":"这里填写总结内容","tags":["标签1","标签2", "..."]}\n'
        "文本内容如下：\n"
        f"{text}"
    )

    messages = [
        ChatMessage(
            role="user",
            blocks=[
                TextBlock(text=prompt_txt),
            ],
        )
    ]

    try:
        # ① 发送请求
        resp = llm.chat(messages)
        raw = resp.message.content.strip()
        data = json.loads(raw)
        return data

    except Exception as e:
        print(f"[Warning] summarize_text({text}) failed → {e}")
        return {"description": "", "tags": ""}


def analyze_photo(image_path: str) -> dict:
    llm = get_vision_llm()

    prompt_txt = (
        "请仔细分析这张图片，详细描述图片的主要内容，包括但不限于："
        "主体物体、颜色、环境背景、光线状况、可能的拍摄设备、物体之间的关系、材质等。"
        "请避免模糊描述，尽量具体且详细。"
        "这段描述会用于后续的智能问答系统，要求信息详尽且准确。"
        "然后提取2-5个与图片内容高度相关的标签。"
        "请用中文回复，并返回严格的JSON格式，格式如下：\n"
        '{"description":"详细描述内容...","tags":["标签1","标签2"]}\n'
        "例如：\n"
        '{"description": "图片中有一台银色的富士XE3相机，放置在白色桌面上，背景是绿色植物。", '
        '"tags": ["富士XE3", "相机", "桌面", "植物"]}'
    )

    messages = [
        ChatMessage(
            role="user",
            blocks=[
                ImageBlock(path=image_path),
                TextBlock(text=prompt_txt),
            ],
        )
    ]

    try:
        resp = llm.chat(messages)
        raw = resp.message.content.strip()
        data = json.loads(raw)
        return data

    except Exception as e:
        print(f"[Warning] analyze_photo({image_path}) failed → {e}")
        return {"description": "", "tags": []}


def summarize_text_file(file_path: str) -> Tuple[str, List[str]]:
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()
    result = analyze_text(content)
    summary = result.get("description") or ""
    tags = result.get("tags") or []
    return summary, tags


def summarize_photo_file(image_path: str) -> Tuple[str, List[str]]:
    try:
        result = analyze_photo(image_path)
        summary = result.get("description") or ""
        tags = result.get("tags") or []
        return summary, tags
    except Exception as e:
        print(f"[⚠️] 图片分析失败: {image_path} - {e}")
        return "", []


if __name__ == '__main__':
    image_path = "/Users/yueyong/alfred_test_data/photos/5F6DE366-A1E4-433A-90C7-79048CB7B7DE.jpg"
    file_path = "/Users/yueyong/alfred_test_data/blogs/技术科普/浅谈策略模式在消息转发场景下的应用.md"

    image_summary, image_tags = summarize_photo_file(image_path)
    file_summary, file_tags = summarize_text_file(file_path)

    print(f"Image Summary: {image_summary}")
    print(f"Image Tags: {image_tags}")

    print(f"File Summary: {file_summary}")
    print(f"File Tags: {file_tags}")
