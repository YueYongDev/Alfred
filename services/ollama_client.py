"""Custom qwen-agent chat model that talks to a local Ollama server."""

from __future__ import annotations

import json
from typing import Dict, Iterator, List, Optional
from urllib.parse import urljoin

import requests

from qwen_agent.llm.base import BaseChatModel, ModelServiceError
from qwen_agent.llm.schema import ASSISTANT, Message
from qwen_agent.log import logger

from server import config


def _to_http_url(base: str) -> str:
    if base.startswith("http://") or base.startswith("https://"):
        return base
    return f"http://{base}"


class OllamaChatModel(BaseChatModel):
    """Minimal chat backend so qwen-agent can orchestrate Ollama models."""

    def __init__(self, cfg: Optional[Dict] = None):
        cfg = cfg or {}
        cfg.setdefault("model", config.BASE_MODEL)
        super().__init__(cfg)

        raw_base_url = cfg.get("base_url") or cfg.get("model_server") or config.OPENAI_BASE_URL
        self.base_url = _to_http_url(raw_base_url.rstrip("/"))
        self.chat_url = urljoin(self.base_url + "/", "api/chat")
        self.timeout = cfg.get("request_timeout", 600)
        self.options = cfg.get("options", {})

    def _chat_stream(
        self,
        messages: List[Message],
        delta_stream: bool,
        generate_cfg: dict,
    ) -> Iterator[List[Message]]:
        payload = self._build_payload(messages, generate_cfg, stream=True)
        try:
            with requests.post(self.chat_url, json=payload, stream=True, timeout=self.timeout) as resp:
                resp.raise_for_status()
                buffer = ""
                for raw_line in resp.iter_lines():
                    if not raw_line:
                        continue
                    chunk = json.loads(raw_line)
                    delta = chunk.get("message", {}).get("content", "")
                    if not delta:
                        continue
                    if delta_stream:
                        yield [Message(role=ASSISTANT, content=delta)]
                    else:
                        buffer += delta
                        yield [Message(role=ASSISTANT, content=buffer)]
        except requests.RequestException as exc:
            logger.exception("Ollama stream failed")
            raise ModelServiceError(exception=exc)

    def _chat_no_stream(
        self,
        messages: List[Message],
        generate_cfg: dict,
    ) -> List[Message]:
        payload = self._build_payload(messages, generate_cfg, stream=False)
        try:
            resp = requests.post(self.chat_url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.exception("Ollama request failed")
            raise ModelServiceError(exception=exc)

        content = data.get("message", {}).get("content", "").strip()
        return [Message(role=ASSISTANT, content=content)]

    def _chat_with_functions(
        self,
        messages: List[Message],
        functions: List[Dict],
        stream: bool,
        delta_stream: bool,
        generate_cfg: dict,
        lang: str,
    ) -> Iterator[List[Message]]:
        raise ModelServiceError(exception=RuntimeError("Function calling is not supported by OllamaChatModel."))

    def _continue_assistant_response(
        self,
        messages: List[Message],
        generate_cfg: dict,
        stream: bool,
    ) -> Iterator[List[Message]]:
        return self._chat(messages, stream=stream, delta_stream=False, generate_cfg=generate_cfg)

    def _build_payload(self, messages: List[Message], generate_cfg: dict, stream: bool) -> Dict:
        options = {**self.options}
        for key in ("temperature", "top_p", "top_k", "repeat_penalty", "num_ctx"):
            if key in generate_cfg:
                options[key] = generate_cfg[key]
        if generate_cfg.get("stop"):
            options["stop"] = generate_cfg["stop"]

        payload = {
            "model": self.model,
            "messages": [self._convert_message(msg) for msg in messages],
            "stream": stream,
        }
        if options:
            payload["options"] = options
        return payload

    @staticmethod
    def _convert_message(message: Message) -> Dict:
        if isinstance(message.content, list):
            content = "".join(part.text or "" for part in message.content if getattr(part, "text", None))
        else:
            content = message.content or ""
        return {
            "role": message.role,
            "content": content,
        }


def build_ollama_chat_model(cfg: Optional[Dict] = None) -> OllamaChatModel:
    cfg = cfg or {}
    cfg.setdefault("model", config.BASE_MODEL)
    cfg.setdefault("base_url", config.OPENAI_BASE_URL)
    return OllamaChatModel(cfg)
