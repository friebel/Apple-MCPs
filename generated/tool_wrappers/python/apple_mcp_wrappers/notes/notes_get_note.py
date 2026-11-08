from __future__ import annotations

from typing import Any

from .client import MCPToolCaller, call_tool_json


async def notes_get_note(
    client: MCPToolCaller,
    note_id: str,
    max_chars: int | None = None
) -> Any:
    """Get Note

    Fetch full details for an Apple Notes note by note_id.

    Example:
        await notes_get_note(client, note_id='example_note_id', max_chars=1)
    """
    arguments = {
        "note_id": note_id,
        "max_chars": max_chars,
    }
    payload = {key: value for key, value in arguments.items() if value is not None}
    return await call_tool_json(client, "notes_get_note", payload)
