"""
Long-lived MCP client connection, shared across every request.

The FastAPI app spawns the OUTTHERE MCP server as a subprocess ONCE at
startup and keeps a single ClientSession open for the process lifetime,
rather than paying subprocess-startup cost (and losing in-memory
business_store state) on every request. Every REST endpoint and the
agent workflow route their work through `call_tool()` here, so the MCP
server is genuinely the one place business logic executes -- FastAPI is
just transport.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_session: ClientSession | None = None
_stack: AsyncExitStack | None = None
_lock = asyncio.Lock()

# Tools whose Python return type is a list -- FastMCP serializes a list
# return as one text content block PER ITEM (not one JSON array block), so
# these must always be reassembled into a list even when there's 0 or 1
# item, rather than inferring shape from the block count.
LIST_RESULT_TOOLS = {"search_creators", "rank_creators", "search_real_creators", "search_youtube_creators"}


def _server_params() -> StdioServerParameters:
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "backend.mcp.server"],
        cwd=project_root,
        env=dict(os.environ),
    )


async def startup() -> None:
    global _session, _stack
    _stack = AsyncExitStack()
    read, write = await _stack.enter_async_context(stdio_client(_server_params()))
    _session = await _stack.enter_async_context(ClientSession(read, write))
    await _session.initialize()


async def shutdown() -> None:
    global _session, _stack
    if _stack is not None:
        await _stack.aclose()
    _session = None
    _stack = None


def get_session() -> ClientSession:
    if _session is None:
        raise RuntimeError("MCP client session not started -- call client_manager.startup() first")
    return _session


async def call_tool(name: str, args: dict) -> tuple[Any, bool]:
    """Call an MCP tool by name and return (parsed_result, is_error).

    Parsed as JSON when possible (every OUTTHERE tool returns JSON-able
    dict/list results); falls back to raw text otherwise.
    """
    session = get_session()
    async with _lock:
        result = await session.call_tool(name, args)

    # FastMCP serializes a single dict/str return as ONE text block, but a
    # list return (e.g. search_creators, rank_creators) gets serialized as
    # one text block PER LIST ITEM rather than a single JSON array -- so a
    # multi-block result is reassembled into a list here.
    text_blocks = [block.text for block in result.content if getattr(block, "type", None) == "text"]

    def _decode(text: str) -> Any:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    if name in LIST_RESULT_TOOLS:
        parsed: Any = [_decode(t) for t in text_blocks]
    elif not text_blocks:
        parsed = {}
    else:
        parsed = _decode(text_blocks[0])

    return parsed, bool(getattr(result, "isError", False))


async def list_tools():
    session = get_session()
    result = await session.list_tools()
    return result.tools
