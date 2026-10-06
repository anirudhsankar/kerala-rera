"""Normalisation tests: dates, numbers, controlled vocabularies and hashing."""

from __future__ import annotations

from datetime import date

import pytest

from rera.ingestion.normalizer import (
    NormalizedProject,
    compute_source_hash,
    normalize_date,
    normalize_district,
    normalize_project_type,
    normalize_record,
    normalize_status,
    parse_int,
)
from rera.ingestion.parser import RawProjectRecord


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2027-12-31", date(2027, 12, 31)),
        ("31/12/2027", date(2027, 12, 31)),
        ("31-12-2027", date(2027, 12, 31)),
        ("31.12.2027", date(2027, 12, 31)),
        ("31/12/27", date(2027, 12, 31)),
        ("31 Dec 2027", date(2027, 12, 31)),
        ("December 31, 2027", date(2027, 12, 31)),
        ("2027/12/31", date(2027, 12, 31)),
        ("2027-12-31 00:00:00", date(2027, 12, 31)),
    ],
)
def test_normalize_date_formats(raw, expected):
    parsed, error = normalize_date(raw)
    assert parsed == expected
    assert error is None


def test_normalize_date_invalid_and_empty():
    assert normalize_date("") == (None, None)
    assert normalize_date(None) == (None, None)
    assert normalize_date("NULL") == (None, None)
    parsed, error = normalize_date("32/13/2022")
    assert parsed is None
    assert error is not None


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("100", 100),
        ("1,000", 1000),
        (" 250 ", 250),
        ("100.0", 100),
        ("", None),
        (None, None),
        ("NULL", None),
        ("n/a", None),
    ],
)
def test_parse_int_ok(raw, expected):
    value, error = parse_int(raw)
    assert value == expected
    assert error is None


def test_parse_int_invalid():
    value, error = parse_int("abc")
    assert value is None
    assert error is not None


def test_parse_int_non_integral_float_is_error():
    value, error = parse_int("100.5")
    assert value is None
    assert error is not None


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("ERNAKULAM", "Ernakulam"),
        ("ernakulam", "Ernakulam"),
        ("Trivandrum", "Thiruvananthapuram"),
        ("CALICUT", "Kozhikode"),
        ("palghat", "Palakkad"),
    ],
)
def test_normalize_district(raw, expected):
    assert normalize_district(raw) == expected


def test_normalize_district_unknown_is_titlecased():
    assert normalize_district("somewhere odd") == "Somewhere Odd"


def test_normalize_status_and_type():
    assert normalize_status("registered") == "Registered"
    assert normalize_status("under construction") == "Ongoing"
    assert normalize_project_type("apartments") == "Apartment"
    assert normalize_project_type("mixed use") == "Mixed"


def test_unknown_status_preserved_verbatim():
    # Source text is preserved, not title-cased or remapped.
    assert normalize_status("Inprogress") == "Inprogress"
    assert normalize_status("Weird Status") == "Weird Status"


def test_unknown_project_type_preserved_verbatim():
    assert (
        normalize_project_type("Residential (Apartment)") == "Residential (Apartment)"
    )
    assert (
        normalize_project_type("Shops/Office Space (Commercial)")
        == "Shops/Office Space (Commercial)"
    )


def test_plots_value_is_preserved():
    assert normalize_project_type("Plots") == "Plots"


def test_normalize_record_emits_issue_for_bad_values():
    raw = RawProjectRecord(
        source_row_number=1,
        raw_row={"x": "1"},
        rera_registration_number="X",
        project_name="P",
        declared_completion_date="not-a-date",
        total_units="1,2,3",
    )
    normalized, issues = normalize_record(raw)

    assert normalized.rera_registration_number == "X"
    assert normalized.declared_completion_date is None
    assert any(i.field_name == "declared_completion_date" for i in issues)
    assert any(i.field_name == "total_units" for i in issues)
    # Raw values are preserved.
    assert normalized.raw_values["declared_completion_date"] == "not-a-date"


def test_source_hash_is_deterministic_and_sensitive():
    base = NormalizedProject(
        rera_registration_number="X",
        project_name="P",
        declared_completion_date=date(2027, 6, 30),
        sold_units=10,
    )
    same = NormalizedProject(
        rera_registration_number="X",
        project_name="P",
        declared_completion_date=date(2027, 6, 30),
        sold_units=10,
    )
    changed = NormalizedProject(
        rera_registration_number="X",
        project_name="P",
        declared_completion_date=date(2027, 12, 31),
        sold_units=10,
    )

    assert compute_source_hash(base) == compute_source_hash(same)
    assert compute_source_hash(base) != compute_source_hash(changed)
