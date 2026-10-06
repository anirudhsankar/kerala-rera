"""Normalise raw source values while always preserving the raw originals.

Every transformation is best-effort: when a value cannot be interpreted the
raw value is retained and a :class:`QualityIssue` is emitted instead of
dropping the row.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from rera.constants import (
    DISTRICT_ALIASES,
    PROJECT_TYPE_ALIASES,
    SOURCE_FIELDS,
    STATUS_ALIASES,
    TRACKED_FIELDS,
)
from rera.ingestion.parser import RawProjectRecord
from rera.ingestion.quality import QualityIssue

NULL_TOKENS = {
    "",
    "-",
    "--",
    "na",
    "n/a",
    "null",
    "none",
    "nil",
    "nan",
    "not available",
    "not applicable",
    "unknown",
}

DATE_FORMATS = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%Y/%m/%d",
    "%d/%m/%y",
    "%d-%m-%y",
    "%d.%m.%y",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%d-%b-%Y",
    "%d %b, %Y",
    "%Y%m%d",
)


class NormalizedProject(BaseModel):
    """Canonical project values with the original strings preserved."""

    model_config = ConfigDict(extra="ignore")

    rera_registration_number: str | None = None
    project_name: str | None = None
    promoter_name: str | None = None
    project_type: str | None = None
    project_status: str | None = None
    project_start_date: date | None = None
    declared_completion_date: date | None = None
    certificate_number: str | None = None
    certificate_date: date | None = None
    last_modified_date: date | None = None
    total_units: int | None = None
    sold_units: int | None = None
    district: str | None = None
    taluk: str | None = None
    village: str | None = None
    source_url: str | None = None

    raw_values: dict[str, str | None] = Field(default_factory=dict)


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    if text.lower() in NULL_TOKENS:
        return None
    return text


def normalize_date(value: str | None) -> tuple[date | None, str | None]:
    """Return ``(date, error_message)``. Empty input yields ``(None, None)``."""

    text = normalize_text(value)
    if text is None:
        return None, None

    # Strip an attached time component where safe.
    match = re.match(r"^(\d{4}-\d{2}-\d{2})[ T]\d{2}:\d{2}", text)
    if match:
        text = match.group(1)
    else:
        match = re.match(r"^(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})[ T]\d", text)
        if match:
            text = match.group(1)

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date(), None
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text).date(), None
    except ValueError:
        return None, f"Unrecognised date format: '{value}'"


def parse_int(value: str | None) -> tuple[int | None, str | None]:
    """Parse an integer from messy strings such as ``'1,000'`` or ``'100.0'``.

    Comma-separated thousands (``1,000``) and Indian grouping (``1,00,000``)
    are accepted, but loosely comma'd strings such as ``1,2,3`` are rejected
    rather than silently coerced.
    """

    text = normalize_text(value)
    if text is None:
        return None, None

    cleaned = text.replace(" ", "")
    if "," in cleaned:
        grouped_intl = re.fullmatch(r"[+-]?\d{1,3}(,\d{3})+", cleaned)
        grouped_indian = re.fullmatch(r"[+-]?\d{1,2}(,\d{2})*,\d{3}", cleaned)
        if not (grouped_intl or grouped_indian):
            return None, f"Not a valid integer: '{value}'"
        cleaned = cleaned.replace(",", "")

    if re.fullmatch(r"[+-]?\d+", cleaned):
        return int(cleaned), None
    if re.fullmatch(r"[+-]?\d+\.0+", cleaned):
        return int(float(cleaned)), None
    return None, f"Not a valid integer: '{value}'"


def normalize_district(value: str | None) -> str | None:
    text = normalize_text(value)
    if text is None:
        return None
    key = text.lower()
    if key in DISTRICT_ALIASES:
        return DISTRICT_ALIASES[key]
    return " ".join(part.capitalize() for part in text.split())


def normalize_status(value: str | None) -> str | None:
    text = normalize_text(value)
    if text is None:
        return None
    key = text.lower()
    if key in STATUS_ALIASES:
        return STATUS_ALIASES[key]
    # Preserve the source text verbatim when it is not a known synonym.
    return text


def normalize_project_type(value: str | None) -> str | None:
    text = normalize_text(value)
    if text is None:
        return None
    key = text.lower()
    if key in PROJECT_TYPE_ALIASES:
        return PROJECT_TYPE_ALIASES[key]
    # Preserve the source text verbatim (e.g. "Residential (Apartment)").
    return text


def normalize_record(
    raw: RawProjectRecord,
) -> tuple[NormalizedProject, list[QualityIssue]]:
    """Normalise a parsed record, emitting issues for unparseable values."""

    issues: list[QualityIssue] = []
    raw_values: dict[str, str | None] = {f: getattr(raw, f, None) for f in SOURCE_FIELDS}

    start_date, err = normalize_date(raw.project_start_date)
    if err:
        issues.append(QualityIssue("WARNING", "invalid_date", err, "project_start_date", raw.project_start_date))

    completion_date, err = normalize_date(raw.declared_completion_date)
    if err:
        issues.append(
            QualityIssue(
                "WARNING",
                "invalid_date",
                err,
                "declared_completion_date",
                raw.declared_completion_date,
            )
        )

    certificate_date, err = normalize_date(raw.certificate_date)
    if err:
        issues.append(QualityIssue("WARNING", "invalid_date", err, "certificate_date", raw.certificate_date))

    last_modified_date, err = normalize_date(raw.last_modified_date)
    if err:
        issues.append(
            QualityIssue("WARNING", "invalid_date", err, "last_modified_date", raw.last_modified_date)
        )

    total_units, err = parse_int(raw.total_units)
    if err:
        issues.append(QualityIssue("WARNING", "invalid_number", err, "total_units", raw.total_units))

    sold_units, err = parse_int(raw.sold_units)
    if err:
        issues.append(QualityIssue("WARNING", "invalid_number", err, "sold_units", raw.sold_units))

    normalized = NormalizedProject(
        rera_registration_number=normalize_text(raw.rera_registration_number),
        project_name=normalize_text(raw.project_name),
        promoter_name=normalize_text(raw.promoter_name),
        project_type=normalize_project_type(raw.project_type),
        project_status=normalize_status(raw.project_status),
        project_start_date=start_date,
        declared_completion_date=completion_date,
        certificate_number=normalize_text(raw.certificate_number),
        certificate_date=certificate_date,
        last_modified_date=last_modified_date,
        total_units=total_units,
        sold_units=sold_units,
        district=normalize_district(raw.district),
        taluk=normalize_text(raw.taluk),
        village=normalize_text(raw.village),
        source_url=normalize_text(raw.source_url),
        raw_values=raw_values,
    )
    return normalized, issues


def _stringify(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def hashed_values(normalized: NormalizedProject) -> dict[str, str | None]:
    """Canonical string values used for hashing and change detection."""

    return {field: _stringify(getattr(normalized, field)) for field in TRACKED_FIELDS}


def compute_source_hash(normalized: NormalizedProject) -> str:
    """Deterministic SHA-256 of the canonicalised source fields."""

    canonical = json.dumps(
        hashed_values(normalized),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
