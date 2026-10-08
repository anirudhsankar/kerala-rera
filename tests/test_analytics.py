"""Analytics layer tests over a small seeded fixture database."""

from __future__ import annotations

from datetime import date

from rera.analytics import queries
from rera.analytics.promoters import build_promoters, canonical_key
from rera.database.models import Project, Promoter


def _add(session, reg, **kwargs):
    project = Project(rera_registration_number=reg, **kwargs)
    session.add(project)
    return project


def _seed(session):
    promoter = Promoter(canonical_name="Acme Builders", normalized_key="ACME BUILDERS")
    session.add(promoter)
    session.flush()

    _add(
        session,
        "R1",
        project_name="Alpha",
        district="Ernakulam",
        taluk="Kanayannur",
        village="KAKKANAD",
        project_type="Residential (Apartment)",
        project_status="Completed",
        project_start_date=date(2020, 1, 1),
        declared_completion_date=date(2023, 1, 1),
        certificate_date=date(2021, 5, 1),
        total_units=100,
        sold_units=40,
        promoter_id=promoter.id,
    )
    _add(
        session,
        "R2",
        project_name="Beta",
        district="Ernakulam",
        taluk="Kanayannur",
        village="EDAPPALLY",
        project_type="Plots",
        project_status="Inprogress",
        project_start_date=date(2022, 1, 1),
        declared_completion_date=date(2030, 1, 1),
        certificate_date=date(2021, 6, 1),
        total_units=50,
        sold_units=50,
        promoter_id=promoter.id,
    )
    _add(
        session,
        "R3",
        project_name="Gamma",
        district="Kollam",
        taluk="Kollam",
        village="SASTHAMANGALAM",
        project_type="Plots",
        project_status="Inprogress",
        project_start_date=date(2021, 1, 1),
        declared_completion_date=date(2000, 1, 1),
        certificate_date=date(2022, 1, 1),
        total_units=None,
        sold_units=10,
    )
    session.commit()


def test_overview_metrics(session):
    _seed(session)
    ov = queries.overview(session, today=date(2026, 1, 1))

    assert ov["total_projects"] == 3
    assert ov["total_units"] == 150
    assert ov["sold_units"] == 100
    assert ov["sell_through"] == round(100 / 150, 4)
    assert ov["projects_with_units"] == 2
    assert ov["projects_without_units"] == 1
    assert ov["declared_completion_date_passed"] == 2
    assert "sell_through" in ov["derived_metrics"]


def test_by_district(session):
    _seed(session)
    districts = {d["district"]: d for d in queries.by_district(session)}

    assert districts["Ernakulam"]["projects"] == 2
    assert districts["Ernakulam"]["completed"] == 1
    assert districts["Ernakulam"]["inprogress"] == 1
    assert districts["Kollam"]["projects"] == 1
    assert districts["Kollam"]["total_units"] == 0  # null total excluded from sum


def test_by_builder_and_detail(session):
    _seed(session)
    builders = queries.by_builder(session)
    acme = next(b for b in builders if b["name"] == "Acme Builders")
    assert acme["projects"] == 2
    assert acme["districts"] == 1

    detail = queries.builder_detail(session, acme["promoter_id"])
    assert detail is not None
    assert detail["summary"]["projects"] == 2
    assert {d["district"] for d in detail["by_district"]} == {"Ernakulam"}


def test_timeline(session):
    _seed(session)
    tl = queries.timeline(session, "year")
    regs = {d["period"]: d["count"] for d in tl["registrations"]}
    assert regs["2021"] == 2
    assert regs["2022"] == 1


def test_search_and_get_project(session):
    _seed(session)
    page = queries.search_projects(session, district="Ernakulam")
    assert page["total"] == 2
    assert all(item["district"] == "Ernakulam" for item in page["items"])

    detail = queries.get_project(session, "R1")
    assert detail is not None
    assert detail["project_name"] == "Alpha"
    assert detail["promoter_canonical_name"] == "Acme Builders"


def test_build_promoters_flags_variants_and_links(session):
    # Two raw spellings that collapse to the same key.
    for reg, raw in [("P1", "Sobha Limited"), ("P2", "SOBHA LIMITED")]:
        _add(session, reg, project_name=reg, promoter_name_raw=raw)
    session.commit()

    result = build_promoters(session)

    assert result.groups == 1
    assert result.created == 1
    assert result.projects_linked == 2
    assert result.needs_review == 1
    assert result.review_examples[0]["normalized_key"] == "SOBHA LIMITED"


def test_canonical_key_normalisation():
    assert canonical_key("  Sobha   Limited ") == "SOBHA LIMITED"
    assert canonical_key("Sobha-Limited") == "SOBHA LIMITED"
    assert canonical_key("A.B.C. Builders") == "A B C BUILDERS"

def test_location_filters_and_newest_sort(session):
    _seed(session)
    assert queries.search_projects(session, taluk="Kanayannur")["total"] == 2
    assert queries.search_projects(session, village="KAKKANAD")["total"] == 1
    newest = queries.search_projects(session, sort="newest")
    assert newest["items"][0]["rera_registration_number"] == "R3"  # registered 2022


def test_by_taluk_and_taluk_detail(session):
    _seed(session)
    taluks = {t["taluk"]: t for t in queries.by_taluk(session, district="Ernakulam")}
    assert taluks["Kanayannur"]["projects"] == 2
    assert taluks["Kanayannur"]["total_units"] == 150
    detail = queries.taluk_detail(session, "Ernakulam", "Kanayannur")
    assert detail is not None
    assert detail["summary"]["projects"] == 2
    assert {v["village"] for v in detail["villages"]} == {"KAKKANAD", "EDAPPALLY"}


def test_taluks_and_villages_for(session):
    _seed(session)
    taluks = queries.taluks_for_district(session, "Ernakulam")
    assert taluks[0]["taluk"] == "Kanayannur" and taluks[0]["projects"] == 2
    villages = queries.villages_for(session, district="Ernakulam", taluk="Kanayannur")
    assert {v["village"] for v in villages} == {"KAKKANAD", "EDAPPALLY"}


def test_recent_projects(session):
    _seed(session)
    recent = queries.recent_projects(session, months=120)
    assert recent["total"] == 3
    assert recent["items"][0]["rera_registration_number"] == "R3"
