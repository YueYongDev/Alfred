import uuid
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field

from agents.core.chat_request import Message


class Custom(BaseModel):
    model_name: str = ""
    search_prob: str = "impossible"
    task_category: List[str] = Field(default_factory=list)


# class Message(BaseModel):
#     role: str
#     from_: Optional[str] = Field(None, alias="from")  # 使用 from_ 并设置别名
#     content: str
#     name: Optional[str] = None
#     function_call: Optional[dict] = None


class Choice(BaseModel):
    finish_reason: str = "stop"
    messages: List[Message]


class Output(BaseModel):
    custom: Custom
    choices: List[Choice]


class Usage(BaseModel):
    completion_tokens: int = 0
    output_tokens: int = 0
    input_tokens: int = 0
    prompt_tokens: int = 0
    model_name: str = ""
    total_tokens: int = 0


class Header(BaseModel):
    task_id: str = ""
    attributes: Dict[str, str] = Field(default_factory=lambda: {"X-DashScope-Experiments": ""})
    event: str = "result-generated"  # task-finished，task-started, result-generated, task-failed
    trace_id: str


class Payload(BaseModel):
    output: Output
    usage: Usage


class ChatResponse(BaseModel):
    code: int = 200
    payload: Payload
    header: Header
    message: str = ""
    track_info: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @classmethod
    def from_success_content(cls, messages: List[Dict[str, str]],
                             model_name: str = "",
                             task_id: str = "",
                             custom: Optional[Dict[str, Any]] = None,
                             usage: Optional[Dict[str, Any]] = None,
                             event: str = "result-generated",
                             track_info: Optional[Dict[str, Any]] = None) -> "ChatResponse":
        """从内容创建响应对象
        
        Args:
            messages: 消息列表
            model_name: 模型名称
            task_id: 任务ID
            custom: 自定义信息
            usage: token 使用情况，格式: {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
            event: 事件类型
            track_info: 跟踪信息
        """
        if custom is None:
            custom = {
                "model_name": model_name,
                "search_prob": "impossible",
                "task_category": []
            }
        if track_info is None:
            track_info = {}
        task_id = task_id or str(uuid.uuid4())
        # 转换消息格式，确保content字段不是None
        processed_messages = []
        for msg in messages:
            # 确保content字段不是None
            if 'content' not in msg or msg.get('content') is None:
                msg = msg.copy()  # 避免修改原始数据
                msg['content'] = ''
            processed_messages.append(Message(**msg))
        formatted_messages = processed_messages

        # 构建 usage 对象
        usage_obj = Usage(model_name=model_name)
        if usage:
            usage_obj.prompt_tokens = usage.get("input_tokens", 0)
            usage_obj.input_tokens = usage.get("input_tokens", 0)
            usage_obj.completion_tokens = usage.get("output_tokens", 0)
            usage_obj.total_tokens = usage.get("total_tokens", 0)
            usage_obj.output_tokens = usage.get("output_tokens", 0)

        return cls(
            code=200,
            payload=Payload(
                output=Output(
                    custom=Custom(**custom),
                    choices=[Choice(
                        finish_reason="stop",
                        messages=formatted_messages
                    )]
                ),
                usage=usage_obj
            ),
            header=Header(
                task_id=task_id,
                event=event,
            ),
            track_info=track_info
        )

    @classmethod
    def from_failed_content(cls, code: int = 500, message: str = "",
                            task_id: str = "",
                            event: str = "task-failed",
                            track_info: Optional[Dict[str, Any]] = None) -> "ChatResponse":
        """创建失败响应对象"""
        if track_info is None:
            track_info = {}
        # 错误消息中可能包含消息，确保这些消息的content字段不为None
        error_messages = [{
            "role": "assistant",
            "content": f"处理过程中出现错误: {message}" if message else "处理过程中出现错误"
        }]

        # 确保错误消息中的content字段不为None
        processed_messages = []
        for msg in error_messages:
            if 'content' not in msg or msg.get('content') is None:
                msg = msg.copy()
                msg['content'] = ''
            processed_messages.append(Message(**msg))

        return cls(
            code=code,
            message=message,
            payload=Payload(
                output=Output(
                    custom=Custom(),
                    choices=[Choice(
                        finish_reason="stop",
                        messages=processed_messages
                    )]
                ),
                usage=Usage()
            ),
            header=Header(
                task_id=task_id,
                event=event,
            ),
            track_info=track_info
        )


if __name__ == "__main__":
    # 测试成功响应
    success_messages = [
        {
            "role": "assistant",
            "content": "你好"
        }
    ]
    success_response = ChatResponse.from_success_content(messages=success_messages)
    print("Success Response:")
    print(success_response.model_dump_json())

    # 测试失败响应
    failed_response = ChatResponse.from_failed_content(
        code=500,
        message="Internal Server Error"
    )
    print("\nFailed Response:")
    print(failed_response.model_dump_json())
