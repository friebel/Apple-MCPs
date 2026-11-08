from __future__ import annotations

from typing import Any

from .client import MCPToolCaller, call_tool_json


async def numbers_delete_rows(
    client: MCPToolCaller,
    document_id: str,
    sheet_name: str,
    table_name: str,
    start_row: int,
    count: int | None = None
) -> Any:
    """Delete Numbers Rows

    Delete rows from a table, last row first, one at a time (Numbers range deletes are unreliable). Rows shift up, so list the table again afterwards. A table keeps at least one row.

    Example:
        await numbers_delete_rows(client, document_id='example_document_id', sheet_name='example_sheet_name', table_name='example_table_name', start_row=1)
    """
    arguments = {
        "document_id": document_id,
        "sheet_name": sheet_name,
        "table_name": table_name,
        "start_row": start_row,
        "count": count,
    }
    payload = {key: value for key, value in arguments.items() if value is not None}
    return await call_tool_json(client, "numbers_delete_rows", payload)
