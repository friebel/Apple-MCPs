from __future__ import annotations

from typing import Any

from .client import MCPToolCaller, call_tool_json


async def numbers_set_format(
    client: MCPToolCaller,
    document_id: str,
    sheet_name: str,
    table_name: str,
    start_row: int,
    start_column: int,
    rows: int | None = None,
    columns: int | None = None,
    cell_format: str | None = None,
    alignment: str | None = None
) -> Any:
    """Format Numbers Cells

    Set the cell format and/or horizontal alignment of a rectangular range (at most 2000 cells). Only the format kinds Numbers offers are accepted; decimal places and the currency cannot be set (currency is always the system currency).

    Example:
        await numbers_set_format(client, document_id='example_document_id', sheet_name='example_sheet_name', table_name='example_table_name', start_row=1, start_column=1)
    """
    arguments = {
        "document_id": document_id,
        "sheet_name": sheet_name,
        "table_name": table_name,
        "start_row": start_row,
        "start_column": start_column,
        "rows": rows,
        "columns": columns,
        "cell_format": cell_format,
        "alignment": alignment,
    }
    payload = {key: value for key, value in arguments.items() if value is not None}
    return await call_tool_json(client, "numbers_set_format", payload)
