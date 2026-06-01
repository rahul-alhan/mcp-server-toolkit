# MCP Server Toolkit — Knowledge Base over Model Context Protocol

Production-style **Model Context Protocol (MCP) server** that exposes a RAG knowledge base to MCP-compatible clients (Claude Desktop, Cursor, Continue) as both **tools** and **resources**. Ships in two transports: **stdio** (for desktop integrations) and **HTTP/SSE** (for remote/team use).

> Plugs directly into the retrieval layer from [`rag-pipeline-demo`](https://github.com/rahul-alhan/rag-pipeline-demo) — same chunking, same vector store, just re-exposed as MCP primitives.

---

## Why MCP?

MCP is the emerging USB-C-for-AI standard (Anthropic, 2024 → widely adopted through 2025). Before MCP, every agent-to-system integration was a bespoke tool/function definition. After MCP, an enterprise stands up *one* MCP server and *any* MCP-compatible client (Claude Desktop, Cursor, custom LangGraph agent) gets typed, validated access.

This repo is the pattern I'd reach for at the enterprise scale: a thin MCP layer over an existing retrieval stack, so the agent runtime is decoupled from the knowledge layer.

---

## What this server exposes

### Tools (callable by the agent)

| Tool | Purpose |
|---|---|
| `search_knowledge_base` | dense + keyword hybrid search over the corpus; returns top-k chunks with citations |
| `get_document_by_id` | fetch a specific document's full text by ID |
| `summarize_document` | LLM-side summary trigger — the *client's* LLM summarizes, server provides text |
| `list_collections` | enumerate which knowledge bases are mounted |

### Resources (readable by the agent)

| Resource URI | What it is |
|---|---|
| `kb://collections` | catalog of mounted collections |
| `kb://collection/{name}` | metadata + document count |
| `kb://document/{id}` | full text of a single document |

### Prompts (templates the client can invoke)

| Prompt | What it does |
|---|---|
| `cite_with_sources` | a "answer-with-citations" template injected into the user's chat |
| `compare_documents` | side-by-side comparison template, slots two document IDs |

---

## Architecture

```
   ┌────────────────────────┐
   │  Claude Desktop /      │       stdio JSON-RPC
   │  Cursor / LangGraph    │ ──────────────────────┐
   └────────────────────────┘                        │
                                                     ▼
                                         ┌────────────────────────┐
                                         │  mcp_server/server.py  │
                                         │   FastMCP application  │
                                         └───────────┬────────────┘
                                                     │
                            ┌────────────────────────┼─────────────────────┐
                            ▼                        ▼                     ▼
                       tools/                   resources/             prompts/
                  search_knowledge_base    kb://collections      cite_with_sources
                  get_document_by_id       kb://document/{id}    compare_documents
                            │                        │
                            └─────────┬──────────────┘
                                      ▼
                              ┌──────────────────┐
                              │   kb/retriever   │  (Chroma + OpenAI embeddings,
                              │                  │   shared with rag-pipeline-demo)
                              └──────────────────┘
```

---

## Quickstart

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...

# 1. Build the knowledge base index (uses sample docs)
python -m kb.build_index --docs docs/ --persist .chroma/

# 2. Run as a stdio server (for Claude Desktop)
python -m mcp_server.server --transport stdio

# 3. Or run as an HTTP/SSE server (for remote/team use)
#    Defaults to --bind 127.0.0.1 (loopback only). To expose on the LAN, pass
#    --bind 0.0.0.0 — a stderr warning will be logged and MCP_AUTH_TOKEN must be set.
export MCP_AUTH_TOKEN=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
python -m mcp_server.server --transport http --port 8765
# python -m mcp_server.server --transport http --port 8765 --bind 0.0.0.0   # LAN-exposed

# 4. Inspect tools/resources interactively without an LLM
npx @modelcontextprotocol/inspector python -m mcp_server.server
```

### Wire it into Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "kb-toolkit": {
      "command": "python",
      "args": ["-m", "mcp_server.server", "--transport", "stdio"],
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "KB_CHROMA_DIR": "/absolute/path/to/.chroma"
      }
    }
  }
}
```

Restart Claude Desktop. The 🔌 icon should show `kb-toolkit` connected.

---

## Repository Layout

```
mcp-server-toolkit/
├── README.md
├── requirements.txt
├── LICENSE
├── .gitignore
├── .env.example
├── docs/                          # sample corpus
│   ├── policy.md
│   └── handbook.md
├── kb/
│   ├── __init__.py
│   ├── build_index.py             # chunk + embed + persist
│   └── retriever.py               # hybrid retrieval
├── mcp_server/
│   ├── __init__.py
│   ├── server.py                  # FastMCP application + transport selector
│   ├── tools.py                   # tool implementations
│   ├── resources.py               # resource handlers
│   └── prompts.py                 # prompt templates
├── clients/
│   ├── stdio_smoke_client.py      # minimal sanity-check client
│   └── claude_desktop_config.example.json
└── tests/
    └── test_tools.py
```

---

## Design Choices

| Decision | Rationale |
|---|---|
| **FastMCP** | Official Python SDK — same DX as FastAPI; transport-agnostic |
| **Hybrid search (BM25 + dense)** | Pure dense misses keyword-precise queries (model IDs, dates); pure BM25 misses paraphrases |
| **Cite-by-default tool output** | Every result includes `source` field; the client LLM is steered to surface it |
| **No streaming on tools** | MCP tools are request/response; streaming belongs to the chat layer, not the tool layer |
| **Resources are read-only** | Mutating MCP servers are a 2026 anti-pattern — keep writes behind an explicit tool |
| **stderr-only logging on stdio** | stdout corrupts JSON-RPC frames; this is the #1 silent failure mode for MCP servers |

---

## Security Notes

- The server **does not execute arbitrary code** — tools are an explicit whitelist
- IDs in `get_document_by_id` are validated against the collection — no path traversal
- HTTP transport requires `MCP_AUTH_TOKEN` env var (bearer-token auth) and uses `hmac.compare_digest` for constant-time token comparison; stdio is trusted by virtue of being a child process
- HTTP transport binds to `127.0.0.1` by default — pass `--bind 0.0.0.0` to expose on other interfaces (warning logged to stderr)
- Inputs are size-capped (`max_query_chars=2000`) to prevent prompt-injection-via-resource

---

## Production Notes

In a real deployment this server would be packaged as:
- A **Docker image** behind an internal ALB with **IAM-authenticated** HTTP transport
- Knowledge-base index swapped from Chroma → **OpenSearch kNN** with hybrid (dense + BM25) ranking native
- **CloudWatch** structured logs of every tool call (request hash, latency, top doc IDs, client identity)
- **Tool versioning** via a `schema_version` field in the tool metadata, so client compatibility is explicit

---

## License

MIT
