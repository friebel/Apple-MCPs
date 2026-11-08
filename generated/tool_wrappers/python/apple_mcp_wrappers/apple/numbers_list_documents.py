from __future__ import annotations

from typing import Any

from .client import MCPToolCaller, call_tool_json


async def numbers_list_documents(
    client: MCPToolCaller
) -> Any:
    """List Numbers Documents

    List the spreadsheets currently open in Numbers. Does not launch Numbers.

    Example:
        await numbers_list_documents(client)
    """
    arguments = {

    }
    payload = {key: value for key, value in arguments.items() if value is not None}
    return await call_tool_json(client, "numbers_list_documents", payload)
