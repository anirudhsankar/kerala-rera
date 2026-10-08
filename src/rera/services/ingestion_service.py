"""Ingestion orchestration service.

Coordinates collection, parsing, normalisation, validation, idempotent upsert,
snapshot creation, change detection and run logging. Also provides reporting
helpers used by the CLI (status / stats / export).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from rera.config import get_settings
from rera.constants import (
    RUN_STATUS_FAILED,
    RUN_STATUS_PARTIAL,
    RUN_STATUS_RUNNING,
    RUN_STATUS_SUCCESS,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARNING,
)
from rera.database.models import (
    Baseline,
    DataQualityIssue,
    IngestionRun,
    Project,
    ProjectChangeEvent,
    ProjectSnapshot,
    utcnow,
)
from rera.database.session import create_db_engine, create_session_factory
from rera.ingestion.change_detector import (
    ChangeEventData,
    detect_changes,
    normalized_values,
    project_values,
)
from rera.ingestion.collector import CollectedData, Collector, save_raw_artifact
from rera.ingestion.normalizer import NormalizedProject, compute_source_hash, normalize_record
from rera.ingestion.parser import ParseError, RawProjectRecord, parse_records
from rera.ingestion.quality import QualityIssue
from rera.ingestion.snapshot import build_snapshot
from rera.ingestion.validator import detect_duplicate_registrations, validate_record
from rera.logging_config import get_logger
from rera.sources.base import FetchResult, ReraSource
from rera.sources.krera import collection_method_for

logger = get_logger("rera.ingestion")


@dataclass
class IngestionReport:
    """Outcome of an ingestion run."""

    dry_run: bool
    status: str
    source: str
    collection_method: str
    parser_version: str
    source_reference: str | None = None
    raw_path: str | None = None
    run_id: int | None = None

    records_found: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_unchanged: int = 0
    records_failed: int = 0
    new_projects: int = 0
    changed_projects: int = 0
    duplicates: int = 0

    warnings: int = 0
    errors: int = 0
    infos: int = 0
    baseline_created: bool = False
    error_summary: str | None = None

    changes: list[ChangeEventData] = field(default_factory=list)
    issues: list[QualityIssue] = field(default_factory=list)
    parse_errors: list[ParseError] = field(default_factory=list)
    unmapped_columns: list[str] = field(default_factory=list)
    missing_required_fields: list[str] = field(default_factory=list)
    column_warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status in (RUN_STATUS_SUCCESS, RUN_STATUS_PARTIAL)

    def summary_lines(self) -> list[str]:
        lines = [
            "K-RERA INGESTION",
            f"  Source method:        {self.collection_method}",
            f"  Source found:         {self.records_found}",
            f"  New:                  {self.records_inserted}",
            f"  Changed:              {self.records_updated}",
            f"  Unchanged:            {self.records_unchanged}",
            f"  Failed:               {self.records_failed}",
            f"  Duplicates:           {self.duplicates}",
            f"  Validation warnings:  {self.warnings}",
            f"  Validation errors:    {self.errors}",
            f"  Change events:        {len(self.changes)}",
            f"  Status:               {self.status}",
        ]
        if self.unmapped_columns:
            lines.append(f"  Unmapped columns:     {', '.join(self.unmapped_columns)}")
        if self.missing_required_fields:
            lines.append(
                f"  Missing required:     {', '.join(self.missing_required_fields)}"
            )
        if self.baseline_created:
            lines.append("  Baseline:             created")
        if self.dry_run:
            lines.append("  Database changes:     NOT COMMITTED (dry run)")
        if self.raw_path:
            lines.append(f"  Raw artefact:         {self.raw_path}")
        if self.error_summary:
            lines.append(f"  Error summary:        {self.error_summary}")
        return lines


def _project_from_normalized(normalized: NormalizedProject) -> Project:
    return Project(
        rera_registration_number=normalized.rera_registration_number or "",
        project_name=normalized.project_name,
        promoter_name_raw=normalized.promoter_name,
        project_type=normalized.project_type,
        project_status=normalized.project_status,
        project_start_date=normalized.project_start_date,
        declared_completion_date=normalized.declared_completion_date,
        certificate_number=normalized.certificate_number,
        certificate_date=normalized.certificate_date,
        last_modified_date=normalized.last_modified_date,
        total_units=normalized.total_units,
        sold_units=normalized.sold_units,
        district=normalized.district,
        taluk=normalized.taluk,
        village=normalized.village,
        source_url=normalized.source_url,
    )


def _apply_normalized(project: Project, normalized: NormalizedProject) -> None:
    project.project_name = normalized.project_name
    project.promoter_name_raw = normalized.promoter_name
    project.project_type = normalized.project_type
    project.project_status = normalized.project_status
    project.project_start_date = normalized.project_start_date
    project.declared_completion_date = normalized.declared_completion_date
    project.certificate_number = normalized.certificate_number
    project.certificate_date = normalized.certificate_date
    project.last_modified_date = normalized.last_modified_date
    project.total_units = normalized.total_units
    project.sold_units = normalized.sold_units
    project.district = normalized.district
    project.taluk = normalized.taluk
    project.village = normalized.village
    if normalized.source_url is not None:
        project.source_url = normalized.source_url


def _count_severities(issues: list[QualityIssue]) -> tuple[int, int, int]:
    warnings = sum(1 for i in issues if i.severity == SEVERITY_WARNING)
    errors = sum(1 for i in issues if i.severity == SEVERITY_ERROR)
    infos = sum(1 for i in issues if i.severity == SEVERITY_INFO)
    return warnings, errors, infos


def run_ingestion(
    source: ReraSource,
    *,
    engine: Engine | None = None,
    dry_run: bool = False,
    limit: int | None = None,
    full_snapshot: bool = True,
    collector: Collector | None = None,
    prefetched: FetchResult | None = None,
) -> IngestionReport:
    """Execute one ingestion run.

    Idempotent: re-running against identical source data yields
    ``inserted=0``/``updated=0`` and ``unchanged=N`` with no new snapshots.
    """

    settings = get_settings()
    engine = engine or create_db_engine()
    factory = create_session_factory(engine)
    session: Session = factory()
    collector = collector or Collector()
    method = collection_method_for(source)
    parser_version = settings.parser_version

    report = IngestionReport(
        dry_run=dry_run,
        status=RUN_STATUS_RUNNING,
        source=source.name,
        collection_method=method,
        parser_version=parser_version,
    )

    run: IngestionRun | None = None
    try:
        if not dry_run:
            run = IngestionRun(
                started_at=utcnow(),
                source=source.name,
                collection_method=method,
                status=RUN_STATUS_RUNNING,
                parser_version=parser_version,
            )
            session.add(run)
            session.commit()
            report.run_id = run.id

        logger.info("ingestion started", extra={"source": source.name, "dry_run": dry_run})

        if prefetched is not None:
            raw_path = save_raw_artifact(
                prefetched.metadata,
                prefetched.raw_bytes,
                run_id=run.id if run else None,
                base_path=collector.raw_base_path,
            )
            collected = CollectedData(fetch=prefetched, raw_path=raw_path)
        else:
            collected = collector.collect(
                source, run_id=run.id if run else None, dry_run=dry_run
            )
        fetch = collected.fetch
        report.raw_path = collected.raw_path
        report.source_reference = fetch.metadata.source_reference
        report.records_found = len(fetch.records)
        logger.info("source fetched", extra={"records": report.records_found})

        parse_result = parse_records(fetch.records, list(fetch.columns))
        report.parse_errors = parse_result.errors
        report.unmapped_columns = parse_result.unmapped_columns
        report.missing_required_fields = parse_result.missing_required_fields
        report.column_warnings = parse_result.column_warnings
        for warning in parse_result.column_warnings:
            logger.warning("column_warning", extra={"detail": warning})
        for missing in parse_result.missing_required_fields:
            logger.warning("missing_required_column", extra={"field": missing})
        logger.info("records parsed", extra={"parsed": len(parse_result.records)})
    except Exception as exc:  # noqa: BLE001
        report.status = RUN_STATUS_FAILED
        report.error_summary = f"{type(exc).__name__}: {exc}"
        logger.error("ingestion failed during collection/parse", extra={"error": str(exc)})
        if run is not None:
            run.status = RUN_STATUS_FAILED
            run.completed_at = utcnow()
            run.errors_count = 1
            run.error_summary = report.error_summary
            session.commit()
        session.close()
        return report

    # --- normalise every parsed record ------------------------------------
    normalized_records: list[tuple[RawProjectRecord, NormalizedProject, list[QualityIssue]]] = []
    records_failed = len(parse_result.errors)
    all_issues: list[tuple[int | None, QualityIssue]] = [
        (None, QualityIssue("ERROR", "row_parse_error", err.message, None, None))
        for err in parse_result.errors
    ]

    for raw in parse_result.records:
        try:
            normalized, norm_issues = normalize_record(raw)
        except Exception as exc:  # noqa: BLE001
            records_failed += 1
            all_issues.append(
                (None, QualityIssue("ERROR", "normalization_failed", str(exc), None, None))
            )
            logger.warning(
                "normalization_failed",
                extra={"row": raw.source_row_number, "error": str(exc)},
            )
            continue
        issues = list(norm_issues)
        issues.extend(validate_record(normalized))
        normalized_records.append((raw, normalized, issues))

    # --- duplicates within the batch --------------------------------------
    duplicate_issues = detect_duplicate_registrations(
        [n.rera_registration_number for _, n, _ in normalized_records]
    )
    duplicate_numbers = {
        issue.raw_value for issue in duplicate_issues if issue.raw_value is not None
    }
    report.duplicates = len(duplicate_numbers)
    for issue in duplicate_issues:
        all_issues.append((None, issue))

    # --- persist each record ----------------------------------------------
    now = utcnow()
    seen_project_ids: set[int] = set()
    seen_reg_numbers: set[str] = set()
    processed = normalized_records[: limit if limit else len(normalized_records)]

    for raw, normalized, issues in processed:
        reg = normalized.rera_registration_number

        if not reg:
            records_failed += 1
            all_issues.extend((None, issue) for issue in issues if issue.severity == SEVERITY_ERROR)
            continue

        if reg in seen_reg_numbers and reg in duplicate_numbers:
            records_failed += 1
            all_issues.append(
                (
                    None,
                    QualityIssue(
                        "ERROR",
                        "duplicate_row_skipped",
                        f"Duplicate registration number '{reg}' skipped for this run.",
                        "rera_registration_number",
                        reg,
                    ),
                )
            )
            continue
        seen_reg_numbers.add(reg)

        project = session.execute(
            select(Project).where(Project.rera_registration_number == reg)
        ).scalar_one_or_none()

        if project is None:
            project = _project_from_normalized(normalized)
            project.first_seen_at = now
            project.last_seen_at = now
            project.last_checked_at = now
            session.add(project)
            session.flush()
            snapshot = build_snapshot(
                project.id,
                normalized,
                raw_record=raw.raw_row,
                collected_at=now,
            )
            session.add(snapshot)
            session.flush()
            report.records_inserted += 1
            report.new_projects += 1
        else:
            latest_snapshot = session.execute(
                select(ProjectSnapshot)
                .where(ProjectSnapshot.project_id == project.id)
                .order_by(ProjectSnapshot.id.desc())
                .limit(1)
            ).scalar_one_or_none()
            new_hash = compute_source_hash(normalized)
            project.last_checked_at = now
            project.not_seen_in_latest_run = False
            project.consecutive_misses = 0

            if latest_snapshot is not None and latest_snapshot.source_hash == new_hash:
                project.last_seen_at = now
                _apply_normalized(project, normalized)
                report.records_unchanged += 1
            else:
                changes = detect_changes(project_values(project), normalized_values(normalized))
                snapshot = build_snapshot(
                    project.id,
                    normalized,
                    raw_record=raw.raw_row,
                    collected_at=now,
                )
                session.add(snapshot)
                session.flush()
                for change in changes:
                    session.add(
                        ProjectChangeEvent(
                            project_id=project.id,
                            ingestion_run_id=run.id if run else None,
                            detected_at=now,
                            field_name=change.field_name,
                            old_value=change.old_value,
                            new_value=change.new_value,
                            source_last_modified_date=normalized.last_modified_date,
                            snapshot_id=snapshot.id,
                        )
                    )
                _apply_normalized(project, normalized)
                project.last_seen_at = now
                report.records_updated += 1
                report.changed_projects += 1
                report.changes.extend(changes)

        seen_project_ids.add(project.id)
        all_issues.extend((project.id, issue) for issue in issues)

    report.records_failed = records_failed

    # --- disappearance handling -------------------------------------------
    if full_snapshot and limit is None and not dry_run and seen_project_ids:
        for project in session.execute(select(Project)).scalars():
            if project.id in seen_project_ids:
                continue
            project.not_seen_in_latest_run = True
            project.consecutive_misses += 1
            project.last_checked_at = now

    # --- data quality persistence -----------------------------------------
    report.warnings, report.errors, report.infos = _count_severities(
        [issue for _, issue in all_issues]
    )
    if not dry_run:
        for project_id, issue in all_issues:
            session.add(
                DataQualityIssue(
                    ingestion_run_id=run.id if run else None,
                    project_id=project_id,
                    severity=issue.severity,
                    field_name=issue.field_name,
                    issue_type=issue.issue_type,
                    message=issue.message,
                    raw_value=issue.raw_value,
                )
            )

    report.issues = [issue for _, issue in all_issues]

    # --- baseline ----------------------------------------------------------
    if (
        not dry_run
        and report.records_inserted > 0
        and session.execute(select(func.count()).select_from(Baseline)).scalar_one() == 0
    ):
        session.add(
            Baseline(
                label="initial",
                baseline_at=now,
                source=source.name,
                record_count=report.records_inserted,
                parser_version=parser_version,
                source_checksum=fetch.metadata.checksum_sha256,
                ingestion_run_id=run.id if run else None,
            )
        )
        report.baseline_created = True

    # --- status ------------------------------------------------------------
    if report.errors > 0 or report.records_failed > 0:
        report.status = RUN_STATUS_PARTIAL
    else:
        report.status = RUN_STATUS_SUCCESS

    if dry_run:
        session.rollback()
        session.close()
        logger.info(
            "ingestion completed (dry run)",
            extra={
                "new": report.records_inserted,
                "changed": report.records_updated,
                "unchanged": report.records_unchanged,
            },
        )
        return report

    assert run is not None
    run.completed_at = utcnow()
    run.status = report.status
    run.records_found = report.records_found
    run.records_inserted = report.records_inserted
    run.records_updated = report.records_updated
    run.records_unchanged = report.records_unchanged
    run.records_failed = report.records_failed
    run.errors_count = report.errors
    run.source_reference = report.source_reference
    run.source_checksum = fetch.metadata.checksum_sha256
    run.error_summary = report.error_summary
    session.commit()
    session.close()
    logger.info(
        "ingestion completed",
        extra={
            "new": report.records_inserted,
            "changed": report.records_updated,
            "unchanged": report.records_unchanged,
            "status": report.status,
        },
    )
    return report


# --------------------------------------------------------------------------
# Reporting helpers (status / stats / export)
# --------------------------------------------------------------------------
def latest_source_checksum(engine: Engine | None = None) -> str | None:
    """Return the source checksum of the most recent ingestion run."""

    engine = engine or create_db_engine()
    factory = create_session_factory(engine)
    with factory() as session:
        return session.execute(
            select(IngestionRun.source_checksum).order_by(IngestionRun.id.desc()).limit(1)
        ).scalar_one_or_none()


def get_status(engine: Engine | None = None, limit: int = 10) -> dict[str, Any]:
    engine = engine or create_db_engine()
    factory = create_session_factory(engine)
    with factory() as session:
        runs = (
            session.execute(
                select(IngestionRun).order_by(IngestionRun.id.desc()).limit(limit)
            )
            .scalars()
            .all()
        )
        project_count = session.execute(select(func.count()).select_from(Project)).scalar_one()
        snapshot_count = session.execute(
            select(func.count()).select_from(ProjectSnapshot)
        ).scalar_one()
        change_count = session.execute(
            select(func.count()).select_from(ProjectChangeEvent)
        ).scalar_one()
        dq_count = session.execute(
            select(func.count()).select_from(DataQualityIssue)
        ).scalar_one()
        baseline = session.execute(
            select(Baseline).order_by(Baseline.id.asc()).limit(1)
        ).scalar_one_or_none()

        return {
            "projects": project_count,
            "snapshots": snapshot_count,
            "change_events": change_count,
            "data_quality_issues": dq_count,
            "baseline": (
                {
                    "baseline_at": baseline.baseline_at.isoformat(),
                    "record_count": baseline.record_count,
                    "parser_version": baseline.parser_version,
                    "source_checksum": baseline.source_checksum,
                }
                if baseline
                else None
            ),
            "runs": [
                {
                    "id": r.id,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                    "status": r.status,
                    "records_found": r.records_found,
                    "inserted": r.records_inserted,
                    "updated": r.records_updated,
                    "unchanged": r.records_unchanged,
                    "failed": r.records_failed,
                }
                for r in runs
            ],
        }


def get_stats(engine: Engine | None = None) -> dict[str, Any]:
    engine = engine or create_db_engine()
    factory = create_session_factory(engine)
    with factory() as session:
        by_district = dict(
            session.execute(
                select(Project.district, func.count()).group_by(Project.district)
            ).all()
        )
        by_status = dict(
            session.execute(
                select(Project.project_status, func.count()).group_by(Project.project_status)
            ).all()
        )
        by_type = dict(
            session.execute(
                select(Project.project_type, func.count()).group_by(Project.project_type)
            ).all()
        )
        not_seen = session.execute(
            select(func.count())
            .select_from(Project)
            .where(Project.not_seen_in_latest_run.is_(True))
        ).scalar_one()
        return {
            "total_projects": session.execute(select(func.count()).select_from(Project)).scalar_one(),
            "not_seen_in_latest_run": not_seen,
            "by_district": by_district,
            "by_status": by_status,
            "by_type": by_type,
        }


def export_projects(
    destination: str | Path,
    *,
    engine: Engine | None = None,
    fmt: str | None = None,
) -> Path:
    """Export the current projects table to CSV or XLSX."""

    import pandas as pd

    engine = engine or create_db_engine()
    destination = Path(destination)
    fmt = (fmt or destination.suffix.lstrip(".") or "csv").lower()

    factory = create_session_factory(engine)
    with factory() as session:
        rows = session.execute(select(Project).order_by(Project.id)).scalars().all()
        records = [
            {
                "rera_registration_number": p.rera_registration_number,
                "project_name": p.project_name,
                "promoter_name_raw": p.promoter_name_raw,
                "project_type": p.project_type,
                "project_status": p.project_status,
                "project_start_date": p.project_start_date,
                "declared_completion_date": p.declared_completion_date,
                "certificate_number": p.certificate_number,
                "certificate_date": p.certificate_date,
                "last_modified_date": p.last_modified_date,
                "total_units": p.total_units,
                "sold_units": p.sold_units,
                "district": p.district,
                "taluk": p.taluk,
                "village": p.village,
                "source_url": p.source_url,
                "first_seen_at": p.first_seen_at,
                "last_seen_at": p.last_seen_at,
                "last_checked_at": p.last_checked_at,
                "not_seen_in_latest_run": p.not_seen_in_latest_run,
            }
            for p in rows
        ]
    frame = pd.DataFrame(records)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if fmt in {"xlsx", "xls"}:
        frame.to_excel(destination, index=False)
    else:
        frame.to_csv(destination, index=False)
    return destination
