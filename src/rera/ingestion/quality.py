"""Data quality finding model shared by normalisation and validation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QualityIssue:
    """A single non-fatal data quality finding.

    Issues never cause a record to be discarded; they are stored in
    ``data_quality_issues`` and surfaced in reports.
    """

    severity: str
    issue_type: str
    message: str
    field_name: str | None = None
    raw_value: str | None = None
