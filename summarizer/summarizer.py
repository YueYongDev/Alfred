import json
import tempfile
import time
from typing import Tuple, List

import pillow_heif
import requests

pillow_heif.register_heif_opener()
from PIL import Image, UnidentifiedImageError
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


def validate_and_prepare_image(file_path: str, max_size=(2048, 2048)) -> str:
    """
    统一处理图片格式，尤其处理伪 JPG 的 HEIF 图像，返回一个临时 JPEG 路径。
    """
    try:
        # 尝试打开图片
        with Image.open(file_path) as im:
            # 自动缩小超高分辨率图像
            im = im.convert("RGB")
            im.thumbnail(max_size)

            # 保存为临时 JPEG 文件
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                im.save(tmp.name, format="JPEG")
                return tmp.name

    except UnidentifiedImageError as e:
        raise ValueError(f"无法识别图片格式: {file_path} → {e}")
    except Exception as e:
        raise ValueError(f"图片处理失败: {file_path} → {e}")


def resize_image(image_path: str, max_size=(1024, 1024)) -> str:
    with Image.open(image_path) as im:
        im = im.convert("RGB")
        im.thumbnail(max_size)
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            im.save(tmp.name, format="JPEG")
            return tmp.name


def analyze_photo(image_path: str) -> dict:
    global raw
    llm = get_vision_llm()

    prompt_txt = (
        "请仔细分析这张图片，详细描述图片的主要内容，包括但不限于："
        "图片的分类、主体物体、颜色、环境背景、光线状况、可能的拍摄设备、物体之间的关系、材质等。"
        "请避免模糊描述，尽量具体。然后提取2-5个与图片内容高度相关的标签。同时也要标记出图片的类型，例如：风景、人物、动物、建筑、截图等。"
        "返回合法 JSON，格式如下：\n"
        '{"description":"详细描述内容...","tags":["标签1","标签2"]}'
    )

    try:
        processed_path = resize_image(image_path, max_size=(1024, 1024))

        messages = [
            ChatMessage(
                role="user",
                blocks=[
                    ImageBlock(path=processed_path),
                    TextBlock(text=prompt_txt),
                ],
            )
        ]

        resp = llm.chat(messages)
        raw = resp.message.content.strip()
        return json.loads(raw)

    except requests.exceptions.RequestException as e:
        print(f"[Error] 模型服务异常 → {e}")
        return {"description": "", "tags": []}
    except json.JSONDecodeError as e:
        print(f"[Error] 模型返回非 JSON → {e, raw}")
        return {"description": "", "tags": []}
    except Exception as e:
        print(f"[Error] analyze_photo({image_path}) failed → {e.args}")
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
    image_path = "/Volumes/personal_folder/Photos/2025/03/23/104033.JPG"
    file_path = "/Users/yueyong/alfred_test_data/blogs/技术科普/浅谈策略模式在消息转发场景下的应用.md"

    start_time = time.time()
    image_summary, image_tags = summarize_photo_file(image_path)
    elapsed = time.time() - start_time
    print(f"took {elapsed:.2f} seconds")
    # file_summary, file_tags = summarize_text_file(file_path)

    print(f"Image Summary: {image_summary}")
    print(f"Image Tags: {image_tags}")

    # print(f"File Summary: {file_summary}")
    # print(f"File Tags: {file_tags}")
