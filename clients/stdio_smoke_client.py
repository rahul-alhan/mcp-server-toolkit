"""Minimal stdio client — verifies tools/resources without an LLM in the loop."""
from __future__ import annotations

import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def smoke():
    params = StdioServerParameters(
        command="python",
        args=["-m", "mcp_server.server", "--transport", "stdio"],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Tools:", [t.name for t in tools.tools])

            res = await session.list_resources()
            print("Resources:", [r.uri for r in res.resources])

            result = await session.call_tool(
                "search_knowledge_base",
                arguments={"query": "incident severity levels", "top_k": 3},
            )
            print("\nsearch_knowledge_base →")
            for item in result.content:
                if hasattr(item, "text"):
                    print(" ", item.text[:200])


if __name__ == "__main__":
    asyncio.run(smoke())
