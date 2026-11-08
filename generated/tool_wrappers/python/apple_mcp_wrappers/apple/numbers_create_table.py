from __future__ import annotations

from typing import Any

from .client import MCPToolCaller, call_tool_json


async def numbers_create_table(
    client: MCPToolCaller,
    document_id: str,
    sheet_name: str,
    table_name: str,
    rows: int,
    columns: int
) -> Any:
    """Create Numbers Table

    Add a new empty table (no header or footer rows) to a sheet. Rejects a duplicate table name. May autosave and sync.

    Example:
        await numbers_create_table(client, document_id='example_document_id', sheet_name='example_sheet_name', table_name='example_table_name', rows=1, columns=1)
    """
    arguments = {
        "document_id": document_id,
        "sheet_name": sheet_name,
        "table_name": table_name,
        "rows": rows,
        "columns": columns,
    }
    payload = {key: value for key, value in arguments.items() if value is not None}
    return await call_tool_json(client, "numbers_create_table", payload)
