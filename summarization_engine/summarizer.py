import json
from typing import Tuple, List

from llama_index.core.llms import ChatMessage
from llama_index.core.llms import TextBlock, ImageBlock

from rag_engine.providers import get_vision_llm, get_summarize_llm


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
        "请分析这张图片，总结其主要内容，并提取2-5个相关标签。内容用中文回复"
        "返回严格的 JSON，格式如下：\n"
        '{"description":"...","tags":["tag1","tag2"]}'
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
        # ① 发送请求
        resp = llm.chat(messages)
        raw = resp.message.content.strip()
        data = json.loads(raw)
        return data

    except Exception as e:
        print(f"[Warning] analyze_photo({image_path}) failed → {e}")
        return {"description": "", "tags": ""}

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
    image_path="/Users/yueyong/alfred_test_data/photos/0.png"
    file_path="/Users/yueyong/alfred_test_data/blogs/技术科普/浅谈策略模式在消息转发场景下的应用.md"

    image_summary, image_tags = summarize_photo_file(image_path)
    file_summary, file_tags = summarize_text_file(file_path)

    print(f"Image Summary: {image_summary}")
    print(f"Image Tags: {image_tags}")

    print(f"File Summary: {file_summary}")
    print(f"File Tags: {file_tags}")
