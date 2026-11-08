from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from apple_numbers_mcp.config import load_settings
from apple_numbers_mcp.models import CellInfo, DocumentInfo, SheetInfo, TableInfo

MAX_READ_CELLS = 200
MAX_WRITE_CELLS = 2000
MAX_NEW_TABLE_CELLS = 10000
OPEN_EXTENSIONS = frozenset({".numbers", ".xls", ".xlsx", ".csv", ".tsv"})
EXPORT_FORMATS = frozenset({"pdf", "xlsx", "csv"})
MAX_FORMAT_CELLS = 2000
MAX_STRUCTURE_CHANGE = 100
CELL_FORMATS = frozenset(
    {"automatic", "checkbox", "currency", "date and time", "duration", "fraction", "number", "numeral system", "percent", "pop up menu", "rating", "scientific", "slider", "stepper", "text"}
)
ALIGNMENTS = frozenset({"auto align", "center", "justify", "left", "right"})

CellValue = str | int | float | bool | None


class NumbersBridgeError(Exception):
    def __init__(self, error_code: str, message: str, suggestion: str | None = None) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.suggestion = suggestion


class NumbersBridge:
    def __init__(
        self,
        script_path: Path | None = None,
        timeout_seconds: int | None = None,
        allowed_roots: tuple[Path, ...] | None = None,
    ) -> None:
        settings = load_settings()
        self.script_path = script_path or settings.script_path
        self.timeout_seconds = timeout_seconds or settings.script_timeout_seconds
        roots = settings.allowed_roots if allowed_roots is None else allowed_roots
        self.allowed_roots = tuple(path.expanduser().resolve(strict=False) for path in roots)

    def osascript_available(self) -> bool:
        return shutil.which("osascript") is not None

    # -- documents -----------------------------------------------------------

    def list_documents(self) -> tuple[list[DocumentInfo], bool]:
        result = self._run({"operation": "list_documents"})
        documents = [DocumentInfo.model_validate(item) for item in self._items(result.get("documents"))]
        return documents, bool(result.get("application_running", True))

    def open_document(self, path: str) -> DocumentInfo:
        resolved = self._resolve_allowed(path)
        if resolved.suffix.lower() not in OPEN_EXTENSIONS:
            raise NumbersBridgeError(
                "UNSUPPORTED_FILE_TYPE",
                f"Numbers can open only {', '.join(sorted(OPEN_EXTENSIONS))} files here (got '{resolved.suffix or 'no extension'}').",
                "Pick a .numbers, .xlsx, .xls, .csv or .tsv file.",
            )
        if not resolved.exists():
            raise NumbersBridgeError("FILE_NOT_FOUND", f"No file exists at '{resolved}'.", "Check the path with the Files server.")
        result = self._run({"operation": "open", "path": str(resolved)})
        return DocumentInfo.model_validate(self._object(result.get("document"), "open"))

    def export_document(self, document_id: str, path: str, export_format: str, overwrite: bool = False) -> str:
        if export_format not in EXPORT_FORMATS:
            raise NumbersBridgeError("INVALID_INPUT", f"Unsupported export format '{export_format}'.", "Use pdf, xlsx or csv.")
        resolved = self._resolve_allowed(path)
        if resolved.suffix.lower() != f".{export_format}":
            raise NumbersBridgeError("INVALID_INPUT", f"The destination must end in .{export_format}.", "Match the file extension to the export format.")
        if not resolved.parent.is_dir():
            raise NumbersBridgeError("INVALID_INPUT", f"The folder '{resolved.parent}' does not exist.", "Create the folder first.")
        if resolved.exists() and not overwrite:
            raise NumbersBridgeError("FILE_EXISTS", f"'{resolved}' already exists.", "Pass overwrite=true to replace it, or choose another path.")
        self._run({"operation": "export", "document_id": document_id, "path": str(resolved), "format": export_format})
        return str(resolved)

    def create_document(self, template_name: str | None = None) -> DocumentInfo:
        result = self._run({"operation": "create", "template_name": template_name})
        return DocumentInfo.model_validate(self._object(result.get("document"), "create"))

    def save_document(self, document_id: str, path: str, overwrite: bool = False) -> DocumentInfo:
        resolved = self._resolve_allowed(path)
        if resolved.suffix.lower() != ".numbers":
            raise NumbersBridgeError("INVALID_INPUT", "A saved Numbers document must end in .numbers.", "Use numbers_export_document for pdf, xlsx or csv.")
        if not resolved.parent.is_dir():
            raise NumbersBridgeError("INVALID_INPUT", f"The folder '{resolved.parent}' does not exist.", "Create the folder first.")
        if resolved.exists() and not overwrite:
            raise NumbersBridgeError("FILE_EXISTS", f"'{resolved}' already exists.", "Pass overwrite=true to replace it, or choose another path.")
        result = self._run({"operation": "save", "document_id": document_id, "path": str(resolved)})
        return DocumentInfo.model_validate(self._object(result.get("document"), "save"))

    def close_document(self, document_id: str, discard: bool = False) -> DocumentInfo:
        result = self._run({"operation": "close", "document_id": document_id, "discard": discard})
        return DocumentInfo.model_validate(self._object(result.get("document"), "close"))

    # -- sheets and tables ---------------------------------------------------

    def list_sheets(self, document_id: str) -> list[SheetInfo]:
        result = self._run({"operation": "list_sheets", "document_id": document_id})
        return [SheetInfo.model_validate(item) for item in self._items(result.get("sheets"))]

    def list_tables(self, document_id: str, sheet_name: str) -> list[TableInfo]:
        result = self._run({"operation": "list_tables", "document_id": document_id, "sheet_name": sheet_name})
        return [TableInfo.model_validate(item) for item in self._items(result.get("tables"))]

    def create_table(self, document_id: str, sheet_name: str, table_name: str, rows: int, columns: int) -> TableInfo:
        if rows < 1 or columns < 1 or rows * columns > MAX_NEW_TABLE_CELLS:
            raise NumbersBridgeError("INVALID_INPUT", f"A new table needs at least 1 row and 1 column and at most {MAX_NEW_TABLE_CELLS} cells.", "Create a smaller table.")
        result = self._run({"operation": "create_table", "document_id": document_id, "sheet_name": sheet_name, "table_name": table_name, "rows": rows, "columns": columns})
        return TableInfo.model_validate(self._object(result.get("table"), "create_table"))

    def add_rows(self, document_id: str, sheet_name: str, table_name: str, count: int, after_row: int | None = None) -> TableInfo:
        return self._change_structure("add_rows", document_id, sheet_name, table_name, count=count, after=after_row)

    def add_columns(self, document_id: str, sheet_name: str, table_name: str, count: int, after_column: int | None = None) -> TableInfo:
        return self._change_structure("add_columns", document_id, sheet_name, table_name, count=count, after=after_column)

    def delete_rows(self, document_id: str, sheet_name: str, table_name: str, start_row: int, count: int = 1) -> TableInfo:
        return self._change_structure("delete_rows", document_id, sheet_name, table_name, count=count, start=start_row)

    def delete_columns(self, document_id: str, sheet_name: str, table_name: str, start_column: int, count: int = 1) -> TableInfo:
        return self._change_structure("delete_columns", document_id, sheet_name, table_name, count=count, start=start_column)

    def _change_structure(self, operation: str, document_id: str, sheet_name: str, table_name: str, *, count: int, after: int | None = None, start: int | None = None) -> TableInfo:
        if count < 1 or count > MAX_STRUCTURE_CHANGE:
            raise NumbersBridgeError("INVALID_INPUT", f"count must be between 1 and {MAX_STRUCTURE_CHANGE}.", "Change the table in smaller steps.")
        if (after is not None and after < 0) or (start is not None and start < 1):
            raise NumbersBridgeError("INVALID_INPUT", "Positions are 1-based (use after=0 to insert before the first row or column).", "Use numbers_list_tables to see the table size.")
        payload: dict[str, object] = {"operation": operation, "document_id": document_id, "sheet_name": sheet_name, "table_name": table_name, "count": count}
        if after is not None:
            payload["after"] = after
        if start is not None:
            payload["start"] = start
        result = self._run(payload)
        return TableInfo.model_validate(self._object(result.get("table"), operation))

    def set_format(
        self,
        document_id: str,
        sheet_name: str,
        table_name: str,
        start_row: int,
        start_column: int,
        rows: int,
        columns: int,
        cell_format: str | None = None,
        alignment: str | None = None,
    ) -> int:
        self._check_position(start_row, start_column)
        if cell_format is None and alignment is None:
            raise NumbersBridgeError("INVALID_INPUT", "Provide cell_format and/or alignment.", "Say which format or alignment to apply.")
        if cell_format is not None and cell_format not in CELL_FORMATS:
            raise NumbersBridgeError("INVALID_INPUT", f"Unknown cell format '{cell_format}'.", f"Use one of: {', '.join(sorted(CELL_FORMATS))}.")
        if alignment is not None and alignment not in ALIGNMENTS:
            raise NumbersBridgeError("INVALID_INPUT", f"Unknown alignment '{alignment}'.", f"Use one of: {', '.join(sorted(ALIGNMENTS))}.")
        if rows < 1 or columns < 1 or rows * columns > MAX_FORMAT_CELLS:
            raise NumbersBridgeError("INVALID_INPUT", f"A format change covers at most {MAX_FORMAT_CELLS} cells.", "Format the table in smaller ranges.")
        result = self._run(
            {"operation": "set_format", "document_id": document_id, "sheet_name": sheet_name, "table_name": table_name, "start_row": start_row, "start_column": start_column, "rows": rows, "columns": columns, "format": cell_format, "alignment": alignment}
        )
        formatted = result.get("formatted_cells")
        return formatted if isinstance(formatted, int) else rows * columns

    def read_range(self, document_id: str, sheet_name: str, table_name: str, start_row: int, start_column: int, rows: int, columns: int, include_style: bool = False) -> list[list[CellInfo]]:
        self._check_position(start_row, start_column)
        if rows < 1 or columns < 1 or rows * columns > MAX_READ_CELLS:
            raise NumbersBridgeError("INVALID_INPUT", f"A read covers at most {MAX_READ_CELLS} cells and needs at least 1 row and 1 column.", "Read the table in smaller ranges.")
        result = self._run(
            {"operation": "read_range", "document_id": document_id, "sheet_name": sheet_name, "table_name": table_name, "start_row": start_row, "start_column": start_column, "rows": rows, "columns": columns, "include_style": include_style}
        )
        grid = result.get("cells")
        if not isinstance(grid, list):
            raise NumbersBridgeError("INVALID_SCRIPT_OUTPUT", "The Numbers script did not return a cell grid.", "Retry; if it persists, report the issue.")
        return [[CellInfo.model_validate(cell) for cell in self._items(line)] for line in grid]

    def write_range(
        self,
        document_id: str,
        sheet_name: str,
        table_name: str,
        start_row: int,
        start_column: int,
        values: list[list[CellValue]],
        allow_formulas: bool = False,
        as_text: bool = False,
    ) -> int:
        self._check_position(start_row, start_column)
        if not values or not values[0] or any(len(line) != len(values[0]) for line in values):
            raise NumbersBridgeError("INVALID_INPUT", "values must be a non-empty rectangular grid.", "Give every row the same number of columns.")
        cell_count = len(values) * len(values[0])
        if cell_count > MAX_WRITE_CELLS:
            raise NumbersBridgeError("INVALID_INPUT", f"A write covers at most {MAX_WRITE_CELLS} cells (got {cell_count}).", "Write the data in several smaller ranges.")
        if as_text and allow_formulas:
            raise NumbersBridgeError("INVALID_INPUT", "as_text and allow_formulas cannot be combined; a text cell never evaluates a formula.", "Pick one of the two options.")
        if not allow_formulas and not as_text:
            for line in values:
                for value in line:
                    if isinstance(value, str) and value.lstrip().startswith("="):
                        raise NumbersBridgeError("FORMULA_NOT_ALLOWED", "A value starts with '=' and would become a formula.", "Pass allow_formulas=true if formulas are intended.")
        result = self._run(
            {"operation": "write_range", "document_id": document_id, "sheet_name": sheet_name, "table_name": table_name, "start_row": start_row, "start_column": start_column, "values": values, "as_text": as_text}
        )
        written = result.get("written_cells")
        return written if isinstance(written, int) else cell_count

    # -- internals -------------------------------------------------------------

    def _check_position(self, start_row: int, start_column: int) -> None:
        if start_row < 1 or start_column < 1:
            raise NumbersBridgeError("INVALID_INPUT", "start_row and start_column are 1-based.", "Use 1 for the first row or column.")

    def _resolve_allowed(self, path: str) -> Path:
        candidate = Path(path).expanduser()
        if not candidate.is_absolute() or "\0" in path:
            raise NumbersBridgeError("INVALID_INPUT", "path must be an absolute file path.", "Pass a full path such as /Users/me/Documents/budget.numbers.")
        resolved = candidate.resolve(strict=False)
        if not any(resolved == root or root in resolved.parents for root in self.allowed_roots):
            raise NumbersBridgeError(
                "PATH_NOT_ALLOWED",
                f"'{resolved}' is outside the allowed folders.",
                "Set APPLE_NUMBERS_MCP_ALLOWED_ROOTS (or APPLE_FILES_MCP_ALLOWED_ROOTS) to include its folder.",
            )
        return resolved

    @staticmethod
    def _items(value: object) -> list[dict[str, object]]:
        return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []

    @staticmethod
    def _object(value: object, operation: str) -> dict[str, object]:
        if not isinstance(value, dict):
            raise NumbersBridgeError("INVALID_SCRIPT_OUTPUT", f"The Numbers {operation} script did not return the expected object.", "Retry; if it persists, report the issue.")
        return value

    def _run(self, payload: dict[str, object]) -> dict[str, object]:
        try:
            completed = subprocess.run(
                ["osascript", "-l", "JavaScript", str(self.script_path), json.dumps(payload)],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            raise NumbersBridgeError("OSASCRIPT_UNAVAILABLE", "osascript was not found; this server only runs on macOS.", "Run the server on a Mac.") from exc
        except subprocess.TimeoutExpired as exc:
            raise NumbersBridgeError(
                "SCRIPT_TIMEOUT",
                f"Numbers did not respond within {self.timeout_seconds} seconds; a write may be partly applied.",
                "Inspect the table with numbers_read_range before retrying a write.",
            ) from exc
        if completed.returncode != 0:
            raise self._map_failure(completed.stderr.strip() or completed.stdout.strip())
        try:
            envelope = json.loads(completed.stdout.strip() or "{}")
        except json.JSONDecodeError as exc:
            raise NumbersBridgeError("INVALID_SCRIPT_OUTPUT", "The Numbers script returned output that is not JSON.", "Retry; if it persists, report the issue.") from exc
        if not isinstance(envelope, dict) or not envelope.get("ok"):
            message = str(envelope.get("message", "unknown error")) if isinstance(envelope, dict) else "unknown error"
            raise self._map_failure(message)
        result = envelope.get("result")
        return result if isinstance(result, dict) else {}

    @staticmethod
    def _map_failure(message: str) -> NumbersBridgeError:
        lowered = message.lower()
        if "-1743" in message or "not authorized" in lowered or "not allowed" in lowered:
            return NumbersBridgeError(
                "PERMISSION_DENIED",
                "macOS blocked Automation access to Numbers.",
                "Allow this app to control Numbers in System Settings > Privacy & Security > Automation.",
            )
        if "unsaved changes" in lowered:
            return NumbersBridgeError("UNSAVED_CHANGES", message, "Save the document with numbers_save_document, or pass discard=true to throw the changes away.")
        if "not found" in lowered:
            return NumbersBridgeError("NOT_FOUND", message, "List documents, sheets and tables first to discover exact names.")
        if "ambiguous" in lowered:
            return NumbersBridgeError("AMBIGUOUS_NAME", message, "Rename the duplicates in Numbers so the name is unique.")
        if "not running" in lowered:
            return NumbersBridgeError("NUMBERS_NOT_RUNNING", message, "Open or create a document first.")
        if "exceeds table bounds" in lowered:
            return NumbersBridgeError("RANGE_OUT_OF_BOUNDS", message, "Call numbers_list_tables to see the table size.")
        if "must keep at least one" in lowered:
            return NumbersBridgeError("INVALID_INPUT", message, "Delete fewer rows or columns.")
        if "already exists" in lowered:
            return NumbersBridgeError("ALREADY_EXISTS", message, "Choose a different table name.")
        return NumbersBridgeError("NUMBERS_ERROR", message, "Check the document state in Numbers and retry.")
