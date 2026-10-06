"""Validation tests: rules emit findings but never discard records."""

from __future__ import annotations

from datetime import date

from rera.constants import SEVERITY_ERROR, SEVERITY_INFO, SEVERITY_WARNING
from rera.ingestion.normalizer import NormalizedProject
from rera.ingestion.validator import detect_duplicate_registrations, validate_record


def _project(**kwargs) -> NormalizedProject:
    defaults = {
        "rera_registration_number": "K-RERA/PRJ/ERK/001/2022",
        "project_name": "Sample",
        "district": "Ernakulam",
        "project_status": "Registered",
        "project_type": "Residential",
    }
    defaults.update(kwargs)
    return NormalizedProject(**defaults)


def test_missing_registration_number_is_error():
    issues = validate_record(_project(rera_registration_number=None))
    assert any(i.issue_type == "missing_registration_number" and i.severity == SEVERITY_ERROR for i in issues)


def test_missing_project_name_is_warning():
    issues = validate_record(_project(project_name=None))
    assert any(i.issue_type == "missing_project_name" and i.severity == SEVERITY_WARNING for i in issues)


def test_sold_units_exceeding_total_is_warning():
    issues = validate_record(_project(total_units=100, sold_units=120))
    assert any(i.issue_type == "sold_exceeds_total" and i.severity == SEVERITY_WARNING for i in issues)


def test_completion_before_start_is_warning():
    issues = validate_record(
        _project(project_start_date=date(2025, 1, 1), declared_completion_date=date(2024, 1, 1))
    )
    assert any(i.issue_type == "completion_before_start" for i in issues)


def test_unknown_district_is_warning():
    issues = validate_record(_project(district="Atlantis"))
    assert any(i.issue_type == "unknown_district" for i in issues)


def test_unexpected_status_is_info():
    issues = validate_record(_project(project_status="Strange Status"))
    assert any(i.issue_type == "unexpected_status" and i.severity == SEVERITY_INFO for i in issues)


def test_completion_date_passed_is_neutral_info():
    issues = validate_record(_project(declared_completion_date=date(2000, 1, 1)))
    passed = [i for i in issues if i.issue_type == "declared_completion_date_passed"]
    assert passed and passed[0].severity == SEVERITY_INFO
    # Neutral wording - no interpretation of "delay"/"default".
    assert "delay" not in passed[0].message.lower()
    assert "default" not in passed[0].message.lower()


def test_detect_duplicate_registrations():
    issues = detect_duplicate_registrations(["A", "B", "A", None, "A"])
    assert len(issues) == 1
    assert issues[0].raw_value == "A"
    assert issues[0].severity == SEVERITY_ERROR
