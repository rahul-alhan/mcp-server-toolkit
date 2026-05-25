"""MCP tool implementations — delegates to the kb/ layer.

KB imports are deferred so this module can be imported (and SearchInput
validated) on a box without Chroma / OpenAI installed.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

MAX_QUERY_CHARS = 2000


class SearchInput(BaseModel):
    query: str = Field(..., max_length=MAX_QUERY_CHARS)
    top_k: int = Field(4, ge=1, le=20)
    alpha: float = Field(0.5, ge=0.0, le=1.0, description="1.0=dense, 0.0=BM25")


def _kb():
    from kb import retriever as _r
    return _r


def tool_search_knowledge_base(query: str, top_k: int = 4, alpha: float = 0.5) -> list[dict]:
    args = SearchInput(query=query, top_k=top_k, alpha=alpha)
    hits = _kb().hybrid_search(args.query, args.top_k, args.alpha)
    return [
        {
            "text": h["text"],
            "source": h["metadata"].get("source", ""),
            "chunk_id": h["metadata"].get("chunk_id"),
            "score": round(float(h["score"]), 4),
        }
        for h in hits
    ]


def tool_get_document_by_id(chunk_id: int) -> dict:
    doc = _kb().get_document_by_id(chunk_id)
    if doc is None:
        return {"error": "not_found", "chunk_id": chunk_id}
    return {
        "text": doc["text"],
        "source": doc["metadata"].get("source", ""),
        "chunk_id": chunk_id,
    }


def tool_list_collections() -> list[dict]:
    return _kb().list_collections()


def tool_summarize_document(chunk_id: int) -> dict:
    """Server returns the text + a directive — the client LLM does the summarization."""
    doc = _kb().get_document_by_id(chunk_id)
    if doc is None:
        return {"error": "not_found"}
    return {
        "text": doc["text"],
        "source": doc["metadata"].get("source", ""),
        "directive": "Summarize the text above in <=120 words. Preserve concrete numbers, dates, and named entities exactly.",
    }
