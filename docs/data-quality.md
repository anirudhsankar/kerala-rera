# Data Quality

Validation is **non-fatal by design**: questionable records are stored and a
finding is recorded in `data_quality_issues`. Records are never silently
discarded.

## Severities

| Severity | Meaning |
|----------|---------|
| `INFO` | Notable but expected; no action required |
| `WARNING` | Suspicious value; investigate if widespread |
| `ERROR` | Critical field problem; record may be skipped |

A run's status is `PARTIAL` if any `ERROR` exists or any row failed, otherwise
`SUCCESS`. `FAILED` is reserved for systemic failures (fetch/parse exceptions).

## Rules

| # | issue_type | Severity | Field | When |
|---|------------|----------|-------|------|
| 1 | `missing_registration_number` | ERROR | `rera_registration_number` | Empty/missing identity |
| 2 | `missing_project_name` | WARNING | `project_name` | Empty/missing name |
| 3 | `invalid_date` | WARNING | date fields | Unparseable date |
| 4 | `invalid_number` | WARNING | `total_units`, `sold_units` | Unparseable integer |
| 5 | `completion_before_start` | WARNING | `declared_completion_date` | Completion earlier than start |
| 6 | `sold_exceeds_total` | WARNING | `sold_units` | Sold units > total units |
| 7 | `negative_total_units` / `negative_sold_units` | WARNING | unit fields | Negative counts |
| 8 | `unknown_district` | WARNING | `district` | Not a known Kerala district |
| 9 | `unexpected_status` | INFO | `project_status` | Value outside controlled vocabulary |
| 10 | `unexpected_project_type` | INFO | `project_type` | Value outside controlled vocabulary |
| 11 | `future_start_date` | INFO | `project_start_date` | Start date in the future |
| 12 | `declared_completion_date_passed` | INFO | `declared_completion_date` | Date is in the past (factual only) |
| 13 | `duplicate_registration_number` | ERROR | `rera_registration_number` | Same reg. number occurs more than once in a batch |
| 14 | `duplicate_row_skipped` | ERROR | `rera_registration_number` | Second duplicate row skipped for the run |
| 15 | `row_parse_error` | ERROR | — | Row had no mapped values / could not be built |
| 16 | `normalization_failed` | ERROR | — | Unexpected normalisation error |
| 17 | `column_warning` (log only) | — | — | Multiple export columns map to one field |
| 18 | `missing_required_column` (log only) | — | — | Required column absent from export |

## Neutral terminology

Rule 12 is deliberately worded as a **fact**, not a judgement. The pipeline
never emits labels such as “delayed”, “defaulting” or “bad promoter”.
Interpretation is left to a later phase and, when added, must be clearly
labelled as derived/interpretive.

## Detecting duplicate registration numbers

`detect_duplicate_registrations()` counts occurrences within a batch. Duplicate
rows are reported as `ERROR`; only the first occurrence is persisted for that
run, to prevent two rows fighting over one identity. Historical records are
untouched.

## Reporting

* `python -m rera.cli.main validate --sample --verbose` — list findings.
* `python -m rera.cli.main stats` — aggregate project statistics.
* `data_quality_issues` — queryable findings per run/project.
* `ingestion_runs` — per-run warning/error counts and status.
