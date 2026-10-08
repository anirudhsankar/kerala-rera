"""Command-line interface for the K-RERA ingestion pipeline.

Examples::

    python -m rera.cli.main inspect-source
    python -m rera.cli.main init-db
    python -m rera.cli.main ingest --source-file data/sample/projects_sample.csv
    python -m rera.cli.main ingest --dry-run
    python -m rera.cli.main validate
    python -m rera.cli.main detect-changes
    python -m rera.cli.main status
    python -m rera.cli.main stats
    python -m rera.cli.main export --output data/processed/projects.csv
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import select

from rera.analytics.promoters import build_promoters
from rera.config import get_settings
from rera.constants import RUN_STATUS_FAILED
from rera.database.models import ProjectChangeEvent
from rera.database.session import create_db_engine, create_session_factory, init_db
from rera.logging_config import get_logger, setup_logging
from rera.services.ingestion_service import (
    IngestionReport,
    export_projects,
    get_stats,
    get_status,
    latest_source_checksum,
    run_ingestion,
)
from rera.services.inspection import inspect_source_file
from rera.sources.base import ReraSource
from rera.sources.krera import (
    KReraDownloadSource,
    KReraExportFileSource,
    inspect_krera_live,
)

logger = get_logger("rera.cli")

_EXPORT_SUFFIXES = (".csv", ".xlsx", ".xlsm", ".xls")


def _latest_manual_file(settings) -> Path | None:
    directory = Path(settings.manual_import_path)
    if not directory.exists():
        return None
    candidates = [
        p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in _EXPORT_SUFFIXES
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _resolve_source_file(args: argparse.Namespace, settings) -> Path | None:
    if args.source_file:
        return Path(args.source_file)
    if getattr(args, "sample", False):
        return Path(settings.sample_data_path) / "projects_sample.csv"
    return _latest_manual_file(settings)


def _build_engine(args: argparse.Namespace):
    return create_db_engine(getattr(args, "database_url", None))


def _print_report(report: IngestionReport) -> None:
    for line in report.summary_lines():
        print(line)
    if report.changes:
        print("  Detected changes:")
        for change in report.changes:
            print(
                f"    - {change.field_name}: {change.old_value!r} -> {change.new_value!r}"
            )
    if report.parse_errors:
        print(f"  Parse errors: {len(report.parse_errors)}")
        for err in report.parse_errors[:5]:
            print(f"    - row {err.row_number}: {err.message}")


def cmd_inspect_source(args: argparse.Namespace) -> int:
    result = inspect_krera_live(args.url)
    print("K-RERA SOURCE INSPECTION")
    for key, value in result.items():
        print(f"  {key}: {value}")
    if result.get("anti_bot_challenge"):
        print(
            "  conclusion: live automated collection intentionally not performed "
            "(anti-bot bypass out of scope). Use the official export file workflow."
        )
    return 0


def cmd_init_db(args: argparse.Namespace) -> int:
    engine = _build_engine(args)
    init_db(engine)
    print(f"Database schema ensured at {engine.url}")
    return 0


def cmd_inspect_file(args: argparse.Namespace) -> int:
    result = inspect_source_file(
        args.source_file,
        sheet_name=args.sheet,
        header_row=args.header_row,
        preview=args.preview,
    )
    print("K-RERA FILE INSPECTION (read-only)")
    print(f"  File:        {result['file']}")
    print(f"  Sheets:      {result['sheets']}")
    print(f"  Header row:  {result['header_row']} (score {result['header_score']})")
    print(f"  Records:     {result['record_count']}")
    print("  Column mapping:")
    for column in result["columns"]:
        fields = result["mapped_columns"].get(column)
        target = ", ".join(fields) if fields else "-- UNMAPPED --"
        print(f"    {column!r:<34} -> {target}")
    if result["unmapped_columns"]:
        print(f"  Unmapped:    {result['unmapped_columns']}")
    if result["missing_required_fields"]:
        print(f"  MISSING REQUIRED: {result['missing_required_fields']}")
    for warning in result["column_warnings"]:
        print(f"  WARNING: {warning}")
    if result["parse_errors"]:
        print(f"  Parse errors: {len(result['parse_errors'])}")
        for error in result["parse_errors"][:5]:
            print(f"    - row {error['row']}: {error['message']}")
    print("  Normalised preview:")
    for row in result["preview"]:
        print(
            f"    [{row['rera_registration_number']}] {row['project_name']!r} "
            f"type={row['project_type']!r} status={row['project_status']!r} "
            f"completion={row['declared_completion_date']} "
            f"units={row['total_units']}/{row['sold_units']} "
            f"district={row['district']!r} issues={row['issues']}"
        )
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    settings = get_settings()
    source_file = _resolve_source_file(args, settings)
    if source_file is None:
        print(
            "No source file found. Place an official K-RERA export in "
            f"'{settings.manual_import_path}' or pass --source-file / --sample.",
            file=sys.stderr,
        )
        return 2
    source = KReraExportFileSource(source_file, source_url=settings.rera_base_url)
    engine = _build_engine(args)
    init_db(engine)
    report = run_ingestion(
        source,
        engine=engine,
        dry_run=args.dry_run,
        limit=args.limit,
        full_snapshot=not args.no_full_snapshot,
    )
    _print_report(report)
    if report.status == RUN_STATUS_FAILED:
        return 2
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    settings = get_settings()
    source_file = _resolve_source_file(args, settings)
    if source_file is None:
        print("No source file found for validation.", file=sys.stderr)
        return 2
    source = KReraExportFileSource(source_file)
    engine = _build_engine(args)
    init_db(engine)
    report = run_ingestion(source, engine=engine, dry_run=True)
    print("K-RERA VALIDATION")
    print(f"  Records found: {report.records_found}")
    print(f"  Validated:     {len(report.issues)} findings")
    print(f"  Warnings:      {report.warnings}")
    print(f"  Errors:        {report.errors}")
    print(f"  Infos:         {report.infos}")
    if report.unmapped_columns:
        print(f"  Unmapped:      {report.unmapped_columns}")
    if report.missing_required_fields:
        print(f"  MISSING REQUIRED: {report.missing_required_fields}")
    if args.verbose:
        for issue in report.issues:
            print(f"  [{issue.severity}] {issue.field_name}: {issue.message}")
    return 1 if report.errors else 0


def cmd_detect_changes(args: argparse.Namespace) -> int:
    settings = get_settings()
    source_file = _resolve_source_file(args, settings)
    if source_file is None:
        engine = _build_engine(args)
        init_db(engine)
        factory = create_session_factory(engine)
        with factory() as session:
            events = (
                session.execute(
                    select(ProjectChangeEvent)
                    .order_by(ProjectChangeEvent.detected_at.desc())
                    .limit(args.limit or 50)
                )
                .scalars()
                .all()
            )
        print(f"Stored change events: {len(events)}")
        for event in events:
            print(
                f"  project_id={event.project_id} {event.field_name}: "
                f"{event.old_value!r} -> {event.new_value!r}"
            )
        return 0

    source = KReraExportFileSource(source_file)
    engine = _build_engine(args)
    init_db(engine)
    report = run_ingestion(source, engine=engine, dry_run=True, limit=args.limit)
    print("K-RERA CHANGE DETECTION (dry run)")
    print(f"  New:       {report.records_inserted}")
    print(f"  Changed:   {report.records_updated}")
    print(f"  Unchanged: {report.records_unchanged}")
    for change in report.changes:
        print(f"  - {change.field_name}: {change.old_value!r} -> {change.new_value!r}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    engine = _build_engine(args)
    init_db(engine)
    status = get_status(engine, limit=args.limit)
    print("K-RERA STATUS")
    print(f"  Projects:            {status['projects']}")
    print(f"  Snapshots:           {status['snapshots']}")
    print(f"  Change events:       {status['change_events']}")
    print(f"  Data quality issues: {status['data_quality_issues']}")
    if status["baseline"]:
        print(f"  Baseline:            {status['baseline']}")
    print("  Recent runs:")
    for run in status["runs"]:
        print(
            f"    #{run['id']} {run['status']} found={run['records_found']} "
            f"new={run['inserted']} changed={run['updated']} "
            f"unchanged={run['unchanged']} failed={run['failed']}"
        )
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    engine = _build_engine(args)
    init_db(engine)
    stats = get_stats(engine)
    print("K-RERA STATISTICS")
    print(f"  Total projects:        {stats['total_projects']}")
    print(f"  Not seen in last run:  {stats['not_seen_in_latest_run']}")
    for label, key in (("By district", "by_district"), ("By status", "by_status"), ("By type", "by_type")):
        print(f"  {label}:")
        for name, count in sorted(stats[key].items(), key=lambda kv: (-kv[1], str(kv[0]))):
            print(f"    {name}: {count}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    engine = _build_engine(args)
    init_db(engine)
    path = export_projects(args.output, engine=engine, fmt=args.format)
    print(f"Exported projects to {path}")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    """Run the read-only analytics API (requires the [api] extra)."""

    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        print(
            'The API server requires optional dependencies. Install with: '
            'pip install -e ".[api]"',
            file=sys.stderr,
        )
        raise SystemExit(2) from exc

    if getattr(args, "database_url", None):
        os.environ["DATABASE_URL"] = args.database_url
    print(f"Serving read-only API on http://{args.host}:{args.port} (docs at /docs)")
    uvicorn.run(
        "rera.api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    settings = get_settings()
    engine = _build_engine(args)
    init_db(engine)

    source: ReraSource
    if settings.rera_export_url:
        print(f"Downloading export from {settings.rera_export_url}")
        source = KReraDownloadSource(settings.rera_export_url)
    else:
        source_file = _latest_manual_file(settings)
        if source_file is None:
            print(
                "No RERA_EXPORT_URL configured and no export in "
                f"'{settings.manual_import_path}'. Nothing to update.",
                file=sys.stderr,
            )
            return 2
        source = KReraExportFileSource(source_file)

    try:
        prefetched = source.fetch_export()
    except Exception as exc:  # noqa: BLE001
        print(f"Update failed while fetching source: {exc}", file=sys.stderr)
        return 2

    checksum = prefetched.metadata.checksum_sha256
    if checksum and checksum == latest_source_checksum(engine):
        print("No new data: source checksum matches the last run; skipping.")
        print(f"  Records in source: {len(prefetched.records)}")
        return 0

    report = run_ingestion(source, engine=engine, prefetched=prefetched)
    _print_report(report)
    if report.status == RUN_STATUS_FAILED:
        return 2

    factory = create_session_factory(engine)
    with factory() as session:
        result = build_promoters(session)
    print("PROMOTER CANONICALISATION")
    for line in result.summary_lines()[1:]:
        print(line)
    return 0


def cmd_promoters_build(args: argparse.Namespace) -> int:
    engine = _build_engine(args)
    init_db(engine)
    factory = create_session_factory(engine)
    with factory() as session:
        result = build_promoters(session, dry_run=args.dry_run)
    for line in result.summary_lines():
        print(line)
    if args.dry_run:
        print("  Database changes:  NOT COMMITTED (dry run)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rera",
        description="Kerala RERA Intelligence - Phase 1 ingestion pipeline",
    )
    parser.add_argument("--database-url", default=None, help="Override DATABASE_URL")
    sub = parser.add_subparsers(dest="command", required=True)

    p_inspect = sub.add_parser("inspect-source", help="Politely probe the live K-RERA site")
    p_inspect.add_argument("--url", default=None)
    p_inspect.set_defaults(func=cmd_inspect_source)

    p_init = sub.add_parser("init-db", help="Create database schema (dev convenience)")
    p_init.set_defaults(func=cmd_init_db)

    p_peek = sub.add_parser(
        "inspect-file", help="Read-only inspection of an export file (no DB writes)"
    )
    p_peek.add_argument("--source-file", required=True)
    p_peek.add_argument("--sheet", default=None)
    p_peek.add_argument("--header-row", type=int, default=None)
    p_peek.add_argument("--preview", type=int, default=8)
    p_peek.set_defaults(func=cmd_inspect_file)

    p_ingest = sub.add_parser("ingest", help="Run an ingestion")
    p_ingest.add_argument("--source-file", default=None)
    p_ingest.add_argument("--sample", action="store_true", help="Use bundled sample fixture")
    p_ingest.add_argument("--dry-run", action="store_true")
    p_ingest.add_argument("--limit", type=int, default=None)
    p_ingest.add_argument("--no-full-snapshot", action="store_true")
    p_ingest.set_defaults(func=cmd_ingest)

    p_validate = sub.add_parser("validate", help="Validate a source file (no DB changes)")
    p_validate.add_argument("--source-file", default=None)
    p_validate.add_argument("--sample", action="store_true")
    p_validate.add_argument("--verbose", action="store_true")
    p_validate.set_defaults(func=cmd_validate)

    p_changes = sub.add_parser("detect-changes", help="Detect changes (dry run or stored)")
    p_changes.add_argument("--source-file", default=None)
    p_changes.add_argument("--sample", action="store_true")
    p_changes.add_argument("--limit", type=int, default=None)
    p_changes.set_defaults(func=cmd_detect_changes)

    p_status = sub.add_parser("status", help="Show ingestion run status")
    p_status.add_argument("--limit", type=int, default=10)
    p_status.set_defaults(func=cmd_status)

    p_stats = sub.add_parser("stats", help="Show aggregate statistics")
    p_stats.set_defaults(func=cmd_stats)

    p_export = sub.add_parser("export", help="Export projects table")
    p_export.add_argument("--output", default="data/processed/projects.csv")
    p_export.add_argument("--format", default=None)
    p_export.set_defaults(func=cmd_export)

    p_prom = sub.add_parser("promoters", help="Promoter (builder) identity operations")
    prom_sub = p_prom.add_subparsers(dest="promoters_command", required=True)
    p_prom_build = prom_sub.add_parser(
        "build", help="Normalise promoter names and link projects"
    )
    p_prom_build.add_argument("--dry-run", action="store_true")
    p_prom_build.set_defaults(func=cmd_promoters_build)

    p_serve = sub.add_parser("serve", help="Run the read-only analytics API")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.add_argument("--reload", action="store_true")
    p_serve.set_defaults(func=cmd_serve)

    p_update = sub.add_parser(
        "update", help="Download (if configured) + ingest + rebuild promoters"
    )
    p_update.set_defaults(func=cmd_update)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = get_settings()
    setup_logging(settings.log_level)
    if getattr(args, "database_url", None):
        settings.database_url = args.database_url
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
