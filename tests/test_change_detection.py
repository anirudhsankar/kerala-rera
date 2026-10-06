"""Change detection tests: field-level diffs."""

from __future__ import annotations

from datetime import date

from rera.ingestion.change_detector import detect_changes


def test_detect_completion_and_sold_change_but_not_status():
    old = {
        "project_name": "P",
        "project_status": "Ongoing",
        "declared_completion_date": date(2027, 6, 30),
        "sold_units": 10,
        "total_units": 100,
    }
    new = {
        "project_name": "P",
        "project_status": "Ongoing",
        "declared_completion_date": date(2027, 12, 31),
        "sold_units": 25,
        "total_units": 100,
    }
    changes = {c.field_name: c for c in detect_changes(old, new)}

    assert changes["declared_completion_date"].old_value == "2027-06-30"
    assert changes["declared_completion_date"].new_value == "2027-12-31"
    assert changes["sold_units"].old_value == "10"
    assert changes["sold_units"].new_value == "25"
    assert "project_status" not in changes
    assert "total_units" not in changes


def test_no_changes_when_identical():
    values = {"project_name": "P", "sold_units": 10}
    assert detect_changes(values, dict(values)) == []


def test_none_to_value_is_a_change():
    changes = detect_changes({"sold_units": None}, {"sold_units": 5})
    assert len(changes) == 1
    assert changes[0].old_value is None
    assert changes[0].new_value == "5"
