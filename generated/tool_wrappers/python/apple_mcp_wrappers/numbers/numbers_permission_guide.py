from __future__ import annotations

from typing import Any

from .client import MCPToolCaller, call_tool_json


async def numbers_permission_guide(
    client: MCPToolCaller
) -> Any:
    """Numbers Permission Guide

    Explain the macOS permission Apple Numbers automation needs.

    Example:
        await numbers_permission_guide(client)
    """
    arguments = {

    }
    payload = {key: value for key, value in arguments.items() if value is not None}
    return await call_tool_json(client, "numbers_permission_guide", payload)
