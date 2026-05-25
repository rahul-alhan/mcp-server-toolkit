"""Reusable prompt templates exposed to MCP clients."""
from __future__ import annotations

CITE_WITH_SOURCES = """Answer the user's question using only the knowledge-base context.
Rules:
1. Cite every factual claim inline with [source: <filename>].
2. If the context is insufficient, say "Insufficient context."
3. Do not invent policies, dates, or thresholds.

Question: {question}"""

COMPARE_DOCUMENTS = """Compare the two documents below side-by-side.
Highlight:
- where they agree
- where they conflict
- gaps that exist in only one

Document A (chunk_id={a_id}):
{a_text}

Document B (chunk_id={b_id}):
{b_text}"""
