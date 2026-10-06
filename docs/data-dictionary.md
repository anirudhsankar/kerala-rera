# Data Dictionary

Terminology:

* **Source** — a value exactly as read from the official K-RERA export.
* **Normalised** — the canonical value stored in typed columns.
* **Raw** — original string values are always preserved (`raw_record`,
  `promoter_name_raw`, or the raw artefact on disk).

> Source field names below are **confirmed** from the official export
> (`project1.xlsx`, 2026-10-06). Matching is tolerant via the alias table in
> `src/rera/ingestion/parser.py`; the registration number is carried in the
> column labelled `Certificate No`.

---

## Table: `projects` (latest known state)

| Field | Type | Source field | Description | Nullable | Transformation | Validation | Example |
|-------|------|--------------|-------------|----------|----------------|------------|---------|
| `id` | INTEGER PK | — | Surrogate key | No | auto | — | `1` |
| `rera_registration_number` | VARCHAR(255) UNIQUE | Certificate No | Primary business identity (`K-RERA/PRJ/...`) | No | trim / whitespace collapse | non-empty (ERROR); duplicates flagged | `K-RERA/PRJ/005/2020` |
| `project_name` | TEXT | Project | Registered project name | Yes | trim / whitespace collapse | non-empty (WARNING) | `THE GARDENIA BY FAVOURITE HOMES` |
| `promoter_name_raw` | TEXT | Promoter Name | Raw promoter name as sourced | Yes | trim only | — | `FAVOURITE CONSTRUCTIONS PRIVATE LIMITED` |
| `promoter_id` | INTEGER FK | — | Link to canonical promoter, if reliably matched | Yes | — | never auto-merged on similarity alone | `NULL` |
| `project_type` | VARCHAR(128) | Project Type | Type of project | Yes | alias map, else **preserve source** | unknown type flagged (INFO) | `Residential (Apartment)` |
| `project_status` | VARCHAR(128) | Status | Source status | Yes | alias map, else **preserve source** | unknown status flagged (INFO) | `Inprogress` |
| `project_start_date` | DATE | Project Start Date | Reported start date | Yes | multi-format date parse | invalid date flagged (WARNING) | `2019-12-01` |
| `declared_completion_date` | DATE | Date of Completion | Completion date reported by source | Yes | multi-format date parse | invalid (WARNING); before start (WARNING); passed = INFO | `2023-05-29` |
| `certificate_number` | VARCHAR(255) | Certificate No | Same value as the identity | Yes | trim | — | `K-RERA/PRJ/005/2020` |
| `certificate_date` | DATE | Certificate Date | Certificate / registration date | Yes | multi-format date parse | invalid date flagged (WARNING) | `2021-03-30` |
| `last_modified_date` | DATE | not in export | Source's own last-modified date | Yes | multi-format date parse | not present in this export | `NULL` |
| `total_units` | INTEGER | Total | Reported total units | Yes | integer parse (`1,000`, `100.0`) | negative (WARNING); parse failure (WARNING) | `1` |
| `sold_units` | INTEGER | Sold | Reported sold units | Yes | integer parse | `> total_units` (WARNING) | `1` |
| `district` | VARCHAR(128) | District | Revenue district | Yes | alias map, else title-case | not a Kerala district (WARNING) | `Ernakulam` |
| `taluk` | VARCHAR(128) | Taluk | Taluk | Yes | trim | — | `Kanayannur` |
| `village` | VARCHAR(255) | Village | Village / local body | Yes | trim | — | `Kakkanad` |
| `source_url` | TEXT | Source URL | Link to source record | Yes | trim | — | `https://rera.kerala.gov.in/...` |
| `first_seen_at` | TIMESTAMPTZ | — | When the project was first observed | No | UTC now | — | `2026-10-06T06:00:00Z` |
| `last_seen_at` | TIMESTAMPTZ | — | When last present in a run | No | UTC now | — | `2026-10-06T06:00:00Z` |
| `last_checked_at` | TIMESTAMPTZ | — | When last checked (seen or not) | No | UTC now | — | `2026-10-06T06:00:00Z` |
| `not_seen_in_latest_run` | BOOLEAN | — | Absent from the latest full run | No | derived | never deletes history | `false` |
| `consecutive_misses` | INTEGER | — | Consecutive runs absent | No | derived | investigate after repeats | `0` |
| `created_at` | TIMESTAMPTZ | — | Row creation time | No | UTC now | — | `2026-10-06T06:00:00Z` |
| `updated_at` | TIMESTAMPTZ | — | Row update time | No | UTC now (auto) | — | `2026-10-06T06:00:00Z` |

---

## Table: `project_snapshots` (immutable history)

Append-only. Shares the project's source fields (`rera_registration_number` …
`source_url`, with `promoter_name_raw` in place of `promoter_name`) plus:

| Field | Type | Description | Nullable |
|-------|------|-------------|----------|
| `id` | INTEGER PK | Snapshot key | No |
| `project_id` | INTEGER FK | Owning project | No |
| `snapshot_date` | DATE | Calendar date of the observation | No |
| `collected_at` | TIMESTAMPTZ | Exact collection time | No |
| `source_hash` | VARCHAR(64) | SHA-256 of canonicalised source fields | No |
| `raw_record` | JSON | Full original source row (verbatim) | Yes |
| `created_at` | TIMESTAMPTZ | Row creation time | No |

Snapshots are **never modified or deleted**.

---

## Table: `project_change_events`

| Field | Type | Description | Nullable |
|-------|------|-------------|----------|
| `id` | INTEGER PK | Event key | No |
| `project_id` | INTEGER FK | Affected project | No |
| `ingestion_run_id` | INTEGER FK | Run that detected the change | Yes |
| `detected_at` | TIMESTAMPTZ | Detection time | No |
| `field_name` | VARCHAR(128) | Changed field | No |
| `old_value` | TEXT | Previous value (stringified) | Yes |
| `new_value` | TEXT | New value (stringified) | Yes |
| `source_last_modified_date` | DATE | Source last-modified date at detection | Yes |
| `snapshot_id` | INTEGER FK | Snapshot in which the new value appears | Yes |
| `created_at` | TIMESTAMPTZ | Row creation time | No |

---

## Table: `ingestion_runs`

| Field | Type | Description |
|-------|------|-------------|
| `id` | INTEGER PK | Run key |
| `started_at` | TIMESTAMPTZ | Run start |
| `completed_at` | TIMESTAMPTZ | Run end |
| `source` | VARCHAR(255) | Adapter name |
| `collection_method` | VARCHAR(64) | e.g. `official_export_file_import` |
| `status` | VARCHAR(32) | `RUNNING` / `SUCCESS` / `PARTIAL` / `FAILED` |
| `parser_version` | VARCHAR(32) | Parser version used |
| `records_found` | INTEGER | Source rows seen |
| `records_inserted` | INTEGER | New projects |
| `records_updated` | INTEGER | Changed projects |
| `records_unchanged` | INTEGER | Unchanged projects |
| `records_failed` | INTEGER | Failed / skipped rows |
| `errors_count` | INTEGER | ERROR-severity findings |
| `source_reference` | TEXT | File path / URL |
| `error_summary` | TEXT | Failure summary |
| `created_at` | TIMESTAMPTZ | Row creation time |

---

## Table: `data_quality_issues`

| Field | Type | Description |
|-------|------|-------------|
| `id` | INTEGER PK | Issue key |
| `ingestion_run_id` | INTEGER FK | Run that produced the issue |
| `project_id` | INTEGER FK | Related project (if any) |
| `severity` | VARCHAR(16) | `INFO` / `WARNING` / `ERROR` |
| `field_name` | VARCHAR(128) | Field concerned |
| `issue_type` | VARCHAR(128) | Machine-readable rule id |
| `message` | TEXT | Human-readable message |
| `raw_value` | TEXT | Offending raw value |
| `created_at` | TIMESTAMPTZ | Row creation time |

---

## Table: `promoters`

| Field | Type | Description |
|-------|------|-------------|
| `id` | INTEGER PK | Promoter key |
| `canonical_name` | VARCHAR(512) UNIQUE | Canonical identity |
| `match_method` | VARCHAR(64) | How the match was made |
| `needs_review` | BOOLEAN | Flagged for manual review |
| `created_at` / `updated_at` | TIMESTAMPTZ | Timestamps |

> Promoters are **not** auto-merged on name similarity. Projects keep
> `promoter_name_raw`; canonical identity is a separate, reviewable concern.

---

## Table: `baselines`

| Field | Type | Description |
|-------|------|-------------|
| `id` | INTEGER PK | Baseline key |
| `label` | VARCHAR(128) | e.g. `initial` |
| `baseline_at` | TIMESTAMPTZ | Baseline timestamp |
| `source` | VARCHAR(255) | Source adapter |
| `record_count` | INTEGER | Records at baseline |
| `parser_version` | VARCHAR(32) | Parser version |
| `source_checksum` | VARCHAR(128) | SHA-256 of the source artefact |
| `ingestion_run_id` | INTEGER FK | Baseline run |
| `created_at` | TIMESTAMPTZ | Row creation time |
