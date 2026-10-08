# Source Inspection — Kerala RERA (K-RERA)

**Inspection date:** 2026-10-06
**Environment:** Windows, Python 3.11.9, `curl 8.13.0`, `httpx`
**Inspector:** Phase 1 reconnaissance (automated, read-only)
**Base URL:** https://rera.kerala.gov.in/

> This document records what was **actually observed**, not what was assumed.
> Anything that could not be verified is explicitly marked **"not confirmed"**.

---

## 1. Summary

| # | Question | Finding |
|---|----------|---------|
| 1 | Project listing URL | `https://rera.kerala.gov.in/projects` — live access **blocked** (see §3) |
| 2 | Export mechanism | Official export obtained by a human via browser — **confirmed** (§7) |
| 3 | Export format | **XLSX**, single sheet `Worksheet` — **confirmed** (§7) |
| 4 | Number of pages | N/A for the export file — **confirmed** (§7) |
| 5 | Pagination mechanism | N/A for the export file — **confirmed** (§7) |
| 6 | Available listing columns | 13 columns — **confirmed** (§7) |
| 7 | Project detail URL pattern | **not confirmed** (blocked) |
| 8 | Publicly accessible detail fields | **not confirmed** (blocked) |
| 9 | Quarterly progress availability | **not confirmed** (blocked) |
| 10 | Publicly accessible structured requests | **not confirmed** (blocked) |
| 11 | Limitations | Active anti-bot JS challenge on the live site; export is human-obtained |
| 12 | Recommended collection method | **Human-in-the-loop official export file import** |

---

## 2. Environment used for inspection

```
OS            : win32 (Windows, PowerShell 5.1)
Python        : 3.11.9
HTTP client   : curl 8.13.0 (also httpx 0.27)
User-Agent    : Mozilla/5.0 (Windows NT 10.0; Win64; x64) KeralaRERA-Research/1.0
Redirects     : not followed (to observe the raw response)
```

---

## 3. What was observed

Every request to the K-RERA host returned **HTTP 503** with a small HTML body
that loads a JavaScript challenge from an external anti-bot service. Example
response body (truncated):

```html
<html><body>
<script type="text/javascript"
  src="https://prophaze-botmodule-static-assets.s3.ap-south-1.amazonaws.com/aes.min.js"></script>
<script>
  function toNumbers(d){...}
  function toHex(){...}
  var a=toNumbers("deadbeefdeadbeefdeadbeefdeadbeef"),
      b=toNumbers("deadbeefdeadbeefdeadbeefdeadbeef"),
      c=toNumbers("0521ecd0c76cfd7bfcc4050f41a8be19");
  document.cookie="BPC="+toHex(slowAES.decrypt(c,2,a,b))+"; expires=...; path=/";
  document.location.href="https://rera.kerala.gov.in/";
</script>
</body></html>
```

The page expects a browser to execute the JavaScript, compute an AES-derived
value, store it in a `BPC` cookie, and reload. Without executing that
JavaScript, the server keeps returning 503.

**This is an active anti-bot / access-control mechanism (Prophaze BotModule).**

### Paths probed

| Path | Status | Body |
|------|--------|------|
| `/` | 503 | Prophaze JS challenge |
| `/projects` | 503 | Prophaze JS challenge |
| `/project` | 503 | Prophaze JS challenge |
| `/project-search` | 503 | Prophaze JS challenge |
| `/api/projects` | 503 | Prophaze JS challenge |
| `/robots.txt` | 503 | Prophaze JS challenge |
| `/sitemap.xml` | 503 | Prophaze JS challenge |

Response headers observed include `Server`, `Content-Type: text/html`, and the
external challenge asset host `prophaze-botmodule-static-assets.s3.ap-south-1.amazonaws.com`.

---

## 4. Why this blocks automated collection

* `robots.txt` could not be retrieved, so the site's stated crawling policy is
  **not confirmed**.
* No public export endpoint or API could be inspected.
* Reproducing the cookie challenge programmatically would constitute
  **circumventing an anti-bot mechanism**. Per the project's principles
  (do not bypass CAPTCHA/authentication/access controls; do not circumvent
  anti-bot mechanisms), this project deliberately does **not** do that.

---

## 5. Alternative official sources checked

| Source | Reachable | Contains K-RERA project register? |
|--------|-----------|-----------------------------------|
| `https://www.data.gov.in` | Yes (HTTP 200) | **not confirmed** |
| `https://kerala.data.gov.in` | Yes (HTTP 200) | **not confirmed** |

A short search of these portals did not return a confirmed K-RERA project
register dataset. This is **not confirmed** to exist; further manual research
would be required.

---

## 6. Conclusion and recommended method

Because the live site is protected by an anti-bot challenge, the pipeline does
**not** automate against it. The recommended and implemented Phase 1 method is:

> **Human-in-the-loop official export import.**
> A person opens K-RERA in a normal browser (solving the challenge naturally,
> as any visitor does), uses the site's own export facility, and places the
> resulting official file (CSV/XLSX) into `data/raw/manual/`. The pipeline then
> parses, validates, normalises and stores that **official** artefact.

A disabled `KReraHttpSource` placeholder exists for a future, legitimate HTTP
collector, and `python -m rera.cli.main inspect-source` performs a single
polite probe and reports the challenge detection without attempting to bypass
it.

### Fields used by the implemented pipeline

Because the official export columns could not be confirmed, the pipeline uses
the field set specified in the project brief. These column names are treated as
**assumed/illustrative** and are matched through a tolerant alias table
(`src/rera/ingestion/parser.py`). When the real export is available, only the
alias table needs updating — no schema redesign is required.

| Canonical field | Status |
|-----------------|--------|
| `rera_registration_number` | assumed from brief |
| `project_name` | assumed from brief |
| `promoter_name` | assumed from brief |
| `project_type` | assumed from brief |
| `project_status` | assumed from brief |
| `project_start_date` | assumed from brief |
| `declared_completion_date` | assumed from brief |
| `certificate_number` | assumed from brief |
| `certificate_date` | assumed from brief |
| `last_modified_date` | assumed from brief |
| `total_units` | assumed from brief |
| `sold_units` | assumed from brief |
| `district` / `taluk` / `village` | assumed from brief |

> **Important:** The export column names and format are now **confirmed** from
> an official export file — see §7. Project detail pages, quarterly progress
> and structured request endpoints remain **not confirmed** because the live
> site is blocked.

---

## 7. Confirmed export structure (official file)

**File inspected:** `data/raw/manual/project1.xlsx` (human-downloaded, 2026-10-06)
**Method:** read-only inspection via `python -m rera.cli.main inspect-file`

| Property | Value |
|----------|-------|
| Format | XLSX |
| Sheets | 1 (`Worksheet`) |
| Header row | row 0 (no title/preamble rows) |
| Data rows | **1681** |
| Columns | **13** |
| Date format | ISO `YYYY-MM-DD` |
| Numeric fields | clean non-negative integers |
| Distinct districts | 14 (all valid Kerala districts, canonical spelling) |

### Columns

```
Project, Promoter Name, Project Type, Project Start Date, Date of Completion,
Certificate No, Certificate Date, Total, Sold, Status, District, Village, Taluk
```

### Confirmed canonical mapping

| Export column | DB field(s) | Notes |
|---------------|-------------|-------|
| `Certificate No` | `rera_registration_number` **and** `certificate_number` | Holds `K-RERA/PRJ/...`; unique except one duplicate |
| `Project` | `project_name` | |
| `Promoter Name` | `promoter_name_raw` | |
| `Project Type` | `project_type` | stored verbatim |
| `Project Start Date` | `project_start_date` | ISO |
| `Date of Completion` | `declared_completion_date` | ISO |
| `Certificate Date` | `certificate_date` | ISO |
| `Total` | `total_units` | empty for all `Plots` rows |
| `Sold` | `sold_units` | |
| `Status` | `project_status` | `Inprogress` / `Completed` |
| `District` / `Village` / `Taluk` | same | |
| — | `last_modified_date`, `source_url` | absent from this export → NULL |

### Observed vocabularies

* **Status:** `Inprogress` (914), `Completed` (767)
* **Project Type:** `Residential (Apartment)` (1122), `Villas (Plots & Buildings)` (272),
  `Plots` (167), `Mixed (Commercial & Residential)` (101), `Shops/Office Space (Commercial)` (19)

### Data quality observed

* Registration-number duplicate: `K-RERA/PRJ/231/2020` appears twice
  ("LANDMARK VILLAGE TOWER VII" and its "PHASE II").
* `sold > total`: 21 rows.
* `Total` empty: 167 rows (all `Plots`).
* `declared_completion_date` already passed: 889 rows (factual, not a delay determination).
* `completion_before_start`: 0 · future start: 0 · unknown district: 0.

> **Completeness note:** whether this export represents the full K-RERA
> register cannot be confirmed from the file alone. The pipeline reports
> exactly what the export contains.


---

## 8. Discovered export endpoint (2026-10-08)

The public project register exposes an export endpoint:

```
https://rera.kerala.gov.in/export-projects
  ?project_name=&registration_number=&district=&taluk=&village=&work_status=&from=&to=
```

**Observed result from a server-to-server request:** `HTTP 503` with the same
**Prophaze BotModule** JavaScript/cookie challenge (body loads
`prophaze-botmodule-static-assets.../aes.min.js` and sets a `BPC` cookie).

**Conclusion:** the export endpoint is protected by the same anti-bot mechanism
as the rest of the site. Automated download is therefore **not performed** — the
project does not bypass anti-bot controls. `rera update` with `RERA_EXPORT_URL`
set to this URL **fails safely**:

```
Anti-bot challenge detected at the export URL; automated download is not permitted.
Provide the file manually instead.
```

The endpoint **is usable in a normal browser** (a human solves the challenge
naturally), and its filter parameters are:

| Param | Meaning |
|-------|---------|
| `project_name` | Filter by project name |
| `registration_number` | Filter by RERA registration number |
| `district` | Filter by district |
| `taluk` | Filter by taluk |
| `village` | Filter by village |
| `work_status` | Filter by status |
| `from`, `to` | Date range |

> **Operational note:** ingest an **unfiltered** register export for the
> reconciliation pipeline. A filtered export (e.g. one district) would be treated
> as a full snapshot and would incorrectly flag other projects as
> `not_seen_in_latest_run`. Use filtered exports only for ad-hoc analysis.
