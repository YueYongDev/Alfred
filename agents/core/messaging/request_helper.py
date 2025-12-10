from typing import Dict, List, Any

from agents.core.messaging.chat_request import ChatRequest


def convert_chat_request_to_messages(request: ChatRequest) -> List[Dict[str, Any]]:
    """
    将 ChatRequest 转换为 Qwen-Agent 所需的消息列表（保留结构化内容）
    """
    qa_messages: List[Dict[str, Any]] = []

    # 支持新旧两种格式
    messages = None
    if request.body and request.body.messages:
        messages = request.body.messages
    elif request.data and request.data.messages:
        messages = request.data.messages

    if messages:
        for m in messages:
            role = m.role
            content = m.content if m.content is not None else ""
            if role == 'system':
                continue

            # 将 plugin role 转换为 function，因为 qwen_agent 不支持 plugin role
            if role == 'plugin':
                role = 'function'

            # 获取 name 字段（如果存在）
            name = getattr(m, 'name', None)
            # 2) 如果没有 name，再从 metadata.agent_name 里还原
            metadata = getattr(m, 'metadata', None)
            if not name and metadata and isinstance(metadata, dict):
                name = metadata.get("agent_name")

            # 跳过工具相关的消息：
            # 1. 跳过 content 为空的 assistant 消息（工具调用消息）
            # 2. 跳过 function/tool 消息（工具返回结果），因为前置的工具调用消息已被跳过
            # 这样可以避免 "tool must be a response to a preceeding message with tool_calls" 错误
            if role == 'assistant' and content == '':
                continue
            if role == 'function':
                continue

            # 检查是否为富文本消息（包含图像等）
            if isinstance(content, str):
                # 普通文本内容
                message_dict = {"role": role, "content": content}
                if name:
                    message_dict["name"] = name
                qa_messages.append(message_dict)
            elif isinstance(content, list):
                # 富文本内容，可能包含图片、文本等
                structured_content = []
                for item in content:
                    if isinstance(item, dict):
                        if 'image' in item:
                            # 图片内容
                            structured_content.append({
                                "image": item['image']
                            })
                        elif 'text' in item:
                            # 文本内容
                            structured_content.append({
                                "text": item['text']
                            })
                        elif 'file' in item:
                            # 文件内容 - 只保留 file 字段，移除 file_id 字段避免 Qwen-Agent 框架错误
                            structured_content.append({
                                "file": item['file'],
                            })
                        else:
                            # 其他类型的内容，直接添加
                            structured_content.append(item)
                    else:
                        # 纯文本内容
                        structured_content.append(str(item))

                message_dict = {"role": role, "content": structured_content}
                if name:
                    message_dict["name"] = name
                qa_messages.append(message_dict)
            else:
                # 其他类型的内容 - 确保添加了content键
                message_dict = {"role": role, "content": content}
                if name:
                    message_dict["name"] = name
                qa_messages.append(message_dict)
    else:
        raise ValueError("chat requires data.messages")
    return qa_messages


def _add_file_to_list(files_list: List[Dict[str, str]], file_url: str, file_id: str = "") -> None:
    """
    将文件添加到列表中，如果文件已存在则更新其 file_id
    """
    for existing_file in files_list:
        if isinstance(existing_file, dict) and existing_file.get("file") == file_url:
            # 如果文件已在列表中，但file_id为空而当前有file_id，则更新file_id
            if not existing_file.get("file_id") and file_id:
                existing_file["file_id"] = file_id
            return
    # 如果文件不存在，则添加到列表
    files_list.append({"file": file_url, "file_id": file_id})


def _extract_files_from_param_list(files_param: List) -> List[Dict[str, str]]:
    """
    从参数列表中提取文件
    """
    files_list = []
    if isinstance(files_param, list):
        for f in files_param:
            if isinstance(f, str):
                # 假设原始格式为字符串，转换为新的字典格式，file_id暂时用空字符串
                files_list.append({"file": f, "file_id": ""})
            elif isinstance(f, dict) and "file" in f and "file_id" in f:
                # 如果已经是目标格式，直接添加
                files_list.append(f)
    return files_list


def _extract_files_from_messages_content(messages) -> List[Dict[str, str]]:
    """
    从消息内容中提取文件
    """
    files_list = []
    if messages:
        for m in messages:
            content = m.content if hasattr(m, 'content') else m.get('content') if isinstance(m, dict) else None
            # 从富文本消息结构中提取 {"file": "...", "file_id": "..."} 项
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "file" in item:
                        file_url = item.get("file")
                        file_id = item.get("file_id", "")  # 提取file_id，如果不存在则为空字符串
                        if isinstance(file_url, str) and file_url:
                            files_list.append({"file": file_url, "file_id": file_id})
    return files_list


def extract_files_from_request(request: ChatRequest) -> List[Dict[str, str]]:
    """
    处理文件列表，将其转换为统一格式
    从请求参数和消息内容中提取文件
    """
    # 从参数中提取文件列表（如果 parameters 是对象，尝试获取 extra 字段）
    files_param = None
    if request.parameters:
        # 如果 parameters 是 Pydantic 对象
        if hasattr(request.parameters, 'extra'):
            files_param = request.parameters.extra.get("files") if request.parameters.extra else None
        # 如果是字典（向后兼容）
        elif isinstance(request.parameters, dict):
            files_param = request.parameters.get("files")

    files_list = _extract_files_from_param_list(files_param) if files_param else []

    # 从消息内容中提取文件（保留从消息结构中提取文件的功能，但仅用于获取file_id信息）
    message_files = _extract_files_from_messages_content(
        getattr(request.body, 'messages', None) if request.body else
        (getattr(request.data, 'messages', None) if request.data else None))

    # 合并两个列表，如果有重复的文件URL，用消息中的file_id更新参数中的file_id
    for file_item in message_files:
        file_url = file_item.get("file", "")
        file_id = file_item.get("file_id", "")
        _add_file_to_list(files_list, file_url, file_id)

    return files_list


def extract_images_from_request(request: ChatRequest) -> List[str]:
    """
    从请求中提取图片URL列表

    Args:
        request: 聊天请求对象

    Returns:
        图片URL列表
    """
    images: List[str] = []

    # 支持新旧两种格式
    messages = None
    if request.body and request.body.messages:
        messages = request.body.messages
    elif request.data and request.data.messages:
        messages = request.data.messages

    if messages:
        for message in messages:
            content = message.content if hasattr(message, 'content') else None

            # 从富文本消息结构中提取图片
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        image_url = item.get("image")
                        if isinstance(image_url, str) and image_url:
                            images.append(image_url)
                        # 也考虑 image_url 字段
                        image_url = item.get("image_url")
                        if isinstance(image_url, str) and image_url:
                            images.append(image_url)

    # 去重并保持顺序
    seen = set()
    dedup: List[str] = []
    for x in images:
        if x not in seen:
            dedup.append(x)
            seen.add(x)

    return dedup
