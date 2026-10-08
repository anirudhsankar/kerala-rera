"""Database / service integration tests: persistence, idempotency, history."""

from __future__ import annotations

import hashlib
from pathlib import Path

from sqlalchemy import func, select

from rera.database.models import (
    Baseline,
    DataQualityIssue,
    IngestionRun,
    Project,
    ProjectChangeEvent,
    ProjectSnapshot,
)
from rera.database.session import create_db_engine, init_db
from rera.ingestion.collector import Collector
from rera.services.ingestion_service import latest_source_checksum, run_ingestion
from rera.sources.krera import KReraExportFileSource


def _run(engine, path: Path, tmp_path: Path, **kwargs):
    collector = Collector(raw_base_path=tmp_path)
    return run_ingestion(
        KReraExportFileSource(path), engine=engine, collector=collector, **kwargs
    )


def _count(engine, model) -> int:
    with engine.connect() as conn:
        return conn.execute(select(func.count()).select_from(model)).scalar_one()


def test_initial_ingest_creates_projects_snapshots_and_baseline(engine, sample_path, tmp_path):
    report = _run(engine, sample_path, tmp_path)

    assert report.records_inserted == 10
    assert report.records_failed == 0
    assert report.status == "SUCCESS"
    assert report.baseline_created is True
    assert _count(engine, Project) == 10
    assert _count(engine, ProjectSnapshot) == 10
    assert _count(engine, Baseline) == 1
    assert _count(engine, IngestionRun) == 1


def test_second_identical_run_is_idempotent(engine, sample_path, tmp_path):
    first = _run(engine, sample_path, tmp_path)
    second = _run(engine, sample_path, tmp_path)

    assert first.records_inserted == 10
    assert second.records_inserted == 0
    assert second.records_updated == 0
    assert second.records_unchanged == 10
    assert _count(engine, Project) == 10
    # No unnecessary snapshot duplication.
    assert _count(engine, ProjectSnapshot) == 10
    assert _count(engine, ProjectChangeEvent) == 0


def test_modified_source_creates_snapshot_and_change_events(
    engine, sample_path, sample_modified_path, tmp_path
):
    _run(engine, sample_path, tmp_path)
    report = _run(engine, sample_modified_path, tmp_path)

    assert report.records_updated == 1
    assert report.records_unchanged == 9
    field_names = {c.field_name for c in report.changes}
    assert "declared_completion_date" in field_names
    assert "sold_units" in field_names

    with engine.connect() as conn:
        project_id = conn.execute(
            select(Project.id).where(
                Project.rera_registration_number == "K-RERA/PRJ/ERK/001/2022"
            )
        ).scalar_one()
        snapshots = conn.execute(
            select(ProjectSnapshot.source_hash, ProjectSnapshot.declared_completion_date)
            .where(ProjectSnapshot.project_id == project_id)
            .order_by(ProjectSnapshot.id)
        ).all()
        # Previous snapshot preserved, new snapshot appended (append-only).
        assert len(snapshots) == 2
        assert str(snapshots[0].declared_completion_date) == "2027-12-31"
        assert str(snapshots[1].declared_completion_date) == "2028-12-31"
        assert snapshots[0].source_hash != snapshots[1].source_hash

    # Change events persisted for the modified project.
    assert _count(engine, ProjectChangeEvent) >= 2


def test_duplicate_registration_numbers_are_flagged_not_double_inserted(
    engine, sample_duplicate_path, tmp_path
):
    report = _run(engine, sample_duplicate_path, tmp_path)

    assert report.duplicates == 1
    assert report.records_failed == 1
    assert report.status == "PARTIAL"
    # Only one of the two duplicate rows is stored.
    assert _count(engine, Project) == 1


def test_disappeared_projects_are_flagged_not_deleted(engine, sample_path, tmp_path):
    _run(engine, sample_path, tmp_path)

    subset = tmp_path / "subset.csv"
    header = (
        "RERA Registration Number,Project Name,Promoter Name,Project Type,Project Status,"
        "Project Start Date,Declared Completion Date,Total Units,Sold Units,District\n"
    )
    row = "K-RERA/PRJ/ERK/001/2022,Green Meadows,ABC Builders,Residential,Registered,01/02/2022,31/12/2027,120,45,Ernakulam\n"
    subset.write_text(header + row, encoding="utf-8")

    _run(engine, subset, tmp_path, full_snapshot=True)

    assert _count(engine, Project) == 10  # nothing deleted
    with engine.connect() as conn:
        not_seen = conn.execute(
            select(func.count()).select_from(Project).where(Project.not_seen_in_latest_run.is_(True))
        ).scalar_one()
    assert not_seen == 9


def test_dry_run_does_not_modify_database(engine, sample_path, tmp_path):
    report = _run(engine, sample_path, tmp_path, dry_run=True)

    assert report.records_inserted == 10
    assert report.dry_run is True
    assert _count(engine, Project) == 0
    assert _count(engine, ProjectSnapshot) == 0
    assert _count(engine, IngestionRun) == 0


def test_questionable_record_is_stored_with_quality_issue(engine, tmp_path):
    csv_path = tmp_path / "odd.csv"
    csv_path.write_text(
        "RERA Registration Number,Project Name,Declared Completion Date,Total Units,Sold Units,District\n"
        "K-RERA/PRJ/XXX/001/2022,,not-a-date,1000,1200,Atlantis\n",
        encoding="utf-8",
    )
    report = _run(engine, csv_path, tmp_path)

    # Record is stored, not discarded.
    assert report.records_inserted == 1
    assert _count(engine, Project) == 1
    # Quality issues recorded.
    assert report.warnings >= 2  # missing name, sold>total, unknown district, invalid date
    assert _count(engine, DataQualityIssue) >= 2

    with engine.connect() as conn:
        project = conn.execute(select(Project)).one()
        assert project.district == "Atlantis"
        assert project.total_units == 1000


def test_latest_checksum_and_prefetched_path(engine, sample_path, tmp_path):
    first = _run(engine, sample_path, tmp_path)
    assert first.records_inserted == 10
    expected = hashlib.sha256(sample_path.read_bytes()).hexdigest()
    assert latest_source_checksum(engine) == expected

    # The `prefetched` path used by `rera update` ingests a pre-fetched source.
    engine2 = create_db_engine(f"sqlite:///{(tmp_path / 'prefetch.db').as_posix()}")
    init_db(engine2)
    source = KReraExportFileSource(sample_path)
    fetched = source.fetch_export()
    report = run_ingestion(
        source,
        engine=engine2,
        collector=Collector(raw_base_path=tmp_path),
        prefetched=fetched,
    )
    assert report.records_inserted == 10
    assert latest_source_checksum(engine2) == fetched.metadata.checksum_sha256
