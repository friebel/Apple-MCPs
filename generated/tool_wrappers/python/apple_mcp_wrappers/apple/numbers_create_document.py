from __future__ import annotations

from typing import Any

from .client import MCPToolCaller, call_tool_json


async def numbers_create_document(
    client: MCPToolCaller,
    template_name: str | None = None
) -> Any:
    """Create Numbers Document

    Create a new, unsaved Numbers spreadsheet, optionally from a named template (for example Blank). Save it with numbers_save_document. A new document holds a default table of about 22 rows and 7 columns.

    Example:
        await numbers_create_document(client, template_name='example_template_name')
    """
    arguments = {
        "template_name": template_name,
    }
    payload = {key: value for key, value in arguments.items() if value is not None}
    return await call_tool_json(client, "numbers_create_document", payload)
