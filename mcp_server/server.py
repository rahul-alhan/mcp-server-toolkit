"""FastMCP application — stdio and HTTP/SSE transports."""
from __future__ import annotations

import argparse
import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

from .prompts import CITE_WITH_SOURCES, COMPARE_DOCUMENTS
from .resources import resource_collection, resource_collections, resource_document
from .tools import (
    tool_get_document_by_id,
    tool_list_collections,
    tool_search_knowledge_base,
    tool_summarize_document,
)

# CRITICAL: never write to stdout on stdio transport — it corrupts JSON-RPC frames.
logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mcp-server-toolkit")

mcp = FastMCP("kb-toolkit")


# ---- tools ----------------------------------------------------------

@mcp.tool()
def search_knowledge_base(query: str, top_k: int = 4, alpha: float = 0.5) -> list[dict]:
    """Hybrid (dense + BM25) search over the knowledge base. Returns top_k chunks
    with source citations. alpha=1.0 is pure dense, 0.0 is pure BM25."""
    return tool_search_knowledge_base(query, top_k, alpha)


@mcp.tool()
def get_document_by_id(chunk_id: int) -> dict:
    """Fetch a single document chunk by its chunk_id."""
    return tool_get_document_by_id(chunk_id)


@mcp.tool()
def list_collections() -> list[dict]:
    """List the knowledge-base collections mounted on this server."""
    return tool_list_collections()


@mcp.tool()
def summarize_document(chunk_id: int) -> dict:
    """Return the document text and a summarization directive for the client LLM."""
    return tool_summarize_document(chunk_id)


# ---- resources ------------------------------------------------------

@mcp.resource("kb://collections")
def res_collections() -> str:
    return resource_collections()


@mcp.resource("kb://collection/{name}")
def res_collection(name: str) -> str:
    return resource_collection(name)


@mcp.resource("kb://document/{chunk_id}")
def res_document(chunk_id: str) -> str:
    return resource_document(chunk_id)


# ---- prompts --------------------------------------------------------

@mcp.prompt()
def cite_with_sources(question: str) -> str:
    return CITE_WITH_SOURCES.format(question=question)


@mcp.prompt()
def compare_documents(a_id: int, b_id: int) -> str:
    # tool_get_document_by_id always returns a truthy dict — on miss it returns
    # {"error": "not_found", "chunk_id": ...} which has no "text" key, so the
    # old `or {...}` fallback never fired and we'd KeyError. Pull "text" defensively.
    a = tool_get_document_by_id(a_id)
    b = tool_get_document_by_id(b_id)
    a_text = a["text"] if "text" in a else "<not found>"
    b_text = b["text"] if "text" in b else "<not found>"
    return COMPARE_DOCUMENTS.format(a_id=a_id, b_id=b_id, a_text=a_text, b_text=b_text)


# ---- entry point ----------------------------------------------------

def _run_http_with_bearer_auth(port: int, bind: str = "127.0.0.1") -> None:
    """Wrap the SSE app in BearerAuthMiddleware and serve over uvicorn.

    Binds to loopback (127.0.0.1) by default. Pass a different bind address
    (e.g. "0.0.0.0") only when you really want the server reachable on other
    interfaces — that path also emits a stderr warning.
    """
    import uvicorn
    from starlette.middleware import Middleware

    from .auth import BearerAuthMiddleware

    expected = os.getenv("MCP_AUTH_TOKEN")
    if not expected:
        raise SystemExit(
            "MCP_AUTH_TOKEN env var is required for HTTP transport. "
            "Set it or use --transport stdio."
        )

    if bind != "127.0.0.1":
        log.warning(
            "HTTP server binding to %s — reachable on non-loopback interfaces. "
            "Ensure MCP_AUTH_TOKEN is strong and the port is firewalled.",
            bind,
        )

    app = mcp.sse_app()
    app.user_middleware.insert(
        0, Middleware(BearerAuthMiddleware, expected_token=expected)
    )
    app.middleware_stack = app.build_middleware_stack()
    uvicorn.run(app, host=bind, port=port, log_level="info")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument(
        "--bind",
        default="127.0.0.1",
        help=(
            "HTTP bind address (default 127.0.0.1 — loopback only). "
            "Set to 0.0.0.0 to expose on all interfaces; a stderr warning will be logged."
        ),
    )
    args = p.parse_args()

    log.info("Starting kb-toolkit MCP server (transport=%s)", args.transport)
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        _run_http_with_bearer_auth(args.port, bind=args.bind)


if __name__ == "__main__":
    main()
