import json
import subprocess
from pathlib import Path

import pytest
from apple_numbers_mcp.numbers_bridge import NumbersBridge, NumbersBridgeError


def _bridge(tmp_path: Path) -> NumbersBridge:
    return NumbersBridge(script_path=Path("/tmp/numbers.js"), timeout_seconds=5, allowed_roots=(tmp_path,))


def _fake_run(monkeypatch, bridge: NumbersBridge, result: dict[str, object] | None = None, *, error: str | None = None) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []

    def fake(payload: dict[str, object]) -> dict[str, object]:
        calls.append(payload)
        if error is not None:
            raise NumbersBridge._map_failure(error)
        return result or {}

    monkeypatch.setattr(bridge, "_run", fake)
    return calls


def _fake_subprocess(monkeypatch, stdout: str, returncode: int = 0, stderr: str = "") -> None:
    def fake(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], returncode, stdout, stderr)

    monkeypatch.setattr(subprocess, "run", fake)


def test_list_documents_reports_application_state(monkeypatch, tmp_path) -> None:
    bridge = _bridge(tmp_path)
    _fake_run(monkeypatch, bridge, {"documents": [{"id": "D1", "name": "Budget", "path": "/x/Budget.numbers", "modified": False, "sheet_count": 2}], "application_running": True})

    documents, running = bridge.list_documents()

    assert running is True
    assert documents[0].name == "Budget"
    assert documents[0].sheet_count == 2


def test_open_document_rejects_path_outside_allowed_roots(tmp_path) -> None:
    with pytest.raises(NumbersBridgeError) as excinfo:
        _bridge(tmp_path).open_document("/etc/passwd.numbers")

    assert excinfo.value.error_code == "PATH_NOT_ALLOWED"


def test_open_document_rejects_relative_and_traversal_paths(tmp_path) -> None:
    bridge = _bridge(tmp_path)

    with pytest.raises(NumbersBridgeError) as relative:
        bridge.open_document("budget.numbers")
    with pytest.raises(NumbersBridgeError) as traversal:
        bridge.open_document(f"{tmp_path}/../outside.numbers")

    assert relative.value.error_code == "INVALID_INPUT"
    assert traversal.value.error_code == "PATH_NOT_ALLOWED"


def test_open_document_rejects_unsupported_extension(tmp_path) -> None:
    target = tmp_path / "notes.txt"
    target.write_text("x")

    with pytest.raises(NumbersBridgeError) as excinfo:
        _bridge(tmp_path).open_document(str(target))

    assert excinfo.value.error_code == "UNSUPPORTED_FILE_TYPE"


def test_open_document_passes_resolved_path(monkeypatch, tmp_path) -> None:
    target = tmp_path / "budget.numbers"
    target.write_text("x")
    bridge = _bridge(tmp_path)
    calls = _fake_run(monkeypatch, bridge, {"document": {"id": "D2", "name": "budget", "path": str(target)}})

    document = bridge.open_document(str(target))

    assert document.name == "budget"
    assert calls[0] == {"operation": "open", "path": str(target.resolve())}


def test_export_requires_matching_extension_and_overwrite(monkeypatch, tmp_path) -> None:
    bridge = _bridge(tmp_path)
    calls = _fake_run(monkeypatch, bridge, {})
    existing = tmp_path / "out.pdf"
    existing.write_text("old")

    with pytest.raises(NumbersBridgeError) as wrong_extension:
        bridge.export_document("Budget", str(tmp_path / "out.xlsx"), "pdf")
    with pytest.raises(NumbersBridgeError) as exists:
        bridge.export_document("Budget", str(existing), "pdf")
    with pytest.raises(NumbersBridgeError) as missing_dir:
        bridge.export_document("Budget", str(tmp_path / "nope" / "out.pdf"), "pdf")
    assert calls == []
    assert wrong_extension.value.error_code == "INVALID_INPUT"
    assert exists.value.error_code == "FILE_EXISTS"
    assert missing_dir.value.error_code == "INVALID_INPUT"

    assert bridge.export_document("Budget", str(existing), "pdf", overwrite=True) == str(existing.resolve())
    assert calls[0]["operation"] == "export"


def test_read_range_limits_cells(monkeypatch, tmp_path) -> None:
    bridge = _bridge(tmp_path)
    calls = _fake_run(monkeypatch, bridge, {})

    with pytest.raises(NumbersBridgeError) as too_big:
        bridge.read_range("B", "S", "T", 1, 1, 21, 10)
    with pytest.raises(NumbersBridgeError) as zero_based:
        bridge.read_range("B", "S", "T", 0, 1, 1, 1)

    assert calls == []
    assert too_big.value.error_code == "INVALID_INPUT"
    assert zero_based.value.error_code == "INVALID_INPUT"


def test_read_range_parses_cells(monkeypatch, tmp_path) -> None:
    bridge = _bridge(tmp_path)
    _fake_run(monkeypatch, bridge, {"cells": [[{"value": 3, "formatted_value": "3", "formula": "=1+2"}, {"value": None}]]})

    cells = bridge.read_range("B", "S", "T", 1, 1, 1, 2)

    assert cells[0][0].formula == "=1+2"
    assert cells[0][1].value is None


def test_write_range_blocks_formulas_unless_allowed(monkeypatch, tmp_path) -> None:
    bridge = _bridge(tmp_path)
    calls = _fake_run(monkeypatch, bridge, {"written_cells": 2})

    with pytest.raises(NumbersBridgeError) as excinfo:
        bridge.write_range("B", "S", "T", 1, 1, [["a", "=SUM(A1:A3)"]])
    assert excinfo.value.error_code == "FORMULA_NOT_ALLOWED"
    assert calls == []

    assert bridge.write_range("B", "S", "T", 1, 1, [["a", "=SUM(A1:A3)"]], allow_formulas=True) == 2
    assert calls[0]["values"] == [["a", "=SUM(A1:A3)"]]


def test_write_range_validates_grid(tmp_path) -> None:
    bridge = _bridge(tmp_path)

    for values in ([], [[]], [["a"], ["b", "c"]]):
        with pytest.raises(NumbersBridgeError) as excinfo:
            bridge.write_range("B", "S", "T", 1, 1, values)
        assert excinfo.value.error_code == "INVALID_INPUT"
    with pytest.raises(NumbersBridgeError):
        bridge.write_range("B", "S", "T", 1, 1, [[1] * 41] * 51)


def test_create_table_limits_size(tmp_path) -> None:
    with pytest.raises(NumbersBridgeError) as excinfo:
        _bridge(tmp_path).create_table("B", "S", "T", 1000, 100)

    assert excinfo.value.error_code == "INVALID_INPUT"


@pytest.mark.parametrize(
    ("message", "code"),
    [
        ("Document not found: X", "NOT_FOUND"),
        ("Sheet name is ambiguous (2 matches): X", "AMBIGUOUS_NAME"),
        ("Numbers is not running; open a document first", "NUMBERS_NOT_RUNNING"),
        ("Range exceeds table bounds (3 rows x 3 columns); nothing was read or written", "RANGE_OUT_OF_BOUNDS"),
        ('A table named "T" already exists on this sheet', "ALREADY_EXISTS"),
        ("Not authorized to send Apple events to Numbers. (-1743)", "PERMISSION_DENIED"),
        ("something else", "NUMBERS_ERROR"),
    ],
)
def test_script_failures_map_to_error_codes(monkeypatch, tmp_path, message: str, code: str) -> None:
    _fake_subprocess(monkeypatch, json.dumps({"ok": False, "message": message}))

    with pytest.raises(NumbersBridgeError) as excinfo:
        _bridge(tmp_path).list_sheets("Budget")

    assert excinfo.value.error_code == code


def test_osascript_failure_and_bad_output(monkeypatch, tmp_path) -> None:
    bridge = _bridge(tmp_path)
    _fake_subprocess(monkeypatch, "", returncode=1, stderr="execution error: Not authorized (-1743)")
    with pytest.raises(NumbersBridgeError) as denied:
        bridge.list_sheets("Budget")
    assert denied.value.error_code == "PERMISSION_DENIED"

    _fake_subprocess(monkeypatch, "not json")
    with pytest.raises(NumbersBridgeError) as garbage:
        bridge.list_sheets("Budget")
    assert garbage.value.error_code == "INVALID_SCRIPT_OUTPUT"


def test_timeout_warns_about_partial_writes(monkeypatch, tmp_path) -> None:
    def fake(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 5)

    monkeypatch.setattr(subprocess, "run", fake)

    with pytest.raises(NumbersBridgeError) as excinfo:
        _bridge(tmp_path).write_range("B", "S", "T", 1, 1, [["a"]])

    assert excinfo.value.error_code == "SCRIPT_TIMEOUT"
    assert "partly applied" in excinfo.value.message


def test_write_range_as_text_skips_formula_guard_but_not_combination(monkeypatch, tmp_path) -> None:
    bridge = _bridge(tmp_path)
    calls = _fake_run(monkeypatch, bridge, {"written_cells": 1})

    assert bridge.write_range("D", "S", "T", 1, 1, [["=not a formula"]], as_text=True) == 1
    assert calls[0]["as_text"] is True
    with pytest.raises(NumbersBridgeError) as excinfo:
        bridge.write_range("D", "S", "T", 1, 1, [["a"]], allow_formulas=True, as_text=True)
    assert excinfo.value.error_code == "INVALID_INPUT"


def test_save_document_rules(monkeypatch, tmp_path) -> None:
    bridge = _bridge(tmp_path)
    calls = _fake_run(monkeypatch, bridge, {"document": {"id": "D1", "name": "x", "path": str(tmp_path / "x.numbers")}})
    existing = tmp_path / "old.numbers"
    existing.write_text("x")

    for bad in (str(tmp_path / "x.xlsx"), str(existing), str(tmp_path / "missing" / "x.numbers")):
        with pytest.raises(NumbersBridgeError):
            bridge.save_document("D1", bad)
    with pytest.raises(NumbersBridgeError) as outside:
        bridge.save_document("D1", "/etc/x.numbers")
    assert outside.value.error_code == "PATH_NOT_ALLOWED"
    assert calls == []

    assert bridge.save_document("D1", str(tmp_path / "x.numbers")).id == "D1"
    assert bridge.save_document("D1", str(existing), overwrite=True).id == "D1"


def test_close_document_reports_unsaved_changes(monkeypatch, tmp_path) -> None:
    _fake_subprocess(monkeypatch, json.dumps({"ok": False, "message": "Document has unsaved changes or no saved path; save it first or pass discard=true"}))

    with pytest.raises(NumbersBridgeError) as excinfo:
        _bridge(tmp_path).close_document("D1")

    assert excinfo.value.error_code == "UNSAVED_CHANGES"


def test_structure_changes_validate_and_send_positions(monkeypatch, tmp_path) -> None:
    bridge = _bridge(tmp_path)
    calls = _fake_run(monkeypatch, bridge, {"table": {"name": "T", "rows": 5, "columns": 2}})

    bridge.add_rows("D", "S", "T", 2, after_row=0)
    bridge.add_columns("D", "S", "T", 1)
    bridge.delete_rows("D", "S", "T", 3, 2)
    bridge.delete_columns("D", "S", "T", 2)

    assert calls[0]["after"] == 0 and calls[0]["count"] == 2
    assert "after" not in calls[1]
    assert calls[2]["start"] == 3 and calls[2]["operation"] == "delete_rows"
    assert calls[3]["operation"] == "delete_columns"
    for call in (lambda: bridge.add_rows("D", "S", "T", 0), lambda: bridge.add_rows("D", "S", "T", 101), lambda: bridge.delete_rows("D", "S", "T", 0), lambda: bridge.add_rows("D", "S", "T", 1, after_row=-1)):
        with pytest.raises(NumbersBridgeError):
            call()
    assert len(calls) == 4


def test_set_format_validation(monkeypatch, tmp_path) -> None:
    bridge = _bridge(tmp_path)
    calls = _fake_run(monkeypatch, bridge, {"formatted_cells": 4})

    for kwargs in ({}, {"cell_format": "0.00"}, {"alignment": "diagonal"}):
        with pytest.raises(NumbersBridgeError):
            bridge.set_format("D", "S", "T", 1, 1, 2, 2, **kwargs)
    assert calls == []

    assert bridge.set_format("D", "S", "T", 1, 1, 2, 2, cell_format="text", alignment="left") == 4
    assert calls[0]["format"] == "text" and calls[0]["alignment"] == "left"


def test_create_document_passes_template(monkeypatch, tmp_path) -> None:
    bridge = _bridge(tmp_path)
    calls = _fake_run(monkeypatch, bridge, {"document": {"id": "D9", "name": "Untitled", "path": None}})

    document = bridge.create_document("Blank")

    assert document.id == "D9" and document.path is None
    assert calls[0] == {"operation": "create", "template_name": "Blank"}
