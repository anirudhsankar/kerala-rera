# Phase 1 Ingestion Report

**Report date:** 2026-10-06
**Database:** PostgreSQL 17.11 (`rera` @ localhost:5432)
**Parser version:** `1.0.0`

This is the **baseline ingestion** of the first official K-RERA export and the
evidence for Phase 1 acceptance.

---

## 1. Source

| Property | Value |
|----------|-------|
| File | `data/raw/manual/project1.xlsx` |
| Format | XLSX, single sheet `Worksheet` |
| Collection method | `official_export_file_import` (human-obtained) |
| SHA-256 | `205e9d41dd06034ae1b87ca9243ee3c00616fec818ce37a60a87e68720c400ae` |
| Rows in export | 1681 |

Raw artefacts preserved under:

* `data/raw/2026/10/06/ingestion_run_1/` (baseline)
* `data/raw/2026/10/06/ingestion_run_2/` (verification run)

---

## 2. Baseline (run #1)

```
Source found:         1681
New:                  1680
Changed:              0
Unchanged:            0
Failed:               1
Duplicates:           1
Validation warnings:  21
Validation errors:    2
Status:               PARTIAL
Baseline:             created
```

| Baseline field | Value |
|----------------|-------|
| `baseline_at` | 2026-10-06T16:38:38+05:30 |
| `record_count` | 1680 |
| `parser_version` | 1.0.0 |
| `source_checksum` | `205e9d41…20c400ae` |

---

## 3. Verification run #2 (identical source)

```
Source found:         1681
New:                  0
Changed:              0
Unchanged:            1680
Failed:               1
Status:               PARTIAL
```

**Idempotency confirmed:** no new projects, no changes, no duplicate rows.
No additional snapshots were created.

---

## 4. Persisted state

| Table | Rows |
|-------|------|
| `projects` | 1680 |
| distinct `rera_registration_number` | 1680 (0 duplicates) |
| `project_snapshots` | 1680 |
| `project_change_events` | 0 |
| `ingestion_runs` | 2 |
| `data_quality_issues` | 1824 (912 per run) |
| `baselines` | 1 |

### Projects by district

Ernakulam 574 · Thiruvananthapuram 460 · Thrissur 227 · Kozhikode 139 ·
Palakkad 116 · Kottayam 54 · Kannur 35 · Malappuram 22 · Kollam 16 ·
Pathanamthitta 15 · Alappuzha 8 · Idukki 6 · Wayanad 5 · Kasaragod 3

### Projects by status

Inprogress 913 · Completed 767

### Projects by type

Residential (Apartment) 1122 · Villas (Plots & Buildings) 272 · Plots 167 ·
Mixed (Commercial & Residential) 100 · Shops/Office Space (Commercial) 19

---

## 5. Data quality findings (per run)

| Severity | Count | Rule |
|----------|-------|------|
| WARNING | 21 | `sold_exceeds_total` |
| INFO | 889 | `declared_completion_date_passed` |
| ERROR | 2 | `duplicate_registration_number` + `duplicate_row_skipped` |
| **Total** | **912** | |

* The single duplicate identity is `K-RERA/PRJ/231/2020` ("LANDMARK VILLAGE
  TOWER VII" and its "PHASE II"). Per design, the first row is stored and the
  second is flagged, not silently dropped.
* `declared_completion_date_passed` is a **neutral factual observation**, not a
  determination of delay.
* No unmapped columns; no missing required columns; 0 rows failed normalisation.

---

## 6. Acceptance result

| Requirement | Result |
|-------------|--------|
| First run: new > 0, snapshots > 0 | ✅ 1680 / 1680 |
| Second run: new 0, changed 0, unchanged all | ✅ 0 / 0 / 1680 |
| Duplicate projects | ✅ 0 |
| Change event on modification | ✅ (verified with fixtures, see `tests/`) |
| Errors 0 or documented | ✅ 2 documented duplicate errors |

**Conclusion:** Phase 1 acceptance criteria met against real official data.

---

## 7. Caveats

* Completeness of the export vs. the full K-RERA register is **not confirmed**.
* `last_modified_date` and `source_url` are absent from the export and are NULL.
* `Total` is empty for the 167 `Plots` rows (`total_units` is NULL).
* The run status is `PARTIAL` solely because of the one documented duplicate
  identity; this is expected and does not indicate a pipeline fault.
