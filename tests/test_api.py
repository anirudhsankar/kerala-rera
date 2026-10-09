"""API tests using FastAPI's TestClient over a seeded fixture database."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from rera.api.app import app
from rera.api.deps import get_session
from rera.database.models import Project, ProjectChangeEvent, Promoter


def _seed(session):
    promoter = Promoter(canonical_name="Acme Builders", normalized_key="ACME BUILDERS")
    session.add(promoter)
    session.flush()
    session.add_all(
        [
            Project(
                rera_registration_number="R1",
                project_name="Alpha",
                district="Ernakulam",
                taluk="Kanayannur",
                village="KAKKANAD",
                project_type="Residential (Apartment)",
                project_status="Completed",
                certificate_date=date(2021, 5, 1),
                declared_completion_date=date(2023, 1, 1),
                total_units=100,
                sold_units=40,
                promoter_id=promoter.id,
            ),
            Project(
                rera_registration_number="R2",
                project_name="Beta",
                district="Kollam",
                taluk="Kollam",
                village="SASTHAMANGALAM",
                project_type="Plots",
                project_status="Inprogress",
                certificate_date=date(2022, 1, 1),
                declared_completion_date=date(2000, 1, 1),
                total_units=None,
                sold_units=5,
            ),
        ]
    )
    session.commit()

    project = session.execute(
        select(Project).where(Project.rera_registration_number == "R1")
    ).scalar_one()
    session.add(
        ProjectChangeEvent(
            project_id=project.id,
            field_name="sold_units",
            old_value="10",
            new_value="40",
            detected_at=datetime(2026, 1, 10, tzinfo=UTC),
        )
    )
    session.commit()


@pytest.fixture()
def client(session):
    _seed(session)

    def override():
        yield session

    app.dependency_overrides[get_session] = override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_overview(client):
    body = client.get("/api/overview").json()
    assert body["total_projects"] == 2
    assert body["total_units"] == 100
    assert body["sold_units"] == 45


def test_districts(client):
    body = client.get("/api/districts").json()
    assert {d["district"] for d in body} == {"Ernakulam", "Kollam"}


def test_district_not_found(client):
    assert client.get("/api/districts/Nowhere").status_code == 404


def test_builders(client):
    body = client.get("/api/builders").json()
    assert body[0]["name"] == "Acme Builders"
    assert body[0]["projects"] == 1


def test_projects_search_and_detail(client):
    page = client.get("/api/projects", params={"district": "Ernakulam"}).json()
    assert page["total"] == 1
    assert page["items"][0]["rera_registration_number"] == "R1"

    detail = client.get(
        "/api/project", params={"registration_number": "R1"}
    ).json()
    assert detail["project_name"] == "Alpha"
    assert detail["promoter_canonical_name"] == "Acme Builders"


def test_project_not_found(client):
    response = client.get("/api/project", params={"registration_number": "missing"})
    assert response.status_code == 404


def test_filters_and_baseline(client):
    filters = client.get("/api/filters").json()
    assert "Ernakulam" in filters["districts"]
    assert client.get("/api/baseline").json() is None


def test_locations_cascading_and_new(client):
    taluks = client.get("/api/locations/taluks", params={"district": "Ernakulam"}).json()
    assert taluks[0]["taluk"] == "Kanayannur"
    villages = client.get(
        "/api/locations/villages", params={"district": "Ernakulam", "taluk": "Kanayannur"}
    ).json()
    assert villages[0]["village"] == "KAKKANAD"
    by_taluk = client.get("/api/locations/by-taluk", params={"district": "Ernakulam"}).json()
    assert by_taluk[0]["taluk"] == "Kanayannur"
    detail = client.get(
        "/api/locations/taluk", params={"district": "Ernakulam", "taluk": "Kanayannur"}
    ).json()
    assert detail["summary"]["projects"] == 1


def test_project_taluk_filter_and_new(client):
    assert client.get("/api/projects", params={"taluk": "Kanayannur"}).json()["total"] == 1
    new = client.get("/api/projects/new", params={"months": 120}).json()
    assert new["total"] >= 1


def test_filters_cascade(client):
    body = client.get("/api/filters", params={"district": "Ernakulam"}).json()
    assert "Kanayannur" in body["taluks"]
    body2 = client.get(
        "/api/filters", params={"district": "Ernakulam", "taluk": "Kanayannur"}
    ).json()
    assert "KAKKANAD" in body2["villages"]


def test_changes_and_history(client):
    body = client.get("/api/changes").json()
    assert body["total"] >= 1
    assert body["items"][0]["field_name"] == "sold_units"
    summary = client.get("/api/history/summary").json()
    assert summary["total_changes"] >= 1
    assert summary["projects_changed"] >= 1


def test_overdue_endpoints(client):
    body = client.get("/api/overdue").json()
    assert body["total"] == 1
    assert body["items"][0]["rera_registration_number"] == "R2"
    assert body["items"][0]["days_past_completion"] > 0
    summary = client.get("/api/overdue/summary").json()
    assert summary["total"] == 1
    assert summary["by_district"][0]["district"] == "Kollam"


def test_market_endpoints(client):
    unsold = client.get("/api/market/unsold").json()
    assert unsold["total_units"] == 100
    assert unsold["undisclosed_projects"] == 1
    assert client.get("/api/market/pipeline").status_code == 200
    reg = client.get("/api/market/registrations", params={"granularity": "month"}).json()
    assert "periods" in reg and reg["periods"]
    assert client.get("/api/market/mix").status_code == 200
    concentration = client.get("/api/market/concentration").json()
    assert concentration["total_units"] == 100


def test_builder_detail_completion_counts(client):
    builders = client.get("/api/builders").json()
    detail = client.get(f"/api/builders/{builders[0]['promoter_id']}").json()
    assert "completed" in detail["summary"]
    assert "past_due_count" in detail["summary"]
