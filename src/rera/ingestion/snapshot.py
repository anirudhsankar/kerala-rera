"""Snapshot creation helpers.

A snapshot captures the source state observed during one collection. Once
created, a snapshot is never modified.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from rera.database.models import ProjectSnapshot
from rera.ingestion.normalizer import NormalizedProject, compute_source_hash

SNAPSHOT_FIELDS = (
    "rera_registration_number",
    "project_name",
    "promoter_name",
    "project_type",
    "project_status",
    "project_start_date",
    "declared_completion_date",
    "certificate_number",
    "certificate_date",
    "last_modified_date",
    "total_units",
    "sold_units",
    "district",
    "taluk",
    "village",
    "source_url",
)

# Map normalized source field -> snapshot column name.
_FIELD_TO_COLUMN = {
    "promoter_name": "promoter_name_raw",
}


def build_snapshot(
    project_id: int,
    normalized: NormalizedProject,
    *,
    raw_record: dict[str, Any] | None = None,
    collected_at: datetime | None = None,
    snapshot_date: date | None = None,
) -> ProjectSnapshot:
    """Create (but do not persist) a :class:`ProjectSnapshot`."""

    collected_at = collected_at or datetime.now().astimezone()
    column_values: dict[str, Any] = {}
    for field in SNAPSHOT_FIELDS:
        column = _FIELD_TO_COLUMN.get(field, field)
        column_values[column] = getattr(normalized, field)

    return ProjectSnapshot(
        project_id=project_id,
        snapshot_date=snapshot_date or collected_at.date(),
        collected_at=collected_at,
        source_hash=compute_source_hash(normalized),
        raw_record=raw_record,
        **column_values,
    )
