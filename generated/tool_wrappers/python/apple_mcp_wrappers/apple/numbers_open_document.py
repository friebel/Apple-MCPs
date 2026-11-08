from __future__ import annotations

from typing import Any

from .client import MCPToolCaller, call_tool_json


async def numbers_open_document(
    client: MCPToolCaller,
    path: str
) -> Any:
    """Open Numbers Document

    Open a .numbers, .xlsx, .xls, .csv or .tsv file from an allowed folder in Numbers. Launches Numbers if needed.

    Example:
        await numbers_open_document(client, path='/path/to/item')
    """
    arguments = {
        "path": path,
    }
    payload = {key: value for key, value in arguments.items() if value is not None}
    return await call_tool_json(client, "numbers_open_document", payload)
