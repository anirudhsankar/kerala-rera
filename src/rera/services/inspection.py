"""Read-only inspection of an export file.

Helps adapt the parser to a real export without touching the database: it
reports sheets, detected header row, column-to-field mapping and a normalised
preview of the first rows.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rera.ingestion.normalizer import normalize_record
from rera.ingestion.parser import build_records_from_grid, parse_records
from rera.sources.krera import KReraExportFileSource


def inspect_source_file(
    file_path: str | Path,
    *,
    sheet_name: str | int | None = None,
    header_row: int | None = None,
    preview: int = 8,
) -> dict[str, Any]:
    """Inspect an export file and return a structured summary (no DB writes)."""

    source = KReraExportFileSource(file_path, sheet_name=sheet_name, header_row=header_row)
    grid = source.read_grid()
    built = build_records_from_grid(grid, header_row)
    parse_result = parse_records(built.rows, built.columns)

    preview_rows: list[dict[str, Any]] = []
    for raw in parse_result.records[:preview]:
        normalized, issues = normalize_record(raw)
        preview_rows.append(
            {
                "row": raw.source_row_number,
                "rera_registration_number": normalized.rera_registration_number,
                "project_name": normalized.project_name,
                "project_type": normalized.project_type,
                "project_status": normalized.project_status,
                "declared_completion_date": (
                    normalized.declared_completion_date.isoformat()
                    if normalized.declared_completion_date
                    else None
                ),
                "total_units": normalized.total_units,
                "sold_units": normalized.sold_units,
                "district": normalized.district,
                "issues": [issue.issue_type for issue in issues],
            }
        )

    return {
        "file": str(file_path),
        "sheets": source.sheet_names,
        "header_row": built.header_row,
        "header_score": built.header_score,
        "columns": built.columns,
        "mapped_columns": {
            column: list(fields) for column, fields in parse_result.mapped_columns.items()
        },
        "unmapped_columns": parse_result.unmapped_columns,
        "missing_required_fields": parse_result.missing_required_fields,
        "column_warnings": parse_result.column_warnings,
        "record_count": len(parse_result.records),
        "parse_errors": [
            {"row": error.row_number, "message": error.message}
            for error in parse_result.errors
        ],
        "preview": preview_rows,
    }
