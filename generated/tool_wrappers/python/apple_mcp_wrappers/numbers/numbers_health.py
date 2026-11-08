from __future__ import annotations

from typing import Any

from .client import MCPToolCaller, call_tool_json


async def numbers_health(
    client: MCPToolCaller
) -> Any:
    """Numbers Health

    Report the active Apple Numbers MCP configuration.

    Example:
        await numbers_health(client)
    """
    arguments = {

    }
    payload = {key: value for key, value in arguments.items() if value is not None}
    return await call_tool_json(client, "numbers_health", payload)
