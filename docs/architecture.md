# Architecture

Phase 1 is a single Python application backed by PostgreSQL (SQLite is
supported for development/tests). No frontend, no public API, no orchestration
framework — deliberately simple, transparent, testable and maintainable.

## Pipeline

```mermaid
flowchart LR
    A["Official K-RERA export<br/>(CSV/XLSX, human-downloaded)"] --> B[Source adapter<br/>KReraExportFileSource]
    B --> C[Raw preservation<br/>data/raw/YYYY/MM/DD/run_id]
    B --> D[Parser<br/>header mapping]
    D --> E[Normaliser<br/>dates, numbers, vocab]
    E --> F[Validator<br/>data quality rules]
    F --> G[Ingestion service]
    G --> H[(PostgreSQL)]
    H --> I[projects<br/>latest state]
    H --> J[project_snapshots<br/>immutable history]
    H --> K[project_change_events]
    H --> L[data_quality_issues]
    H --> M[ingestion_runs]
    H --> N[baselines]
```

## Component responsibilities

| Module | Responsibility |
|--------|----------------|
| `rera.config` | Environment-driven settings (no hard-coded values) |
| `rera.logging_config` | Structured `key=value` logging |
| `rera.database.models` | SQLAlchemy 2.x ORM models |
| `rera.database.session` | Engine / session / `init_db` |
| `rera.sources.base` | `ReraSource` interface + provenance dataclasses |
| `rera.sources.krera` | Official-file adapter + polite HTTP inspect probe |
| `rera.ingestion.collector` | Fetch + raw artefact preservation |
| `rera.ingestion.parser` | Raw rows → `RawProjectRecord` (header mapping) |
| `rera.ingestion.normalizer` | Raw → `NormalizedProject` (raw retained) |
| `rera.ingestion.validator` | Non-fatal data quality findings |
| `rera.ingestion.snapshot` | Build immutable snapshots + source hash |
| `rera.ingestion.change_detector` | Field-level change events |
| `rera.services.ingestion_service` | Orchestration, idempotency, reporting |
| `rera.cli.main` | Command-line interface |

## Data model (ER)

```mermaid
erDiagram
    PROMOTERS ||--o{ PROJECTS : "canonically identified by (optional)"
    PROJECTS ||--o{ PROJECT_SNAPSHOTS : "has history"
    PROJECTS ||--o{ PROJECT_CHANGE_EVENTS : "has changes"
    PROJECT_SNAPSHOTS ||--o{ PROJECT_CHANGE_EVENTS : "recorded in"
    INGESTION_RUNS ||--o{ PROJECT_CHANGE_EVENTS : "detected by"
    INGESTION_RUNS ||--o{ DATA_QUALITY_ISSUES : "produced"
    PROJECTS ||--o{ DATA_QUALITY_ISSUES : "concerns"
    INGESTION_RUNS ||--o| BASELINES : "baseline run"

    PROJECTS {
        int id PK
        string rera_registration_number UK
        text project_name
        text promoter_name_raw
        int promoter_id FK
        date declared_completion_date
        int total_units
        int sold_units
        bool not_seen_in_latest_run
        int consecutive_misses
    }
    PROJECT_SNAPSHOTS {
        int id PK
        int project_id FK
        date snapshot_date
        string source_hash
        json raw_record
    }
    PROJECT_CHANGE_EVENTS {
        int id PK
        int project_id FK
        string field_name
        text old_value
        text new_value
        int snapshot_id FK
    }
    INGESTION_RUNS {
        int id PK
        string status
        int records_inserted
        int records_updated
        int records_unchanged
        int records_failed
    }
    DATA_QUALITY_ISSUES {
        int id PK
        string severity
        string issue_type
        text message
    }
    BASELINES {
        int id PK
        datetime baseline_at
        int record_count
        string source_checksum
    }
    PROMOTERS {
        int id PK
        string canonical_name UK
        bool needs_review
    }
```

## Key design decisions

1. **Separation of layers.** Source / parse / normalise / validate / persist are
   independent and unit-tested. The K-RERA site can change without touching the
   database layer.
2. **Raw before normalised.** Raw artefact preserved on disk and the full
   original row stored in `project_snapshots.raw_record`.
3. **Immutable history.** `project_snapshots` is append-only; previous snapshots
   are never modified.
4. **Hash-based change detection.** A deterministic SHA-256 of canonical source
   fields avoids unnecessary snapshots.
5. **Non-fatal validation.** Questionable records are stored *and* flagged;
   nothing is silently discarded.
6. **Fail safely.** If fetch/parse fails, the run is marked `FAILED` and no
   corrupted data is inserted.
7. **Promoter identity is reviewable.** No automatic merging on name similarity.
8. **Provider-agnostic storage.** Generic SQLAlchemy types -> PostgreSQL in
   production, SQLite for tests.

## Future compatibility

The schema already supports later phases without redesign: district analytics
(`district`), promoter analytics (`promoters`), project history
(`project_snapshots`), change timelines (`project_change_events`), regulatory
orders/complaints/quarterly progress/document metadata (new tables referencing
`projects`), alerts (queryable `not_seen_in_latest_run` / change events) and a
public API (read from existing tables).
