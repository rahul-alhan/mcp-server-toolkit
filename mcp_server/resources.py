"""MCP resource handlers — read-only views of the knowledge base."""
from __future__ import annotations

import json

from kb.retriever import get_document_by_id, list_collections


def resource_collections() -> str:
    return json.dumps(list_collections(), indent=2)


def resource_collection(name: str) -> str:
    collections = list_collections()
    match = next((c for c in collections if c["name"] == name), None)
    if not match:
        return json.dumps({"error": "not_found", "name": name})
    return json.dumps(match, indent=2)


def resource_document(chunk_id: str) -> str:
    try:
        cid = int(chunk_id)
    except ValueError:
        return json.dumps({"error": "invalid_id", "value": chunk_id})
    doc = get_document_by_id(cid)
    if doc is None:
        return json.dumps({"error": "not_found", "chunk_id": cid})
    return doc["text"]
