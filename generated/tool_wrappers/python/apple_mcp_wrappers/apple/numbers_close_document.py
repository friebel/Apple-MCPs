from __future__ import annotations

from typing import Any

from .client import MCPToolCaller, call_tool_json


async def numbers_close_document(
    client: MCPToolCaller,
    document_id: str,
    discard: bool | None = None
) -> Any:
    """Close Numbers Document

    Close an open document. Refuses when it has unsaved changes or was never saved, unless discard=true (which throws the changes away).

    Example:
        await numbers_close_document(client, document_id='example_document_id', discard=False)
    """
    arguments = {
        "document_id": document_id,
        "discard": discard,
    }
    payload = {key: value for key, value in arguments.items() if value is not None}
    return await call_tool_json(client, "numbers_close_document", payload)
