from __future__ import annotations

from typing import Any

from .client import MCPToolCaller, call_tool_json


async def numbers_add_columns(
    client: MCPToolCaller,
    document_id: str,
    sheet_name: str,
    table_name: str,
    count: int | None = None,
    after_column: int | None = None
) -> Any:
    """Add Numbers Columns

    Insert empty columns into a table (at most 100 per call). Columns go after after_column (1-based; 0 inserts before the first column); omit it to append at the end.

    Example:
        await numbers_add_columns(client, document_id='example_document_id', sheet_name='example_sheet_name', table_name='example_table_name')
    """
    arguments = {
        "document_id": document_id,
        "sheet_name": sheet_name,
        "table_name": table_name,
        "count": count,
        "after_column": after_column,
    }
    payload = {key: value for key, value in arguments.items() if value is not None}
    return await call_tool_json(client, "numbers_add_columns", payload)
