"""Orchestrator runtime built on top of qwen-agent."""

from __future__ import annotations

from typing import Dict, Iterator, List

from qwen_agent.agents import ReActChat

from services.ollama_client import build_ollama_chat_model
from services.tools import default_tools

SYSTEM_PROMPT = (
    "你是 Alfred 的总协调 Agent，需要综合个人知识库、日常数据源以及各种工具来回答问题。"
    "在作答前应先判断是否需要查询 vector_rag_search 等工具，并给出引用或依据。"
    "当用户要求触发数据同步或摘要任务时，可以调用 ingest_/summarize_ 系列工具。"
)


def build_agent() -> ReActChat:
    tools = list(default_tools().values())
    llm = build_ollama_chat_model()
    return ReActChat(function_list=tools, llm=llm, system_message=SYSTEM_PROMPT, name="Orchestrator")


def run_agent(messages: List[Dict]) -> str:
    """Run the orchestrator in non-streaming mode and return the final content string."""
    agent = build_agent()
    responses = agent.run_nonstream(messages)
    if not responses:
        return ""
    return responses[-1].content or ""


def stream_agent(messages: List[Dict]) -> Iterator[str]:
    """Stream textual deltas from the orchestrator."""
    agent = build_agent()
    buffer = ""
    for chunk in agent.run(messages):
        if not chunk:
            continue
        latest = chunk[-1].content or ""
        if latest.startswith(buffer):
            delta = latest[len(buffer):]
        else:
            delta = latest
        buffer = latest
        if delta:
            yield delta
