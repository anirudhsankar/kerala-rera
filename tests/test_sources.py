"""Tests for source helpers: download parsing + anti-bot detection."""

from __future__ import annotations

from rera.sources.krera import _looks_like_challenge, _records_from_bytes, _suffix_for


def test_suffix_for_prefers_url_extension():
    assert _suffix_for("https://x/export.csv", None) == ".csv"
    assert _suffix_for("https://x/export.xlsx?token=1", "text/html") == ".xlsx"


def test_suffix_for_falls_back_to_content_type():
    assert _suffix_for("https://x/download", "application/vnd.ms-excel") == ".xlsx"
    assert _suffix_for("https://x/blob", "text/csv; charset=utf-8") == ".csv"


def test_records_from_csv_bytes():
    data = (
        b"Project,Certificate No,Status\n"
        b"Alpha,K-RERA/PRJ/001/2020,Completed\n"
        b"Beta,K-RERA/PRJ/002/2020,Inprogress\n"
    )
    rows, columns = _records_from_bytes(data, ".csv")
    assert columns == ["Project", "Certificate No", "Status"]
    assert rows[0]["Project"] == "Alpha"
    assert rows[1]["Certificate No"] == "K-RERA/PRJ/002/2020"


def test_challenge_detection():
    assert _looks_like_challenge(
        '<script src="https://prophaze-botmodule-static-assets.s3.amazonaws.com/aes.min.js"></script>'
    )
    assert not _looks_like_challenge("Project,Status\nAlpha,Completed\n")
