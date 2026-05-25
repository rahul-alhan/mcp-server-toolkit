"""Validation tests — don't hit the LLM or vector store."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from mcp_server.tools import SearchInput


def test_search_input_caps_query_length():
    with pytest.raises(ValidationError):
        SearchInput(query="x" * 5000)


def test_search_input_bounds_top_k():
    with pytest.raises(ValidationError):
        SearchInput(query="ok", top_k=99)


def test_search_input_alpha_range():
    with pytest.raises(ValidationError):
        SearchInput(query="ok", alpha=1.5)
    SearchInput(query="ok", alpha=0.0)
    SearchInput(query="ok", alpha=1.0)
