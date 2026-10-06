# Ingestion Methodology

This is a **secondary analytical dataset** derived from publicly available
K-RERA information. It is not an official K-RERA product and must not be
presented as such.

## What source is used

Official K-RERA public export files (CSV/XLSX) obtained by a human through
normal browser use. See `data-source.md` and `source-inspection.md`.

## How data is collected

1. Raw artefact is read from `data/raw/manual/` (or `--source-file`) by
   `KReraExportFileSource`.
2. The artefact's bytes are copied to
   `data/raw/YYYY/MM/DD/ingestion_run_<id>/` with a `metadata.json` recording:
   source URL, collection timestamp, HTTP status (if any), collection method,
   parser version, record count and SHA-256 checksum.
3. Rows are parsed, normalised and validated.
4. Records are upserted idempotently; snapshots and change events are appended.

## Collection frequency (production design)

| Cadence | Activity |
|---------|----------|
| Daily | Check the listing/export; detect new or modified projects |
| Weekly | Full reconciliation against the complete export |
| Quarterly/periodic | Review quarterly progress information when available |

The source's own `last_modified_date` field is used wherever present to
prioritise checks. Quarterly *reporting* does not mean the website should only
be *checked* quarterly.

> Because live access is currently blocked (anti-bot), the actual cadence is
> whatever schedule a human obtains fresh official exports on. Scheduling can
> be a simple cron / GitHub Actions job once legitimate access exists.

## How changes are detected

1. A project is identified by `rera_registration_number`.
2. A deterministic `source_hash` (SHA-256 of canonical source fields) is
   computed.
3. If the hash equals the latest snapshot's hash: the project is **unchanged**
   (only `last_seen_at` / `last_checked_at` are refreshed; no new snapshot).
4. If the hash differs: a **new snapshot** is created, field-level **change
   events** are recorded, and the current project row is updated.

## How missing records are handled

If a project present in the database is absent from a later full run it is
**never deleted**. It is marked `not_seen_in_latest_run = true` and
`consecutive_misses` is incremented. A single absence may simply reflect
pagination, filtering, an outage or a parsing change. Repeated absences are
what warrant investigation. (Disappearance tracking is skipped for partial /
`--limit` runs so a limited run cannot mask everything as "missing".)

## How raw data is preserved

* Byte-for-byte source artefact + `metadata.json` under `data/raw/`.
* Full original row per record in `project_snapshots.raw_record`.
* `raw_values` retained during normalisation for debugging.

Raw datasets are git-ignored (they may be large and are regenerable).

## Baseline

The first successful full ingestion is recorded once in `baselines` with the
baseline timestamp, source, record count, parser version and source checksum.

## Limitations

* **Live scraping is out of scope** due to the active anti-bot challenge.
* Export **column names/formats are unconfirmed**; they are matched via a
  tolerant alias table.
* Controlled vocabularies (status/type) are **illustrative** and only flag
  unknown values.
* Normalisation is best-effort; unparseable values are retained raw and
  flagged.
* No claim is made about the completeness of any given export.
* Date ambiguity (e.g. `01/02/2022`) is resolved as **day-first**, matching
  Indian convention.

## Data quality issues

See `data-quality.md`. Findings are recorded in `data_quality_issues`; they
never cause silent data loss.

## Legal and ethical considerations

* Only publicly accessible information is used.
* No CAPTCHA, authentication or anti-bot mechanism is bypassed.
* Request behaviour is polite (configurable delay, timeout, bounded retries),
  though the current method performs no repeated live requests.
* This dataset is clearly presented as a secondary, derived analytical dataset.
* Source values are preserved and provenance is recorded.

## Analytical distinction

The system separates, and never conflates:

* **SOURCE FACT** — “Declared completion date: 31 December 2027”.
* **DERIVED METRIC** — “Declared completion date has passed”.
* **INTERPRETATION** — “Project is delayed” *(never produced automatically)*.
