from typing import Literal

from pydantic import BaseModel, Field


class ToolError(BaseModel):
    error_code: str = Field(description="Stable machine-readable error code")
    message: str = Field(description="Human-readable error message")
    suggestion: str | None = Field(default=None, description="Suggested next step")


class ErrorResponse(BaseModel):
    ok: Literal[False] = False
    error: ToolError


class NumbersPermissionStatus(BaseModel):
    osascript_available: bool
    script_timeout_seconds: int
    allowed_roots: list[str]


class HealthResponse(BaseModel):
    ok: Literal[True] = True
    server_name: str
    version: str
    safety_mode: str
    safety_mode_warning: str | None = Field(default=None, description="Set when the configured safety value was invalid or blank and the server fell back to a safer mode")
    transport: str
    capabilities: list[str]
    permissions: NumbersPermissionStatus
    transport_support: list[str]


class DocumentInfo(BaseModel):
    id: str = Field(description="Stable document id; pass it as document_id to every other tool")
    name: str
    path: str | None = Field(default=None, description="POSIX path once the document has been saved; None for an unsaved document")
    modified: bool = False
    sheet_count: int = 0


class SheetInfo(BaseModel):
    name: str
    table_count: int = 0


class TableInfo(BaseModel):
    name: str
    rows: int
    columns: int
    header_rows: int = 0
    header_columns: int = 0
    footer_rows: int = 0


class CellInfo(BaseModel):
    value: str | int | float | bool | None = None
    formatted_value: str = ""
    formula: str = ""
    format: str | None = Field(default=None, description="Cell format such as automatic, number, text, date and time or checkbox; None when Numbers does not report one")
    alignment: str | None = Field(default=None, description="Horizontal alignment; only present when include_style=true")


class DocumentListResponse(BaseModel):
    ok: Literal[True] = True
    documents: list[DocumentInfo]
    count: int
    application_running: bool = True


class DocumentResponse(BaseModel):
    ok: Literal[True] = True
    document: DocumentInfo


class SheetListResponse(BaseModel):
    ok: Literal[True] = True
    sheets: list[SheetInfo]
    count: int


class TableListResponse(BaseModel):
    ok: Literal[True] = True
    tables: list[TableInfo]
    count: int


class TableResponse(BaseModel):
    ok: Literal[True] = True
    table: TableInfo


class RangeResponse(BaseModel):
    ok: Literal[True] = True
    start_row: int
    start_column: int
    cells: list[list[CellInfo]]
    truncated_text_limit: int = Field(description="Strings and formulas longer than this many characters are cut")


class WriteRangeResponse(BaseModel):
    ok: Literal[True] = True
    written_cells: int


class FormatRangeResponse(BaseModel):
    ok: Literal[True] = True
    formatted_cells: int


class ExportResponse(BaseModel):
    ok: Literal[True] = True
    path: str
    format: str
