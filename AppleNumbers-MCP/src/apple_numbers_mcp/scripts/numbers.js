// JXA bridge for Numbers. Input is one JSON object (argv[0]); every user value
// crosses the Apple Event boundary as data, never as script source.
// Output is always one JSON line: {ok: true, result} or {ok: false, message}.
var CELL_TEXT_LIMIT = 500;

function exact(collection, name, label) {
  var matches = collection.whose({name: name})();
  if (matches.length === 0) throw new Error(label + ' not found: ' + name);
  if (matches.length > 1) throw new Error(label + ' name is ambiguous (' + matches.length + ' matches): ' + name);
  return matches[0];
}

function optional(fn, fallback) {
  try { var value = fn(); return value === undefined ? fallback : value; } catch (error) { return fallback; }
}

// Documents are addressed by their stable id; names can repeat.
function docById(app, id) {
  var matches = app.documents().filter(function (doc) { return String(doc.id()) === id; });
  if (matches.length === 0) throw new Error('Document not found: ' + id + ' (it may have been closed)');
  return matches[0];
}

function docInfo(doc) {
  var file = optional(function () { return doc.file(); }, null);
  return {
    id: String(doc.id()),
    name: String(doc.name()),
    path: file ? String(file) : null,
    modified: Boolean(optional(function () { return doc.modified(); }, false)),
    sheet_count: doc.sheets().length
  };
}

function tableInfo(table) {
  return {
    name: String(table.name()),
    rows: table.rowCount(),
    columns: table.columnCount(),
    header_rows: optional(function () { return table.headerRowCount(); }, 0),
    header_columns: optional(function () { return table.headerColumnCount(); }, 0),
    footer_rows: optional(function () { return table.footerRowCount(); }, 0)
  };
}

function cut(text) { return String(text).slice(0, CELL_TEXT_LIMIT); }

// Numbers reports a checkbox cell as a real boolean but a plain cell holding
// true as the number 1, so the format decides what a boolean-looking value is.
function readCell(cell, includeStyle) {
  var raw = optional(function () { return cell.value(); }, null);
  var format = String(optional(function () { return cell.format(); }, 'undefined'));
  var value = raw instanceof Date ? raw.toISOString() : typeof raw === 'string' ? cut(raw) : raw;
  if (format === 'checkbox' && (value === 1 || value === 0)) value = value === 1;
  var info = {
    value: value === undefined ? null : value,
    formatted_value: cut(optional(function () { return cell.formattedValue(); }, '') || ''),
    formula: cut(optional(function () { return cell.formula(); }, '') || ''),
    format: format === 'undefined' ? null : format
  };
  if (includeStyle) info.alignment = String(optional(function () { return cell.alignment(); }, ''));
  return info;
}

function writeCell(cell, value, asText) {
  if (value === null) { cell.value = ''; return; }
  if (asText) {
    // Text format first, or Numbers turns "15.05.2025" into a date and "05.2025" into 5.2025.
    cell.format = 'text';
    cell.value = String(value);
    return;
  }
  if (typeof value === 'boolean') { cell.format = 'checkbox'; cell.value = value; return; }
  cell.value = value;
}

function tableOf(app, input) {
  var sheet = exact(docById(app, input.document_id).sheets, input.sheet_name, 'Sheet');
  return exact(sheet.tables, input.table_name, 'Table');
}

function checkBounds(table, input, rows, columns) {
  if (input.start_row + rows - 1 > table.rowCount() || input.start_column + columns - 1 > table.columnCount()) {
    throw new Error('Range exceeds table bounds (' + table.rowCount() + ' rows x ' + table.columnCount() + ' columns); nothing was read or written');
  }
}

function dispatch(input) {
  var app = Application('Numbers');
  var op = input.operation;
  if (op === 'list_documents') {
    if (!app.running()) return {documents: [], application_running: false};
    return {documents: app.documents().map(docInfo), application_running: true};
  }
  if (op === 'open') {
    var opened = app.open(Path(input.path));
    var first = Array.isArray(opened) ? opened[0] : opened;
    if (!first) throw new Error('Numbers did not return the opened document');
    return {document: docInfo(first)};
  }
  if (op === 'create') {
    var properties = {};
    if (input.template_name) properties.documentTemplate = exact(app.templates, input.template_name, 'Template');
    var fresh = app.Document(properties);
    app.documents.push(fresh);
    return {document: docInfo(fresh)};
  }
  if (!app.running()) throw new Error('Numbers is not running; open a document first');
  var doc = docById(app, input.document_id);

  if (op === 'save') {
    app.save(doc, {in: Path(input.path)});
    // Saving can take a moment to settle path metadata; retry the lookup only, never the save.
    for (var attempt = 0; attempt < 10; attempt++) {
      var info = optional(function () { return docInfo(docById(app, input.document_id)); }, null);
      if (info && info.path) return {document: info};
      if (typeof delay === 'function') delay(0.1);
    }
    throw new Error('Saved, but Numbers did not report the saved path; call list_documents to check');
  }
  if (op === 'close') {
    var state = docInfo(doc);
    if ((state.modified || !state.path) && !input.discard) throw new Error('Document has unsaved changes or no saved path; save it first or pass discard=true');
    app.close(doc, {saving: 'no'});
    return {document: state};
  }
  if (op === 'export') {
    var formats = {pdf: 'PDF', xlsx: 'Microsoft Excel', csv: 'CSV'};
    app.export(doc, {to: Path(input.path), as: formats[input.format]});
    return {path: input.path, format: input.format};
  }
  if (op === 'list_sheets') {
    return {sheets: doc.sheets().map(function (sheet) { return {name: String(sheet.name()), table_count: sheet.tables().length}; })};
  }
  var sheet = exact(doc.sheets, input.sheet_name, 'Sheet');
  if (op === 'list_tables') return {tables: sheet.tables().map(tableInfo)};
  if (op === 'create_table') {
    if (sheet.tables.whose({name: input.table_name})().length) throw new Error('A table named "' + input.table_name + '" already exists on this sheet');
    var created = app.Table({name: input.table_name, rowCount: input.rows, columnCount: input.columns, headerRowCount: 0, headerColumnCount: 0, footerRowCount: 0});
    sheet.tables.push(created);
    return {table: tableInfo(created)};
  }
  var table = exact(sheet.tables, input.table_name, 'Table');

  if (op === 'add_rows' || op === 'add_columns') {
    var isRow = op === 'add_rows';
    var size = isRow ? table.rowCount() : table.columnCount();
    var after = input.after === null || input.after === undefined ? size : input.after;
    if (after < 0 || after > size) throw new Error('Position exceeds table bounds (' + size + (isRow ? ' rows' : ' columns') + '); nothing was added');
    // after = 0 inserts before the first row/column.
    for (var n = 0; n < input.count; n++) {
      if (isRow) {
        if (after === 0) app.addRowAbove(table.rows[0]); else app.addRowBelow(table.rows[after - 1]);
      } else {
        if (after === 0) app.addColumnBefore(table.columns[0]); else app.addColumnAfter(table.columns[after - 1]);
      }
    }
    return {table: tableInfo(table)};
  }
  if (op === 'delete_rows' || op === 'delete_columns') {
    var byRow = op === 'delete_rows';
    var total = byRow ? table.rowCount() : table.columnCount();
    if (input.start < 1 || input.start + input.count - 1 > total) throw new Error('Range exceeds table bounds (' + total + (byRow ? ' rows' : ' columns') + '); nothing was deleted');
    if (input.count >= total) throw new Error('A table must keep at least one ' + (byRow ? 'row' : 'column') + '; nothing was deleted');
    // Range deletes are unreliable in Numbers: delete one at a time, last first.
    for (var index = input.start + input.count - 1; index >= input.start; index--) {
      app.delete(byRow ? table.rows[index - 1] : table.columns[index - 1]);
    }
    return {table: tableInfo(table)};
  }
  if (op === 'read_range') {
    checkBounds(table, input, input.rows, input.columns);
    var cells = [];
    for (var r = 0; r < input.rows; r++) {
      var line = [];
      for (var c = 0; c < input.columns; c++) line.push(readCell(table.rows[input.start_row - 1 + r].cells[input.start_column - 1 + c], input.include_style));
      cells.push(line);
    }
    return {start_row: input.start_row, start_column: input.start_column, cells: cells, truncated_text_limit: CELL_TEXT_LIMIT};
  }
  if (op === 'write_range') {
    checkBounds(table, input, input.values.length, input.values[0].length);
    var written = 0;
    for (var wr = 0; wr < input.values.length; wr++) {
      for (var wc = 0; wc < input.values[wr].length; wc++) {
        var cell = table.rows[input.start_row - 1 + wr].cells[input.start_column - 1 + wc];
        try { writeCell(cell, input.values[wr][wc], input.as_text); written++; }
        catch (error) { throw new Error('Write stopped after ' + written + ' cells; partial changes remain. ' + String(error)); }
      }
    }
    return {written_cells: written};
  }
  if (op === 'set_format') {
    checkBounds(table, input, input.rows, input.columns);
    var styled = 0;
    for (var sr = 0; sr < input.rows; sr++) {
      for (var sc = 0; sc < input.columns; sc++) {
        var target = table.rows[input.start_row - 1 + sr].cells[input.start_column - 1 + sc];
        try {
          if (input.format) target.format = input.format;
          if (input.alignment) target.alignment = input.alignment;
          styled++;
        } catch (error) { throw new Error('Formatting stopped after ' + styled + ' cells; partial changes remain. ' + String(error)); }
      }
    }
    return {formatted_cells: styled};
  }
  throw new Error('Unsupported Numbers operation: ' + op);
}

function run(argv) {
  try {
    return JSON.stringify({ok: true, result: dispatch(JSON.parse(argv[0]))});
  } catch (error) {
    return JSON.stringify({ok: false, message: String(error && error.message ? error.message : error)});
  }
}
