"""Parse raw export rows into canonical :class:`RawProjectRecord` objects.

The parser performs *structural* work only (header detection, header mapping,
row extraction). It never normalises values - that is the normaliser's job. All
original columns are retained on each record in ``raw_row`` for provenance.

A single source column can feed more than one canonical field (for example the
K-RERA export labels its registration number column ``Certificate No``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict

from rera.constants import REQUIRED_FIELDS, SOURCE_FIELDS

# Maps canonical field -> possible header spellings found in an export.
COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "rera_registration_number": (
        "rera registration number",
        "registration number",
        "registration no",
        "reg no",
        "reg number",
        "rera reg no",
        "rera number",
        "kochi rera number",
        "k rera number",
        "project registration number",
        "certificate number rera",
        # Observed in the official export: the registration number column is
        # labelled "Certificate No" and holds a K-RERA/PRJ/... value.
        "certificate no",
        "certificate number",
    ),
    "project_name": (
        "project name",
        "name of project",
        "project",
        "project title",
    ),
    "promoter_name": (
        "promoter name",
        "name of promoter",
        "promoter",
        "developer name",
        "developer",
    ),
    "project_type": ("project type", "type of project", "type"),
    "project_status": ("project status", "status", "current status"),
    "project_start_date": (
        "project start date",
        "start date",
        "commencement date",
        "date of commencement",
        "project commencement date",
    ),
    "declared_completion_date": (
        "declared completion date",
        "completion date",
        "date of completion",
        "declared date of completion",
        "proposed completion date",
        "expected completion date",
    ),
    "certificate_number": (
        "certificate number",
        "registration certificate number",
        "certificate no",
        "rera certificate number",
    ),
    "certificate_date": (
        "certificate date",
        "date of registration",
        "registration date",
        "certificate issued date",
    ),
    "last_modified_date": (
        "last modified date",
        "last modified",
        "modified date",
        "last updated date",
        "last updated",
    ),
    "total_units": (
        "total units",
        "total no of units",
        "number of units",
        "no of units",
        "total",
    ),
    "sold_units": (
        "sold units",
        "units sold",
        "no of units sold",
        "booked units",
        "number of units sold",
        "sold",
    ),
    "district": ("district", "revenue district", "district name"),
    "taluk": ("taluk", "taluk name"),
    "village": ("village", "village name", "local body"),
    "source_url": ("source url", "project url", "detail url", "url", "link"),
}


def normalize_header(header: str) -> str:
    """Lowercase and collapse non-alphanumeric characters for matching."""

    return re.sub(r"[^a-z0-9]+", " ", str(header).lower()).strip()


_HEADER_TO_FIELDS: dict[str, list[str]] = {}
for _field, _aliases in COLUMN_ALIASES.items():
    for _alias in _aliases:
        _slot = _HEADER_TO_FIELDS.setdefault(normalize_header(_alias), [])
        if _field not in _slot:
            _slot.append(_field)


class RawProjectRecord(BaseModel):
    """A single parsed row with canonical field names but raw (string) values."""

    model_config = ConfigDict(extra="ignore")

    source_row_number: int
    raw_row: dict[str, str] = field(default_factory=dict)

    rera_registration_number: str | None = None
    project_name: str | None = None
    promoter_name: str | None = None
    project_type: str | None = None
    project_status: str | None = None
    project_start_date: str | None = None
    declared_completion_date: str | None = None
    certificate_number: str | None = None
    certificate_date: str | None = None
    last_modified_date: str | None = None
    total_units: str | None = None
    sold_units: str | None = None
    district: str | None = None
    taluk: str | None = None
    village: str | None = None
    source_url: str | None = None


@dataclass
class ParseError:
    row_number: int | None
    message: str
    raw_row: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParseResult:
    records: list[RawProjectRecord] = field(default_factory=list)
    errors: list[ParseError] = field(default_factory=list)
    unmapped_columns: list[str] = field(default_factory=list)
    missing_required_fields: list[str] = field(default_factory=list)
    column_warnings: list[str] = field(default_factory=list)
    mapped_columns: dict[str, tuple[str, ...]] = field(default_factory=dict)


@dataclass
class BuiltTable:
    """A grid converted into named rows using a detected header row."""

    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, str]] = field(default_factory=list)
    header_row: int = 0
    header_score: int = 0


def _header_score(cells: list[Any]) -> int:
    return sum(1 for cell in cells if normalize_header(cell) in _HEADER_TO_FIELDS)


def detect_header_row(
    grid: list[list[Any]], max_scan: int = 15
) -> tuple[int, int]:
    """Return ``(header_row_index, score)`` for the most header-like row.

    Scans the first ``max_scan`` rows and picks the one with the most
    recognised column headers. Falls back to row 0 when nothing matches.
    """

    best_index, best_score = 0, -1
    for index, row in enumerate(grid[:max_scan]):
        score = _header_score(row)
        if score > best_score:
            best_index, best_score = index, score
    if best_score <= 0:
        return 0, best_score
    return best_index, best_score


def _dedupe_columns(columns: list[str]) -> list[str]:
    """Make column names non-empty and unique while preserving order."""

    seen: dict[str, int] = {}
    result: list[str] = []
    for position, column in enumerate(columns):
        name = column.strip() or f"column_{position + 1}"
        if name in seen:
            seen[name] += 1
            name = f"{name}__{seen[name]}"
        else:
            seen[name] = 0
        result.append(name)
    return result


def build_records_from_grid(
    grid: list[list[Any]], header_row: int | None = None
) -> BuiltTable:
    """Convert a raw grid (list of rows) into named row dicts."""

    if not grid:
        return BuiltTable()

    if header_row is None:
        detected, score = detect_header_row(grid)
        header_row = detected
    else:
        score = _header_score(grid[header_row]) if header_row < len(grid) else 0

    header_cells = list(grid[header_row]) if header_row < len(grid) else []
    columns = _dedupe_columns([str(cell).strip() for cell in header_cells])

    rows: list[dict[str, str]] = []
    for raw_row in grid[header_row + 1 :]:
        values = ["" if value is None else str(value).strip() for value in raw_row]
        values = (values + [""] * len(columns))[: len(columns)]
        if any(value != "" for value in values):
            rows.append(dict(zip(columns, values, strict=False)))

    return BuiltTable(
        columns=columns, rows=rows, header_row=header_row, header_score=score
    )


def _map_headers(
    columns: list[str],
) -> tuple[dict[str, tuple[str, ...]], list[str], list[str]]:
    """Return (column -> fields map, unmapped columns, warnings)."""

    mapping: dict[str, tuple[str, ...]] = {}
    unmapped: list[str] = []
    warnings: list[str] = []
    claimed_fields: dict[str, str] = {}

    for column in columns:
        fields = _HEADER_TO_FIELDS.get(normalize_header(column), [])
        if not fields:
            unmapped.append(column)
            continue
        usable: list[str] = []
        for field_name in fields:
            if field_name in claimed_fields:
                warnings.append(
                    f"Multiple columns map to '{field_name}': "
                    f"'{claimed_fields[field_name]}' and '{column}'. Using the first."
                )
                continue
            claimed_fields[field_name] = column
            usable.append(field_name)
        if usable:
            mapping[column] = tuple(usable)
    return mapping, unmapped, warnings


def parse_records(
    rows: list[dict[str, Any]], columns: list[str] | None = None
) -> ParseResult:
    """Parse raw export rows into structured records.

    Args:
        rows: list of row dicts exactly as read from the source export.
        columns: optional ordered column names; derived from rows otherwise.
    """

    result = ParseResult()
    if columns is None:
        seen: list[str] = []
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.append(key)
        columns = seen

    header_map, unmapped, warnings = _map_headers(columns)
    result.unmapped_columns = unmapped
    result.column_warnings = warnings
    result.mapped_columns = header_map

    mapped_fields: set[str] = set()
    for fields in header_map.values():
        mapped_fields.update(fields)
    result.missing_required_fields = [f for f in REQUIRED_FIELDS if f not in mapped_fields]

    for index, row in enumerate(rows, start=1):
        canonical: dict[str, Any] = {f: None for f in SOURCE_FIELDS}
        raw_row: dict[str, str] = {}
        for column, value in row.items():
            text = "" if value is None else str(value)
            raw_row[column] = text
            for field_name in header_map.get(column, ()):
                if canonical.get(field_name) in (None, ""):
                    canonical[field_name] = text if text != "" else None

        if all(value is None for value in canonical.values()):
            result.errors.append(
                ParseError(
                    row_number=index,
                    message="Row contains no mapped values.",
                    raw_row=raw_row,
                )
            )
            continue

        try:
            record = RawProjectRecord(
                source_row_number=index, raw_row=raw_row, **canonical
            )
        except Exception as exc:  # noqa: BLE001
            result.errors.append(
                ParseError(
                    row_number=index,
                    message=f"Could not build record: {exc}",
                    raw_row=raw_row,
                )
            )
            continue
        result.records.append(record)

    return result
