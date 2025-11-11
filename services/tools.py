"""qwen-agent tool implementations that wrap service functions."""

from __future__ import annotations

import json
from typing import Any, Dict

from qwen_agent.tools import BaseTool

from services import data_ops, growth_service, rag_service


class NotesIngestionTool(BaseTool):
    name = "ingest_notes"
    description = "导入本地 Markdown 笔记到数据库中，保持数据最新。"
    parameters = {
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "可选，覆盖默认的 NOTES_DIR。"
            }
        }
    }

    def call(self, params: Dict[str, Any], **_: Any) -> str:
        args = self._verify_json_format_args(params)
        result = data_ops.ingest_notes(args.get("directory"))
        return json.dumps(result, ensure_ascii=False, indent=2)


class NotesSummarizeTool(BaseTool):
    name = "summarize_notes"
    description = "运行摘要任务，为尚未处理的笔记生成 AI 摘要与标签。"
    parameters = {
        "type": "object",
        "properties": {}
    }

    def call(self, params: Dict[str, Any], **_: Any) -> str:
        self._verify_json_format_args(params or {})
        result = data_ops.summarize_notes()
        return json.dumps(result, ensure_ascii=False, indent=2)


class PhotoprismIngestionTool(BaseTool):
    name = "ingest_photoprism"
    description = "从 Photoprism 同步照片元数据到数据库。需要正确的 Photoprism 账号配置。"
    parameters = {"type": "object", "properties": {}}

    def call(self, params: Dict[str, Any], **_: Any) -> str:
        self._verify_json_format_args(params or {})
        result = data_ops.ingest_photoprism_photos()
        return json.dumps(result, ensure_ascii=False, indent=2)


class PhotoprismSummarizeTool(BaseTool):
    name = "summarize_photoprism"
    description = "为 Photoprism 中缺失描述的照片生成 AI 摘要。"
    parameters = {"type": "object", "properties": {}}

    def call(self, params: Dict[str, Any], **_: Any) -> str:
        self._verify_json_format_args(params or {})
        result = data_ops.summarize_photoprism_photos()
        return json.dumps(result, ensure_ascii=False, indent=2)


class VectorRAGSearchTool(BaseTool):
    name = "vector_rag_search"
    description = "在个人知识库（笔记/博客/照片）中进行语义检索，获取回答问题所需的上下文。"
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "必须，用户问题或要搜索的文本。"
            },
            "top_k": {
                "type": "integer",
                "minimum": 1,
                "maximum": 20,
                "default": 6,
                "description": "返回的语义匹配数量。"
            }
        },
        "required": ["query"]
    }

    def call(self, params: Dict[str, Any], **_: Any) -> str:
        args = self._verify_json_format_args(params)
        query = args["query"].strip()
        top_k = args.get("top_k", 6)
        results = rag_service.vector_search(query, top_k=top_k)
        return rag_service.format_vector_results(query, results)


class DailyHotTrendsTool(BaseTool):
    name = "daily_hot_trends"
    description = "抓取 Daily Hot 服务的热点榜单，用于灵感/热点洞察。"
    parameters = {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "可选，只获取指定榜单（按照名称匹配）。"
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 20,
                "default": 5,
                "description": "每个榜单返回的条数。"
            }
        }
    }

    def call(self, params: Dict[str, Any], **_: Any) -> str:
        args = self._verify_json_format_args(params or {})
        result = growth_service.fetch_daily_hot(args.get("category"), args.get("limit", 5))
        formatted = [f"来源：{result['source']}"]
        for category, items in result["results"].items():
            formatted.append(f"\n# {category}")
            for item in items:
                formatted.append(
                    f"- {item.get('title')} (score={item.get('hot_score')})\n  {item.get('description') or ''}\n  {item.get('url') or ''}"
                )
        return "\n".join(formatted)


def default_tools() -> Dict[str, BaseTool]:
    """Helper to create all built-in tools in one place."""
    tool_instances = [
        NotesIngestionTool(),
        NotesSummarizeTool(),
        PhotoprismIngestionTool(),
        PhotoprismSummarizeTool(),
        VectorRAGSearchTool(),
        DailyHotTrendsTool(),
    ]
    return {tool.name: tool for tool in tool_instances}
