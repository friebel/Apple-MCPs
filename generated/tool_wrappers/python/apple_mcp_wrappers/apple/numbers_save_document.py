from __future__ import annotations

from typing import Any

from .client import MCPToolCaller, call_tool_json


async def numbers_save_document(
    client: MCPToolCaller,
    document_id: str,
    path: str,
    overwrite: bool | None = None
) -> Any:
    """Save Numbers Document

    Save a document as a .numbers file inside the allowed folders. Refuses to replace an existing file unless overwrite=true.

    Example:
        await numbers_save_document(client, document_id='example_document_id', path='/path/to/item')
    """
    arguments = {
        "document_id": document_id,
        "path": path,
        "overwrite": overwrite,
    }
    payload = {key: value for key, value in arguments.items() if value is not None}
    return await call_tool_json(client, "numbers_save_document", payload)
