# Kerala RERA Intelligence

[![CI](https://github.com/anirudhsankar/kerala-rera/actions/workflows/ci.yml/badge.svg)](https://github.com/anirudhsankar/kerala-rera/actions/workflows/ci.yml)

Automated acquisition, structured storage and historical change tracking for
publicly available **Kerala Real Estate Regulatory Authority (K-RERA)** project
information.

> **Phase 1 scope:** data acquisition, storage and change detection only.
> No frontend, public API, authentication, payments or AI features.

---

## Problem

K-RERA publishes project information publicly, but analysing trends and
historical changes across projects requires structured data processing. The
public site presents information one project at a time and does not expose a
convenient, versioned, analysable dataset.

## Phase 1

Build a reliable, maintainable and auditable K-RERA **data ingestion pipeline**
that:

* acquires public K-RERA data,
* stores it in PostgreSQL,
* preserves historical snapshots,
* detects changes over time,
* records provenance and data quality issues,
* and exposes a simple CLI.

The goal is **a trustworthy historical K-RERA dataset, not merely a scraper.**

---

## Architecture

```mermaid
flowchart TB
    subgraph Source
        HR["Human downloads official<br/>K-RERA export (CSV/XLSX)"]
    end

    subgraph "Acquisition"
        SA["Source adapter<br/>KReraExportFileSource"]
        RAW["Raw preservation<br/>data/raw/YYYY/MM/DD/run_id"]
        PARSE["Parser<br/>header mapping"]
        NORM["Normaliser<br/>dates / numbers / vocab"]
        VAL["Validator<br/>quality rules"]
    end

    subgraph "Storage (PostgreSQL)"
        PROJ["projects<br/>(latest state)"]
        SNAP["project_snapshots<br/>(immutable)"]
        CHG["project_change_events"]
        DQ["data_quality_issues"]
        RUN["ingestion_runs"]
        BASE["baselines"]
    end

    HR --> SA --> RAW
    SA --> PARSE --> NORM --> VAL --> SVC["Ingestion service"]
    SVC --> PROJ
    SVC --> SNAP
    SVC --> CHG
    SVC --> DQ
    SVC --> RUN
    SVC --> BASE
    SNAP -. "different snapshot" .-> CHG
```

Diagram source: [`docs/architecture.md`](docs/architecture.md).

---

## Data source

Official K-RERA public information (`https://rera.kerala.gov.in/`).

**Important:** as of 2026-10-06 the live site is protected by an active
anti-bot JavaScript/cookie challenge (Prophaze BotModule); every probed path,
including `/projects` and `/robots.txt`, returns HTTP 503 until the challenge
is solved in a browser. This project **does not bypass anti-bot mechanisms**.

Instead it uses the site's **official export** obtained by a human through
normal browser use, placed in `data/raw/manual/`. See
[`docs/source-inspection.md`](docs/source-inspection.md) and
[`docs/data-source.md`](docs/data-source.md).

---

## Pipeline

```
Source → Raw → Parse → Validate → Normalise → PostgreSQL → Snapshots → Change Events
```

* **Source** — official export file (human-obtained).
* **Raw** — byte-for-byte copy + `metadata.json` (URL, method, timestamp,
  checksum, parser version).
* **Parse** — tolerant header/alias mapping into canonical fields.
* **Normalise** — dates, integers, districts, statuses (raw values retained).
* **Validate** — non-fatal quality findings.
* **Snapshots** — immutable, hash-gated.
* **Change Events** — field-level diffs between observations.

---

## Installation

Requires **Python 3.11+** (3.12+ recommended) and PostgreSQL for production
(SQLite works for development/tests).

```powershell
# 1. Clone / open the project
cd D:\Anirudh\RERA

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install (includes PostgreSQL driver)
pip install -e ".[dev,postgres]"

# 4. Configure environment
Copy-Item .env.example .env
#   then edit DATABASE_URL, e.g.
#   DATABASE_URL=postgresql+psycopg://rera:rera@localhost:5432/rera
```

### Create the PostgreSQL database (production)

```sql
CREATE USER rera WITH PASSWORD 'rera';
CREATE DATABASE rera OWNER rera;
```

Apply the schema with Alembic:

```powershell
alembic upgrade head
```

(`python -m rera.cli.main init-db` is a development convenience that creates
missing tables directly.)

---

## Configuration

Configuration lives in `.env` (see `.env.example`); nothing is hard-coded.

| Variable | Purpose | Default |
|----------|---------|---------|
| `DATABASE_URL` | SQLAlchemy database URL | `sqlite:///./data/rera.db` |
| `RERA_BASE_URL` | K-RERA base URL | `https://rera.kerala.gov.in` |
| `RERA_REQUEST_DELAY_SECONDS` | Delay between requests | `2` |
| `RERA_MAX_RETRIES` | Max retries | `3` |
| `RERA_TIMEOUT_SECONDS` | HTTP timeout | `30` |
| `RERA_USER_AGENT` | Identifying User-Agent | `KeralaRERA-Intelligence/0.1 ...` |
| `RAW_DATA_PATH` | Raw artefact root | `./data/raw` |
| `MANUAL_IMPORT_PATH` | Where official exports are dropped | `./data/raw/manual` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `PARSER_VERSION` | Parser version stamped on runs | `1.0.0` |

`.env` is git-ignored; never commit credentials.

---

## Running

```powershell
# Probe the live site (read-only, no bypass) and report the anti-bot challenge
python -m rera.cli.main inspect-source

# Inspect an export file's structure/column mapping (read-only, no DB writes)
python -m rera.cli.main inspect-file --source-file data/raw/manual/project1.xlsx

# Ingest the bundled sample (deterministic)
python -m rera.cli.main ingest --sample

# Ingest an official export you downloaded into data/raw/manual/
python -m rera.cli.main ingest
python -m rera.cli.main ingest --source-file "C:\path\to\krera_export.xlsx"

# Preview without changing the database
python -m rera.cli.main ingest --dry-run

# Validate a file and list findings
python -m rera.cli.main validate --sample --verbose

# Show detected changes (dry run vs stored events)
python -m rera.cli.main detect-changes --sample

# Operational reporting
python -m rera.cli.main status
python -m rera.cli.main stats
python -m rera.cli.main export --output data/processed/projects.csv
```

> On Windows PowerShell, structured logs are written to **stderr** and may be
> prefixed with `python.exe :` by the shell. This is normal.

### Example ingest output

```
K-RERA INGESTION
  Source method:        official_export_file_import
  Source found:         10
  New:                  10
  Changed:              0
  Unchanged:            0
  Failed:               0
  Duplicates:           0
  Validation warnings:  3
  Validation errors:    0
  Change events:        0
  Status:               SUCCESS
  Baseline:             created
  Raw artefact:         data\raw\2026\10\06\ingestion_run_1
```

### Idempotency

Running the same ingestion twice produces **no duplicates**:

```
Run 1:  new=10  changed=0  unchanged=0
Run 2:  new=0   changed=0  unchanged=10
```

---

## Testing

```powershell
python -m pytest
```

The suite covers the parser, normalisation (dates, numbers, vocabularies,
hashing), validation rules, change detection, and database integration
(initial load, idempotency, snapshot immutability, duplicates, disappearance,
dry-run). Tests use an in-memory SQLite database and the bundled sample
fixtures — they never touch the live site or a production database.

```powershell
# Lint
python -m ruff check src tests
```

---

## Project layout

```
pyproject.toml        .env.example        README.md
alembic.ini
docs/                 data-source.md  data-dictionary.md  architecture.md
                      ingestion-methodology.md  data-quality.md  source-inspection.md
migrations/           Alembic env + initial schema
src/rera/             config, logging_config, constants
  database/           models.py, session.py
  sources/            base.py, krera.py
  ingestion/          collector, parser, normalizer, validator, snapshot,
                      change_detector, quality
  services/           ingestion_service.py
  cli/                main.py
tests/                test_parser, test_normalizer, test_validator,
                      test_change_detection, test_database
data/                 raw/  sample/  processed/
```

---

## Dashboard (Phase 2)

A local, read-only analytics dashboard over the ingested data:

```powershell
# 1. canonicalise builders (once / after new ingestions)
rera promoters build

# 2. run the read-only API
pip install -e ".[api]"
rera serve --host 127.0.0.1 --port 8000      # docs at /docs

# 3. run the frontend
cd frontend
npm install
npm run dev                                   # http://localhost:5173
```

Pages: **Overview**, **Districts** (choropleth + drill-down), **Builders**
(leaderboard + detail), **Projects** (search/detail/history), and
**Data & provenance**. See [`docs/dashboard.md`](docs/dashboard.md).

The dashboard is read-only and uses a least-privilege DB role
(`READ_ONLY_DATABASE_URL`). It reports factual/derived metrics only and never
labels a project "delayed" or a promoter "bad".

---

## Data limitations

* **Live scraping is out of scope** due to the active anti-bot challenge; the
  official-export workflow is used instead.
* Export **format and columns are confirmed** for the first official file
  (XLSX, 13 columns); see [`docs/source-inspection.md`](docs/source-inspection.md#7-confirmed-export-structure-official-file).
  Project detail pages, quarterly progress and structured endpoints remain
  unconfirmed.
* The registration number is carried in the export column `Certificate No`
  (`K-RERA/PRJ/...`) and stored in both `rera_registration_number` and
  `certificate_number`.
* Export **pagination and detail pages are unconfirmed**; matching is via a
  tolerant alias table.
* Status/type **controlled vocabularies are illustrative**; unknown values are
  flagged, not corrected.
* Records are keyed by `rera_registration_number`; changes to that identifier
  are treated as a new identity.
* Normalisation is best-effort. Unparseable values are stored raw and flagged.
* The dataset is a **secondary, derived product** and is not official K-RERA
  data.
* The pipeline never deletes records that disappear from a run; it flags them
  for investigation.
* No determination of “delay” or “default” is produced automatically.

---

## Documentation

| Document | Contents |
|----------|----------|
| [`docs/source-inspection.md`](docs/source-inspection.md) | Live-site reconnaissance findings |
| [`docs/data-source.md`](docs/data-source.md) | Source and acquisition method |
| [`docs/data-dictionary.md`](docs/data-dictionary.md) | Every field documented |
| [`docs/architecture.md`](docs/architecture.md) | Components and data model |
| [`docs/ingestion-methodology.md`](docs/ingestion-methodology.md) | End-to-end methodology |
| [`docs/data-quality.md`](docs/data-quality.md) | Validation rules and severities |
| [`docs/ingestion-report.md`](docs/ingestion-report.md) | Phase 1 baseline ingestion report |
| [`docs/dashboard.md`](docs/dashboard.md) | Analytics dashboard (API + React frontend) |

---

## License

MIT. The data originates from publicly available K-RERA information and remains
subject to the source's own terms of use.
