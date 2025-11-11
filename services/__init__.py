"""Shared service layer for qwen-agent tools.

This package exposes reusable wrappers around the existing collectors,
summarizers and retrieval modules so tools (and future micro-services)
can call them with a simple, well-defined API.
"""

from . import data_ops, rag_service, growth_service  # noqa: F401
