"""Utility helpers for working with the unified RAG engine."""

from __future__ import annotations

import time
from typing import Dict, List

from rag_engine.vector_rag.build_index import build_index
from rag_engine.vector_rag.query_engine import search_vector_db


def rebuild_unified_index() -> Dict:
    """Rebuild the unified pgvector index from the relational tables."""
    started = time.time()
    build_index()
    duration = time.time() - started
    return {
        "task": "rebuild_unified_index",
        "elapsed_seconds": round(duration, 2),
    }


def vector_search(query: str, top_k: int = 6) -> List[Dict]:
    """Run a similarity search against the unified_embeddings table."""
    return search_vector_db(query, top_k=top_k)


def format_vector_results(query: str, results: List[Dict]) -> str:
    if not results:
        return f"No relevant content found for query: {query}"

    lines = [f"Top matches for: {query}"]
    for idx, item in enumerate(results, start=1):
        lines.append(
            f"[{idx}] type={item['entry_type']} id={item['entry_id']} score={item['score']:.4f}\n{item['text']}"
        )
    return "\n\n".join(lines)
