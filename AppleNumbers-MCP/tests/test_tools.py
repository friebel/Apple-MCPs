import pytest
from apple_numbers_mcp import tools
from apple_numbers_mcp.config import load_settings
from apple_numbers_mcp.models import CellInfo, DocumentInfo, SheetInfo, TableInfo


class FakeBridge:
    allowed_roots = ()

    def osascript_available(self) -> bool:
        return True

    def list_documents(self):
        return [DocumentInfo(id="D1", name="Budget", path="/x/Budget.numbers", sheet_count=1)], True

    def list_sheets(self, document_id):
        return [SheetInfo(name="Sheet 1", table_count=1)]

    def list_tables(self, document_id, sheet_name):
        return [TableInfo(name="Table 1", rows=3, columns=2)]

    def read_range(self, *args, **kwargs):
        return [[CellInfo(value="a", formatted_value="a")]]

    def write_range(self, *args, **kwargs):
        return 4


@pytest.fixture(autouse=True)
def _settings(monkeypatch):
    monkeypatch.setenv("APPLE_NUMBERS_MCP_SAFETY_MODE", "full_access")
    load_settings.cache_clear()
    monkeypatch.setattr(tools, "_bridge", lambda: FakeBridge())
    yield
    load_settings.cache_clear()


def test_health_reports_capabilities() -> None:
    result = tools.numbers_health()

    assert result.ok is True
    assert "read_ranges" in result.capabilities


def test_list_tools_return_structured_payloads() -> None:
    assert tools.numbers_list_documents().count == 1
    assert tools.numbers_list_sheets(document_id="Budget").sheets[0].name == "Sheet 1"
    assert tools.numbers_list_tables(document_id="Budget", sheet_name="Sheet 1").tables[0].rows == 3
    assert tools.numbers_read_range(document_id="Budget", sheet_name="Sheet 1", table_name="Table 1").cells[0][0].value == "a"


def test_write_range_blocked_in_readonly_mode(monkeypatch) -> None:
    monkeypatch.setenv("APPLE_NUMBERS_MCP_SAFETY_MODE", "safe_readonly")
    load_settings.cache_clear()

    result = tools.numbers_write_range(document_id="Budget", sheet_name="Sheet 1", table_name="Table 1", values=[["a"]])

    assert result.ok is False
    assert result.error.error_code == "WRITE_BLOCKED"


def test_reads_allowed_in_readonly_mode(monkeypatch) -> None:
    monkeypatch.setenv("APPLE_NUMBERS_MCP_SAFETY_MODE", "safe_readonly")
    load_settings.cache_clear()

    assert tools.numbers_list_documents().ok is True


def test_invalid_safety_mode_falls_back_to_readonly(monkeypatch) -> None:
    monkeypatch.setenv("APPLE_NUMBERS_MCP_SAFETY_MODE", "bogus")
    load_settings.cache_clear()

    assert load_settings().safety_mode == "safe_readonly"
    assert tools.numbers_health().safety_mode_warning


def test_write_range_returns_written_count() -> None:
    result = tools.numbers_write_range(document_id="Budget", sheet_name="Sheet 1", table_name="Table 1", values=[["a", "b"], ["c", "d"]])

    assert result.ok is True
    assert result.written_cells == 4


def test_lifecycle_and_structure_tools_blocked_in_readonly_mode(monkeypatch) -> None:
    monkeypatch.setenv("APPLE_NUMBERS_MCP_SAFETY_MODE", "safe_readonly")
    load_settings.cache_clear()

    results = [
        tools.numbers_create_document(),
        tools.numbers_save_document(document_id="D1", path="/tmp/x.numbers"),
        tools.numbers_close_document(document_id="D1"),
        tools.numbers_add_rows(document_id="D1", sheet_name="S", table_name="T"),
        tools.numbers_delete_columns(document_id="D1", sheet_name="S", table_name="T", start_column=1),
        tools.numbers_set_format(document_id="D1", sheet_name="S", table_name="T", start_row=1, start_column=1, cell_format="text"),
    ]

    assert all(result.ok is False and result.error.error_code == "WRITE_BLOCKED" for result in results)
