"""Read-only analytics queries over the K-RERA dataset.

All functions take a SQLAlchemy ``Session`` and return plain Python structures
(dicts / lists) so they can be reused by the API, the CLI or tests. Nothing in
this module writes to the database.

Derived metrics are returned alongside the source facts they are computed from.
The system never labels a project as "delayed" or a promoter as "bad"; it only
reports factual counts (e.g. "declared completion date has passed").
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import case, extract, func, or_, select
from sqlalchemy.orm import Session

from rera.database.models import (
    Baseline,
    DataQualityIssue,
    IngestionRun,
    Project,
    ProjectChangeEvent,
    ProjectSnapshot,
    Promoter,
)


def _int(value: Any) -> int:
    return int(value) if value is not None else 0


def _sell_through(sold: int, total: int) -> float | None:
    if not total:
        return None
    return round(sold / total, 4)


def _period(year: Any, month: Any = None) -> str:
    if month is None:
        return str(int(year))
    return f"{int(year)}-{int(month):02d}"


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
def overview(session: Session, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()

    total_projects = session.execute(select(func.count()).select_from(Project)).scalar_one()

    by_status = [
        {"status": status, "count": count}
        for status, count in session.execute(
            select(Project.project_status, func.count())
            .group_by(Project.project_status)
            .order_by(func.count().desc())
        ).all()
    ]
    by_type = [
        {"type": project_type, "count": count}
        for project_type, count in session.execute(
            select(Project.project_type, func.count())
            .group_by(Project.project_type)
            .order_by(func.count().desc())
        ).all()
    ]

    row = session.execute(
        select(
            func.count(Project.total_units),
            func.coalesce(func.sum(Project.total_units), 0),
            func.coalesce(func.sum(Project.sold_units), 0),
        )
    ).one()
    projects_with_units = _int(row[0])
    total_units = _int(row[1])
    sold_units = _int(row[2])

    completion_passed = session.execute(
        select(func.count())
        .select_from(Project)
        .where(
            Project.declared_completion_date.is_not(None),
            Project.declared_completion_date < today,
        )
    ).scalar_one()

    return {
        "total_projects": total_projects,
        "total_units": total_units,
        "sold_units": sold_units,
        "sell_through": _sell_through(sold_units, total_units),
        "units_under_development": total_units - sold_units,
        "projects_with_units": projects_with_units,
        "projects_without_units": total_projects - projects_with_units,
        "declared_completion_date_passed": completion_passed,
        "by_status": by_status,
        "by_type": by_type,
        "derived_metrics": [
            "sell_through",
            "units_under_development",
            "declared_completion_date_passed",
        ],
    }


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------
def timeline(session: Session, granularity: str = "year") -> dict[str, Any]:
    if granularity not in {"year", "month"}:
        raise ValueError("granularity must be 'year' or 'month'")

    def _grouped(column) -> list[dict[str, Any]]:
        if granularity == "year":
            key = extract("year", column)
            rows = session.execute(
                select(key, func.count())
                .where(column.is_not(None))
                .group_by(key)
                .order_by(key)
            ).all()
            return [{"period": _period(year), "count": count} for year, count in rows]
        year = extract("year", column)
        month = extract("month", column)
        month_rows = session.execute(
            select(year, month, func.count())
            .where(column.is_not(None))
            .group_by(year, month)
            .order_by(year, month)
        ).all()
        return [
            {"period": _period(y, m), "count": count} for y, m, count in month_rows
        ]

    return {
        "granularity": granularity,
        "registrations": _grouped(Project.certificate_date),
        "declared_completions": _grouped(Project.declared_completion_date),
        "note": "Derived from source dates (certificate_date / declared_completion_date).",
    }


# ---------------------------------------------------------------------------
# District
# ---------------------------------------------------------------------------
def by_district(session: Session) -> list[dict[str, Any]]:
    completed = func.sum(case((Project.project_status == "Completed", 1), else_=0))
    rows = session.execute(
        select(
            Project.district,
            func.count(),
            func.coalesce(func.sum(Project.total_units), 0),
            func.coalesce(func.sum(Project.sold_units), 0),
            completed,
        )
        .group_by(Project.district)
        .order_by(func.count().desc())
    ).all()

    result = []
    for district, projects, total_units, sold_units, completed_count in rows:
        total_units = _int(total_units)
        sold_units = _int(sold_units)
        result.append(
            {
                "district": district,
                "projects": projects,
                "total_units": total_units,
                "sold_units": sold_units,
                "sell_through": _sell_through(sold_units, total_units),
                "completed": _int(completed_count),
                "inprogress": projects - _int(completed_count),
            }
        )
    return result


def district_detail(session: Session, district: str) -> dict[str, Any] | None:
    base = select(Project).where(Project.district == district)
    projects = session.execute(base).scalars().all()
    if not projects:
        return None

    total_units = sum(p.total_units or 0 for p in projects)
    sold_units = sum(p.sold_units or 0 for p in projects)
    completed = sum(1 for p in projects if p.project_status == "Completed")

    by_type: dict[str, int] = {}
    taluks: dict[str, int] = {}
    builders: dict[int | None, int] = {}
    for project in projects:
        by_type[project.project_type or "Unknown"] = (
            by_type.get(project.project_type or "Unknown", 0) + 1
        )
        taluks[project.taluk or "Unknown"] = taluks.get(project.taluk or "Unknown", 0) + 1
        builders[project.promoter_id] = builders.get(project.promoter_id, 0) + 1

    promoter_names = {}
    ids = [pid for pid in builders if pid is not None]
    if ids:
        promoter_names = {
            pid: name
            for pid, name in session.execute(
                select(Promoter.id, Promoter.canonical_name).where(Promoter.id.in_(ids))
            ).all()
        }

    top_builders: list[dict[str, Any]] = [
        {
            "promoter_id": pid,
            "name": promoter_names.get(pid, "Unknown") if pid is not None else "Unknown",
            "projects": count,
        }
        for pid, count in builders.items()
    ]
    top_builders.sort(key=lambda item: int(item["projects"]), reverse=True)
    top_builders = top_builders[:10]

    return {
        "district": district,
        "summary": {
            "projects": len(projects),
            "total_units": total_units,
            "sold_units": sold_units,
            "sell_through": _sell_through(sold_units, total_units),
            "completed": completed,
            "inprogress": len(projects) - completed,
        },
        "by_type": [
            {"type": name, "count": count}
            for name, count in sorted(by_type.items(), key=lambda kv: -kv[1])
        ],
        "taluks": [
            {"taluk": name, "count": count}
            for name, count in sorted(taluks.items(), key=lambda kv: -kv[1])
        ],
        "top_builders": top_builders,
    }


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------
def by_builder(session: Session, *, limit: int = 50, sort: str = "projects") -> list[dict[str, Any]]:
    rows = session.execute(
        select(
            Promoter.id,
            Promoter.canonical_name,
            Promoter.needs_review,
            func.count(Project.id),
            func.coalesce(func.sum(Project.total_units), 0),
            func.coalesce(func.sum(Project.sold_units), 0),
            func.count(func.distinct(Project.district)),
        )
        .join(Project, Project.promoter_id == Promoter.id)
        .group_by(Promoter.id, Promoter.canonical_name, Promoter.needs_review)
    ).all()

    builders = []
    for pid, name, needs_review, projects, total_units, sold_units, districts in rows:
        total_units = _int(total_units)
        sold_units = _int(sold_units)
        builders.append(
            {
                "promoter_id": pid,
                "name": name,
                "needs_review": bool(needs_review),
                "projects": projects,
                "total_units": total_units,
                "sold_units": sold_units,
                "sell_through": _sell_through(sold_units, total_units),
                "districts": int(districts),
            }
        )

    sort_keys = {"projects", "total_units", "sold_units", "districts"}
    key = sort if sort in sort_keys else "projects"
    builders.sort(key=lambda item: (item[key], item["projects"]), reverse=True)
    return builders[:limit]


def builder_detail(session: Session, promoter_id: int) -> dict[str, Any] | None:
    promoter = session.get(Promoter, promoter_id)
    if promoter is None:
        return None

    projects = session.execute(
        select(Project).where(Project.promoter_id == promoter_id)
    ).scalars().all()

    total_units = sum(p.total_units or 0 for p in projects)
    sold_units = sum(p.sold_units or 0 for p in projects)

    by_district: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for project in projects:
        by_district[project.district or "Unknown"] = (
            by_district.get(project.district or "Unknown", 0) + 1
        )
        by_type[project.project_type or "Unknown"] = (
            by_type.get(project.project_type or "Unknown", 0) + 1
        )

    return {
        "promoter_id": promoter.id,
        "name": promoter.canonical_name,
        "needs_review": promoter.needs_review,
        "match_method": promoter.match_method,
        "summary": {
            "projects": len(projects),
            "total_units": total_units,
            "sold_units": sold_units,
            "sell_through": _sell_through(sold_units, total_units),
        },
        "by_district": [
            {"district": name, "count": count}
            for name, count in sorted(by_district.items(), key=lambda kv: -kv[1])
        ],
        "by_type": [
            {"type": name, "count": count}
            for name, count in sorted(by_type.items(), key=lambda kv: -kv[1])
        ],
        "projects": [_project_brief(p) for p in projects],
    }


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
def _project_brief(project: Project) -> dict[str, Any]:
    return {
        "rera_registration_number": project.rera_registration_number,
        "project_name": project.project_name,
        "promoter_name_raw": project.promoter_name_raw,
        "promoter_id": project.promoter_id,
        "project_type": project.project_type,
        "project_status": project.project_status,
        "project_start_date": _iso(project.project_start_date),
        "declared_completion_date": _iso(project.declared_completion_date),
        "certificate_number": project.certificate_number,
        "certificate_date": _iso(project.certificate_date),
        "total_units": project.total_units,
        "sold_units": project.sold_units,
        "district": project.district,
        "taluk": project.taluk,
        "village": project.village,
    }


def _iso(value: Any) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else value


def search_projects(
    session: Session,
    *,
    q: str | None = None,
    district: str | None = None,
    project_type: str | None = None,
    project_status: str | None = None,
    promoter_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    filters = []
    if q:
        like = f"%{q}%"
        filters.append(
            or_(
                Project.project_name.ilike(like),
                Project.rera_registration_number.ilike(like),
                Project.promoter_name_raw.ilike(like),
            )
        )
    if district:
        filters.append(Project.district == district)
    if project_type:
        filters.append(Project.project_type == project_type)
    if project_status:
        filters.append(Project.project_status == project_status)
    if promoter_id:
        filters.append(Project.promoter_id == promoter_id)

    total = session.execute(
        select(func.count()).select_from(Project).where(*filters)
    ).scalar_one()

    items = (
        session.execute(
            select(Project)
            .where(*filters)
            .order_by(Project.district, Project.project_name)
            .limit(limit)
            .offset(offset)
        )
        .scalars()
        .all()
    )

    return {"total": total, "limit": limit, "offset": offset, "items": [_project_brief(p) for p in items]}


def get_project(session: Session, registration_number: str) -> dict[str, Any] | None:
    project = session.execute(
        select(Project).where(Project.rera_registration_number == registration_number)
    ).scalar_one_or_none()
    if project is None:
        return None
    data = _project_brief(project)
    data["not_seen_in_latest_run"] = project.not_seen_in_latest_run
    data["first_seen_at"] = _iso(project.first_seen_at)
    data["last_seen_at"] = _iso(project.last_seen_at)
    data["last_checked_at"] = _iso(project.last_checked_at)
    if project.promoter_id:
        promoter = session.get(Promoter, project.promoter_id)
        data["promoter_canonical_name"] = promoter.canonical_name if promoter else None
    return data


def project_history(session: Session, registration_number: str) -> list[dict[str, Any]]:
    project = session.execute(
        select(Project).where(Project.rera_registration_number == registration_number)
    ).scalar_one_or_none()
    if project is None:
        return []
    snapshots = (
        session.execute(
            select(ProjectSnapshot)
            .where(ProjectSnapshot.project_id == project.id)
            .order_by(ProjectSnapshot.id)
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": s.id,
            "snapshot_date": _iso(s.snapshot_date),
            "collected_at": _iso(s.collected_at),
            "source_hash": s.source_hash,
            "project_status": s.project_status,
            "declared_completion_date": _iso(s.declared_completion_date),
            "total_units": s.total_units,
            "sold_units": s.sold_units,
        }
        for s in snapshots
    ]


def project_changes(session: Session, registration_number: str) -> list[dict[str, Any]]:
    project = session.execute(
        select(Project).where(Project.rera_registration_number == registration_number)
    ).scalar_one_or_none()
    if project is None:
        return []
    events = (
        session.execute(
            select(ProjectChangeEvent)
            .where(ProjectChangeEvent.project_id == project.id)
            .order_by(ProjectChangeEvent.detected_at)
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": e.id,
            "detected_at": _iso(e.detected_at),
            "field_name": e.field_name,
            "old_value": e.old_value,
            "new_value": e.new_value,
        }
        for e in events
    ]


# ---------------------------------------------------------------------------
# Operations / data quality
# ---------------------------------------------------------------------------
def data_quality_summary(session: Session) -> dict[str, Any]:
    by_severity = {
        severity: count
        for severity, count in session.execute(
            select(DataQualityIssue.severity, func.count()).group_by(
                DataQualityIssue.severity
            )
        ).all()
    }
    by_type = [
        {"issue_type": issue_type, "count": count}
        for issue_type, count in session.execute(
            select(DataQualityIssue.issue_type, func.count())
            .group_by(DataQualityIssue.issue_type)
            .order_by(func.count().desc())
        ).all()
    ]
    return {
        "total": sum(by_severity.values()),
        "by_severity": by_severity,
        "by_type": by_type,
    }


def runs(session: Session, limit: int = 20) -> list[dict[str, Any]]:
    records = (
        session.execute(select(IngestionRun).order_by(IngestionRun.id.desc()).limit(limit))
        .scalars()
        .all()
    )
    return [
        {
            "id": r.id,
            "started_at": _iso(r.started_at),
            "completed_at": _iso(r.completed_at),
            "status": r.status,
            "source": r.source,
            "collection_method": r.collection_method,
            "parser_version": r.parser_version,
            "records_found": r.records_found,
            "inserted": r.records_inserted,
            "updated": r.records_updated,
            "unchanged": r.records_unchanged,
            "failed": r.records_failed,
        }
        for r in records
    ]


def baseline(session: Session) -> dict[str, Any] | None:
    record = session.execute(select(Baseline).order_by(Baseline.id).limit(1)).scalar_one_or_none()
    if record is None:
        return None
    return {
        "baseline_at": _iso(record.baseline_at),
        "source": record.source,
        "record_count": record.record_count,
        "parser_version": record.parser_version,
        "source_checksum": record.source_checksum,
    }


def filter_options(session: Session) -> dict[str, Any]:
    districts = [
        d for (d,) in session.execute(
            select(Project.district).distinct().order_by(Project.district)
        ).all()
        if d
    ]
    types = [
        t for (t,) in session.execute(
            select(Project.project_type).distinct().order_by(Project.project_type)
        ).all()
        if t
    ]
    statuses = [
        s for (s,) in session.execute(
            select(Project.project_status).distinct().order_by(Project.project_status)
        ).all()
        if s
    ]
    return {"districts": districts, "types": types, "statuses": statuses}
