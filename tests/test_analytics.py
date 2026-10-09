"""Analytics layer tests over a small seeded fixture database."""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select

from rera.analytics import queries
from rera.analytics.promoters import build_promoters, canonical_key
from rera.database.models import Project, ProjectChangeEvent, Promoter


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


def test_history_queries(session):
    _seed(session)
    project = session.execute(
        select(Project).where(Project.rera_registration_number == "R1")
    ).scalar_one()
    session.add(
        ProjectChangeEvent(
            project_id=project.id,
            field_name="project_status",
            old_value="Ongoing",
            new_value="Completed",
            detected_at=datetime(2026, 1, 15, tzinfo=UTC),
        )
    )
    session.commit()

    changes = queries.recent_changes(session)
    assert changes["total"] == 1
    assert changes["items"][0]["field_name"] == "project_status"
    assert changes["items"][0]["district"] == "Ernakulam"

    summary = queries.history_summary(session)
    assert summary["total_changes"] == 1
    assert summary["projects_changed"] == 1
    assert any(f["field_name"] == "project_status" for f in summary["changes_by_field"])
    assert summary["status_transitions"][0]["count"] == 1


def test_overdue_queries(session):
    _seed(session)
    rows = queries.overdue_projects(session)
    assert rows["total"] == 1  # R3 (Inprogress, completion 2000); R1 Completed, R2 future
    assert rows["items"][0]["rera_registration_number"] == "R3"
    assert rows["items"][0]["days_past_completion"] > 0
    summary = queries.overdue_summary(session)
    assert summary["total"] == 1
    assert summary["by_district"][0]["district"] == "Kollam"


def test_unsold_inventory(session):
    _seed(session)
    inv = queries.unsold_inventory(session)
    assert inv["total_units"] == 150
    assert inv["sold_units"] == 100
    assert inv["unsold_units"] == 50
    assert inv["undisclosed_projects"] == 1


def test_supply_pipeline_and_registration_trend(session):
    _seed(session)
    pipe = {p["year"]: p for p in queries.supply_pipeline(session)}
    assert pipe[2030]["units"] == 50 and pipe[2030]["projects"] == 1
    assert 2000 in pipe and pipe[2000]["units"] == 0

    t = queries.registration_trend(session, "month")
    assert t["periods"] == ["2021-05", "2021-06", "2022-01"]
    assert t["series"][0]["data"] == [1, 1, 1]
    tq = queries.registration_trend(session, "quarter", by_type=True)
    assert "2021-Q2" in tq["periods"]


def test_builder_concentration_and_detail(session):
    _seed(session)
    c = queries.builder_concentration(session)
    assert c["total_units"] == 150
    assert c["top10_share"] == 1.0

    acme = next(b for b in queries.by_builder(session) if b["name"] == "Acme Builders")
    detail = queries.builder_detail(session, acme["promoter_id"])
    assert detail["summary"]["completed"] == 1
    assert detail["summary"]["inprogress"] == 1
    assert detail["summary"]["past_due_count"] == 0
