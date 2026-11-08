from __future__ import annotations

from typing import Any

from .client import MCPToolCaller, call_tool_json


async def numbers_write_range(
    client: MCPToolCaller,
    document_id: str,
    sheet_name: str,
    table_name: str,
    values: list[Any],
    start_row: int | None = None,
    start_column: int | None = None,
    allow_formulas: bool | None = None,
    as_text: bool | None = None
) -> Any:
    """Write Numbers Range

    Write a rectangular grid of values into existing table cells (at most 2000 cells). null clears a cell. Strings starting with '=' are formulas and need allow_formulas=true; true/false become checkbox cells. Writing into a merged range silently un-merges it, and overwriting a formula cell with a literal breaks the sheet, so read the range first. Bounds are checked first; an application failure can leave a partial write. May autosave and sync.

    Example:
        await numbers_write_range(client, document_id='example_document_id', sheet_name='example_sheet_name', table_name='example_table_name', values=[])
    """
    arguments = {
        "document_id": document_id,
        "sheet_name": sheet_name,
        "table_name": table_name,
        "values": values,
        "start_row": start_row,
        "start_column": start_column,
        "allow_formulas": allow_formulas,
        "as_text": as_text,
    }
    payload = {key: value for key, value in arguments.items() if value is not None}
    return await call_tool_json(client, "numbers_write_range", payload)
