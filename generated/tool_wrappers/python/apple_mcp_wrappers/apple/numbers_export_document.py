from __future__ import annotations

from typing import Any

from .client import MCPToolCaller, call_tool_json


async def numbers_export_document(
    client: MCPToolCaller,
    document_id: str,
    path: str,
    export_format: str,
    overwrite: bool | None = None
) -> Any:
    """Export Numbers Document

    Export an open Numbers document to PDF, Excel (xlsx) or CSV inside an allowed folder. Large exports can be slow.

    Example:
        await numbers_export_document(client, document_id='example_document_id', path='/path/to/item', export_format='pdf')
    """
    arguments = {
        "document_id": document_id,
        "path": path,
        "export_format": export_format,
        "overwrite": overwrite,
    }
    payload = {key: value for key, value in arguments.items() if value is not None}
    return await call_tool_json(client, "numbers_export_document", payload)
