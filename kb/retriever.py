"""Hybrid dense + BM25 retrieval."""
from __future__ import annotations

import os
from functools import lru_cache

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from rank_bm25 import BM25Okapi

from .build_index import COLLECTION


def _persist_dir() -> str:
    return os.getenv("KB_CHROMA_DIR", ".chroma")


@lru_cache(maxsize=1)
def _vec():
    return Chroma(
        persist_directory=_persist_dir(),
        collection_name=COLLECTION,
        embedding_function=OpenAIEmbeddings(model="text-embedding-3-small"),
    )


@lru_cache(maxsize=1)
def _bm25_index():
    coll = _vec()._collection
    raw = coll.get(include=["documents", "metadatas"])
    docs, metas = raw["documents"], raw["metadatas"]
    corpus_tokens = [(d or "").lower().split() for d in docs]
    return BM25Okapi(corpus_tokens), docs, metas


def hybrid_search(query: str, top_k: int = 4, alpha: float = 0.5) -> list[dict]:
    """alpha=1.0 → pure dense, alpha=0.0 → pure BM25."""
    dense_hits = _vec().similarity_search_with_score(query, k=top_k * 3)
    bm25, docs, metas = _bm25_index()
    bm25_scores = bm25.get_scores(query.lower().split())

    by_text: dict[str, dict] = {}
    for d, dist in dense_hits:
        text = d.page_content
        by_text[text] = {
            "text": text,
            "metadata": d.metadata,
            "dense_score": 1.0 / (1.0 + float(dist)),
            "bm25_score": 0.0,
        }
    bm25_max = max(bm25_scores) if len(bm25_scores) else 1.0
    for text, meta, s in zip(docs, metas, bm25_scores):
        norm = float(s) / bm25_max if bm25_max else 0.0
        if text in by_text:
            by_text[text]["bm25_score"] = norm
        else:
            by_text[text] = {
                "text": text,
                "metadata": meta or {},
                "dense_score": 0.0,
                "bm25_score": norm,
            }

    combined = [
        {**v, "score": alpha * v["dense_score"] + (1 - alpha) * v["bm25_score"]}
        for v in by_text.values()
    ]
    combined.sort(key=lambda x: -x["score"])
    return combined[:top_k]


def get_document_by_id(chunk_id: int) -> dict | None:
    coll = _vec()._collection
    raw = coll.get(where={"chunk_id": chunk_id}, include=["documents", "metadatas"])
    if not raw["documents"]:
        return None
    return {"text": raw["documents"][0], "metadata": raw["metadatas"][0]}


def list_collections() -> list[dict]:
    return [{"name": COLLECTION, "doc_count": _vec()._collection.count()}]
