"""SQLAlchemy 2.x ORM models for the K-RERA Intelligence database.

Design notes
------------
* ``projects`` holds the latest known *normalised* state of each project.
* ``project_snapshots`` is an immutable, append-only record of the source state
  observed during each collection. Historical snapshots are never modified.
* ``project_change_events`` records field-level differences between snapshots.
* ``ingestion_runs`` tracks every collection attempt and its outcome.
* ``data_quality_issues`` stores validation findings without discarding rows.
* ``promoters`` stores canonical promoter identities; projects keep the raw
  promoter name in ``promoter_name_raw``. Automatic merging is never assumed.
* ``baselines`` records the initial full-load checkpoint.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    """Return the current UTC time (timezone-aware)."""

    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Promoter(Base):
    __tablename__ = "promoters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(512), nullable=False)
    normalized_key: Mapped[str] = mapped_column(
        String(512), nullable=False, unique=True, index=True
    )
    match_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    projects: Mapped[list[Project]] = relationship(back_populates="promoter")


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("rera_registration_number", name="uq_projects_rera_registration_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rera_registration_number: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    project_name: Mapped[str | None] = mapped_column(Text)
    promoter_name_raw: Mapped[str | None] = mapped_column(Text)
    promoter_id: Mapped[int | None] = mapped_column(
        ForeignKey("promoters.id"), nullable=True
    )

    project_type: Mapped[str | None] = mapped_column(String(128))
    project_status: Mapped[str | None] = mapped_column(String(128))
    project_start_date: Mapped[date | None] = mapped_column(Date)
    declared_completion_date: Mapped[date | None] = mapped_column(Date)
    certificate_number: Mapped[str | None] = mapped_column(String(255))
    certificate_date: Mapped[date | None] = mapped_column(Date)
    last_modified_date: Mapped[date | None] = mapped_column(Date)

    total_units: Mapped[int | None] = mapped_column(Integer)
    sold_units: Mapped[int | None] = mapped_column(Integer)

    district: Mapped[str | None] = mapped_column(String(128))
    taluk: Mapped[str | None] = mapped_column(String(128))
    village: Mapped[str | None] = mapped_column(String(255))

    source_url: Mapped[str | None] = mapped_column(Text)

    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    not_seen_in_latest_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consecutive_misses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    promoter: Mapped[Promoter | None] = relationship(back_populates="projects")
    snapshots: Mapped[list[ProjectSnapshot]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    change_events: Mapped[list[ProjectChangeEvent]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProjectSnapshot(Base):
    """Immutable record of the source state observed during a collection."""

    __tablename__ = "project_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )

    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    rera_registration_number: Mapped[str | None] = mapped_column(String(255))
    project_name: Mapped[str | None] = mapped_column(Text)
    promoter_name_raw: Mapped[str | None] = mapped_column(Text)
    project_type: Mapped[str | None] = mapped_column(String(128))
    project_status: Mapped[str | None] = mapped_column(String(128))
    project_start_date: Mapped[date | None] = mapped_column(Date)
    declared_completion_date: Mapped[date | None] = mapped_column(Date)
    certificate_number: Mapped[str | None] = mapped_column(String(255))
    certificate_date: Mapped[date | None] = mapped_column(Date)
    last_modified_date: Mapped[date | None] = mapped_column(Date)
    total_units: Mapped[int | None] = mapped_column(Integer)
    sold_units: Mapped[int | None] = mapped_column(Integer)
    district: Mapped[str | None] = mapped_column(String(128))
    taluk: Mapped[str | None] = mapped_column(String(128))
    village: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(Text)

    source_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    raw_record: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped[Project] = relationship(back_populates="snapshots")
    change_events: Mapped[list[ProjectChangeEvent]] = relationship(
        back_populates="snapshot"
    )


class ProjectChangeEvent(Base):
    __tablename__ = "project_change_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )
    ingestion_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("ingestion_runs.id"), nullable=True
    )

    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    source_last_modified_date: Mapped[date | None] = mapped_column(Date)
    snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("project_snapshots.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped[Project] = relationship(back_populates="change_events")
    snapshot: Mapped[ProjectSnapshot | None] = relationship(
        back_populates="change_events"
    )


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    source: Mapped[str | None] = mapped_column(String(255))
    collection_method: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="RUNNING")
    parser_version: Mapped[str | None] = mapped_column(String(32))

    records_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_unchanged: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    errors_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_reference: Mapped[str | None] = mapped_column(Text)
    error_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DataQualityIssue(Base):
    __tablename__ = "data_quality_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ingestion_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("ingestion_runs.id"), nullable=True, index=True
    )
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True, index=True
    )

    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="WARNING")
    field_name: Mapped[str | None] = mapped_column(String(128))
    issue_type: Mapped[str | None] = mapped_column(String(128))
    message: Mapped[str | None] = mapped_column(Text)
    raw_value: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Baseline(Base):
    """Checkpoint for the first full ingestion (baseline snapshot)."""

    __tablename__ = "baselines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str | None] = mapped_column(String(128))
    baseline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    source: Mapped[str | None] = mapped_column(String(255))
    record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parser_version: Mapped[str | None] = mapped_column(String(32))
    source_checksum: Mapped[str | None] = mapped_column(String(128))
    ingestion_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("ingestion_runs.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
