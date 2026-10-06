"""Validation rules producing non-fatal data quality findings.

Validation never discards a record. Instead it emits :class:`QualityIssue`
objects that are persisted to ``data_quality_issues`` for review.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from rera.constants import (
    KERALA_DISTRICTS,
    KNOWN_PROJECT_STATUSES,
    KNOWN_PROJECT_TYPES,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
)
from rera.ingestion.normalizer import NormalizedProject
from rera.ingestion.quality import QualityIssue


def validate_record(
    normalized: NormalizedProject,
    *,
    today: date | None = None,
) -> list[QualityIssue]:
    """Apply field-level validation rules to a normalised record."""

    today = today or datetime.now(UTC).date()
    issues: list[QualityIssue] = []
    raw = normalized.raw_values

    # Identity / required fields
    if not normalized.rera_registration_number:
        issues.append(
            QualityIssue(
                SEVERITY_ERROR,
                "missing_registration_number",
                "RERA registration number is missing.",
                "rera_registration_number",
                raw.get("rera_registration_number"),
            )
        )
    if not normalized.project_name:
        issues.append(
            QualityIssue(
                SEVERITY_WARNING,
                "missing_project_name",
                "Project name is missing.",
                "project_name",
                raw.get("project_name"),
            )
        )

    # Date consistency
    if (
        normalized.project_start_date
        and normalized.declared_completion_date
        and normalized.declared_completion_date < normalized.project_start_date
    ):
        issues.append(
            QualityIssue(
                SEVERITY_WARNING,
                "completion_before_start",
                "Declared completion date is earlier than the project start date.",
                "declared_completion_date",
                raw.get("declared_completion_date"),
            )
        )

    if (
        normalized.project_start_date
        and normalized.project_start_date > today
    ):
        issues.append(
            QualityIssue(
                SEVERITY_INFO,
                "future_start_date",
                "Project start date is in the future.",
                "project_start_date",
                raw.get("project_start_date"),
            )
        )

    # Unit consistency
    if normalized.total_units is not None and normalized.total_units < 0:
        issues.append(
            QualityIssue(
                SEVERITY_WARNING,
                "negative_total_units",
                "Total units is negative.",
                "total_units",
                raw.get("total_units"),
            )
        )
    if normalized.sold_units is not None and normalized.sold_units < 0:
        issues.append(
            QualityIssue(
                SEVERITY_WARNING,
                "negative_sold_units",
                "Sold units is negative.",
                "sold_units",
                raw.get("sold_units"),
            )
        )
    if (
        normalized.total_units is not None
        and normalized.sold_units is not None
        and normalized.sold_units > normalized.total_units
    ):
        issues.append(
            QualityIssue(
                SEVERITY_WARNING,
                "sold_exceeds_total",
                f"Sold units ({normalized.sold_units}) exceed total units "
                f"({normalized.total_units}).",
                "sold_units",
                raw.get("sold_units"),
            )
        )

    # Controlled vocabularies
    if normalized.district and normalized.district not in KERALA_DISTRICTS:
        issues.append(
            QualityIssue(
                SEVERITY_WARNING,
                "unknown_district",
                f"District '{normalized.district}' is not a known Kerala district.",
                "district",
                raw.get("district"),
            )
        )
    if normalized.project_status and normalized.project_status not in KNOWN_PROJECT_STATUSES:
        issues.append(
            QualityIssue(
                SEVERITY_INFO,
                "unexpected_status",
                f"Unrecognised project status '{normalized.project_status}'.",
                "project_status",
                raw.get("project_status"),
            )
        )
    if normalized.project_type and normalized.project_type not in KNOWN_PROJECT_TYPES:
        issues.append(
            QualityIssue(
                SEVERITY_INFO,
                "unexpected_project_type",
                f"Unrecognised project type '{normalized.project_type}'.",
                "project_type",
                raw.get("project_type"),
            )
        )

    # Neutral, factual derived observation (never an interpretation).
    if normalized.declared_completion_date and normalized.declared_completion_date < today:
        issues.append(
            QualityIssue(
                SEVERITY_INFO,
                "declared_completion_date_passed",
                "Declared completion date has passed (factual observation only; "
                "not a regulatory determination).",
                "declared_completion_date",
                raw.get("declared_completion_date"),
            )
        )

    return issues


def detect_duplicate_registrations(
    registration_numbers: list[str | None],
) -> list[QualityIssue]:
    """Flag registration numbers that occur more than once in a batch."""

    issues: list[QualityIssue] = []
    seen: dict[str, int] = {}
    for number in registration_numbers:
        if not number:
            continue
        seen[number] = seen.get(number, 0) + 1
    for number, count in seen.items():
        if count > 1:
            issues.append(
                QualityIssue(
                    SEVERITY_ERROR,
                    "duplicate_registration_number",
                    f"Registration number '{number}' appears {count} times in this batch.",
                    "rera_registration_number",
                    number,
                )
            )
    return issues
