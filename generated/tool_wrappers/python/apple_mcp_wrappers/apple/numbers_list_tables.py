from __future__ import annotations

from typing import Any

from .client import MCPToolCaller, call_tool_json


async def numbers_list_tables(
    client: MCPToolCaller,
    document_id: str,
    sheet_name: str
) -> Any:
    """List Numbers Tables

    List the tables of a sheet with their row, column, header and footer counts.

    Example:
        await numbers_list_tables(client, document_id='example_document_id', sheet_name='example_sheet_name')
    """
    arguments = {
        "document_id": document_id,
        "sheet_name": sheet_name,
    }
    payload = {key: value for key, value in arguments.items() if value is not None}
    return await call_tool_json(client, "numbers_list_tables", payload)
