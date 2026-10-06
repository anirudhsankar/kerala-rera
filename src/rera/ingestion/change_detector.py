"""Field-level change detection between two observed states."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rera.constants import TRACKED_FIELDS

# Registration number is the identity key; it is not a "change".
CHANGE_FIELDS = tuple(f for f in TRACKED_FIELDS if f != "rera_registration_number")

# Snapshot/project column differs from the normalized field name here.
_FIELD_TO_ATTR = {
    "promoter_name": "promoter_name_raw",
}


@dataclass
class ChangeEventData:
    field_name: str
    old_value: str | None
    new_value: str | None


def format_value(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def normalized_values(normalized: Any) -> dict[str, Any]:
    return {field: getattr(normalized, field, None) for field in CHANGE_FIELDS}


def project_values(project: Any) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for field in CHANGE_FIELDS:
        attr = _FIELD_TO_ATTR.get(field, field)
        values[field] = getattr(project, attr, None)
    return values


def detect_changes(
    old_values: dict[str, Any], new_values: dict[str, Any]
) -> list[ChangeEventData]:
    """Return one event per changed tracked field."""

    events: list[ChangeEventData] = []
    for field in CHANGE_FIELDS:
        old_raw = old_values.get(field)
        new_raw = new_values.get(field)
        old_str = format_value(old_raw)
        new_str = format_value(new_raw)
        if old_str != new_str:
            events.append(
                ChangeEventData(field_name=field, old_value=old_str, new_value=new_str)
            )
    return events
