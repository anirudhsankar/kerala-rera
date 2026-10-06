"""Parser tests: header mapping, canonicalisation and structural errors."""

from __future__ import annotations

from rera.ingestion.parser import (
    build_records_from_grid,
    normalize_header,
    parse_records,
)


def test_normalize_header_collapses_punctuation():
    assert normalize_header("RERA Registration Number") == "rera registration number"
    assert normalize_header("Total  Units ") == "total units"
    assert normalize_header("Declared-Completion_Date") == "declared completion date"


def test_parse_records_maps_columns():
    rows = [
        {
            "RERA Registration Number": "K-RERA/PRJ/ERK/001/2022",
            "Project Name": "Green Meadows",
            "Promoter Name": "ABC Builders",
            "Project Type": "Residential",
            "Project Status": "Registered",
            "Project Start Date": "01/02/2022",
            "Declared Completion Date": "31/12/2027",
            "Total Units": "120",
            "Sold Units": "45",
            "District": "Ernakulam",
        }
    ]
    result = parse_records(rows)

    assert len(result.records) == 1
    record = result.records[0]
    assert record.rera_registration_number == "K-RERA/PRJ/ERK/001/2022"
    assert record.project_name == "Green Meadows"
    assert record.total_units == "120"
    assert record.source_row_number == 1
    # Original columns are preserved verbatim.
    assert record.raw_row["Project Name"] == "Green Meadows"
    assert not result.errors


def test_parse_records_reports_unmapped_and_missing_columns():
    rows = [{"Weird Column": "x", "Project Name": "Only Name"}]
    result = parse_records(rows)

    assert "Weird Column" in result.unmapped_columns
    assert "rera_registration_number" in result.missing_required_fields
    # Row still parsed (project name present) - we never silently drop rows.
    assert len(result.records) == 1


def test_parse_records_empty_row_is_an_error():
    rows = [{"RERA Registration Number": "", "Project Name": ""}]
    result = parse_records(rows)

    assert not result.records
    assert len(result.errors) == 1
    assert result.errors[0].row_number == 1


def test_parse_records_detects_duplicate_column_mapping():
    rows = [{"Project Name": "A", "Name Of Project": "B", "RERA Registration Number": "X"}]
    result = parse_records(rows)

    assert any("Multiple columns map to 'project_name'" in w for w in result.column_warnings)


def test_real_export_headers_map_expected_fields():
    columns = [
        "Project",
        "Promoter Name",
        "Project Type",
        "Project Start Date",
        "Date of Completion",
        "Certificate No",
        "Certificate Date",
        "Total",
        "Sold",
        "Status",
        "District",
        "Village",
        "Taluk",
    ]
    rows = [
        {
            "Project": "THE GARDENIA",
            "Promoter Name": "FAVOURITE",
            "Project Type": "Residential (Apartment)",
            "Project Start Date": "2019-12-01",
            "Date of Completion": "2023-05-29",
            "Certificate No": "K-RERA/PRJ/005/2020",
            "Certificate Date": "2021-03-30",
            "Total": "1",
            "Sold": "1",
            "Status": "Completed",
            "District": "Thiruvananthapuram",
            "Village": "ATTIPRA",
            "Taluk": "Thiruvananathapuram",
        }
    ]
    result = parse_records(rows, columns)

    assert not result.missing_required_fields
    assert result.unmapped_columns == []
    record = result.records[0]
    # 'Certificate No' feeds BOTH the identity and certificate_number.
    assert record.rera_registration_number == "K-RERA/PRJ/005/2020"
    assert record.certificate_number == "K-RERA/PRJ/005/2020"
    assert record.project_name == "THE GARDENIA"
    assert record.total_units == "1"
    assert record.sold_units == "1"
    assert record.declared_completion_date == "2023-05-29"


def test_build_records_from_grid_detects_header_after_preamble():
    grid = [
        ["Kerala Real Estate Regulatory Authority", "", ""],
        ["Project", "Certificate No", "Status"],
        ["Alpha", "K-RERA/PRJ/001/2020", "Completed"],
        ["Beta", "K-RERA/PRJ/002/2020", "Inprogress"],
    ]
    built = build_records_from_grid(grid)

    assert built.header_row == 1  # preamble skipped
    assert built.columns == ["Project", "Certificate No", "Status"]
    assert len(built.rows) == 2
    assert built.rows[0]["Project"] == "Alpha"


def test_build_records_from_grid_drops_empty_rows():
    grid = [
        ["Project", "Status"],
        ["Alpha", "Completed"],
        ["", ""],
        ["Beta", "Inprogress"],
    ]
    built = build_records_from_grid(grid)
    assert [r["Project"] for r in built.rows] == ["Alpha", "Beta"]

