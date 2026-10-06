"""Read-only HTTP API for the K-RERA analytics dashboard.

All endpoints are GET and read-only. Derived metrics are labelled; the API
never returns interpretive judgements such as "delayed" or "bad promoter".
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from rera.analytics import queries
from rera.api.deps import get_session

app = FastAPI(
    title="Kerala RERA Intelligence API",
    version="0.1.0",
    description=(
        "Read-only analytics over publicly available Kerala RERA project data. "
        "Derived metrics are labelled; no interpretive judgements are produced."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)

SessionDep = Annotated[Session, Depends(get_session)]


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/overview", tags=["analytics"])
def overview(session: SessionDep) -> dict:
    return queries.overview(session)


@app.get("/api/timeline", tags=["analytics"])
def timeline(
    session: SessionDep,
    granularity: Annotated[str, Query(pattern="^(year|month)$")] = "year",
) -> dict:
    return queries.timeline(session, granularity)


@app.get("/api/districts", tags=["analytics"])
def districts(session: SessionDep) -> list[dict]:
    return queries.by_district(session)


@app.get("/api/districts/{district}", tags=["analytics"])
def district(district: str, session: SessionDep) -> dict:
    data = queries.district_detail(session, district)
    if data is None:
        raise HTTPException(status_code=404, detail="District not found")
    return data


@app.get("/api/builders", tags=["analytics"])
def builders(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    sort: Annotated[
        str, Query(pattern="^(projects|total_units|sold_units|districts)$")
    ] = "projects",
) -> list[dict]:
    return queries.by_builder(session, limit=limit, sort=sort)


@app.get("/api/builders/{promoter_id}", tags=["analytics"])
def builder(promoter_id: int, session: SessionDep) -> dict:
    data = queries.builder_detail(session, promoter_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Builder not found")
    return data


@app.get("/api/projects", tags=["projects"])
def projects(
    session: SessionDep,
    q: str | None = None,
    district: str | None = None,
    project_type: str | None = None,
    project_status: str | None = None,
    promoter_id: int | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    return queries.search_projects(
        session,
        q=q,
        district=district,
        project_type=project_type,
        project_status=project_status,
        promoter_id=promoter_id,
        limit=limit,
        offset=offset,
    )


@app.get("/api/project", tags=["projects"])
def project(registration_number: str, session: SessionDep) -> dict:
    data = queries.get_project(session, registration_number)
    if data is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return data


@app.get("/api/project/history", tags=["projects"])
def project_history(registration_number: str, session: SessionDep) -> list[dict]:
    return queries.project_history(session, registration_number)


@app.get("/api/project/changes", tags=["projects"])
def project_changes(registration_number: str, session: SessionDep) -> list[dict]:
    return queries.project_changes(session, registration_number)


@app.get("/api/filters", tags=["meta"])
def filters(session: SessionDep) -> dict:
    return queries.filter_options(session)


@app.get("/api/runs", tags=["meta"])
def ingestion_runs(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 20,
) -> list[dict]:
    return queries.runs(session, limit)


@app.get("/api/baseline", tags=["meta"])
def baseline(session: SessionDep) -> dict | None:
    return queries.baseline(session)


@app.get("/api/data-quality/summary", tags=["meta"])
def data_quality(session: SessionDep) -> dict:
    return queries.data_quality_summary(session)
