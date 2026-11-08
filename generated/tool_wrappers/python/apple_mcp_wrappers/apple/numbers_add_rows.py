from __future__ import annotations

from typing import Any

from .client import MCPToolCaller, call_tool_json


async def numbers_add_rows(
    client: MCPToolCaller,
    document_id: str,
    sheet_name: str,
    table_name: str,
    count: int | None = None,
    after_row: int | None = None
) -> Any:
    """Add Numbers Rows

    Insert empty rows into a table (at most 100 per call). Rows go after after_row (1-based; 0 inserts before the first row); omit it to append at the end.

    Example:
        await numbers_add_rows(client, document_id='example_document_id', sheet_name='example_sheet_name', table_name='example_table_name')
    """
    arguments = {
        "document_id": document_id,
        "sheet_name": sheet_name,
        "table_name": table_name,
        "count": count,
        "after_row": after_row,
    }
    payload = {key: value for key, value in arguments.items() if value is not None}
    return await call_tool_json(client, "numbers_add_rows", payload)
