from __future__ import annotations

from typing import Any

from .client import MCPToolCaller, call_tool_json


async def numbers_list_sheets(
    client: MCPToolCaller,
    document_id: str
) -> Any:
    """List Numbers Sheets

    List the sheets of an open Numbers document with their table counts.

    Example:
        await numbers_list_sheets(client, document_id='example_document_id')
    """
    arguments = {
        "document_id": document_id,
    }
    payload = {key: value for key, value in arguments.items() if value is not None}
    return await call_tool_json(client, "numbers_list_sheets", payload)
