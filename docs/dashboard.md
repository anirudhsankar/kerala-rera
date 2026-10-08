# Analytics Dashboard

A local, read-only analytics dashboard for the Kerala RERA dataset built on top
of Phase 1. It is **not** part of the Phase 1 ingestion pipeline and never
writes to source data.

```
PostgreSQL  ──▶  Analytics layer  ──▶  FastAPI (read-only)  ──▶  React SPA
              src/rera/analytics      src/rera/api            frontend/
```

---

## Components

| Layer | Path | Purpose |
|-------|------|---------|
| Analytics queries | `src/rera/analytics/queries.py` | Overview, timeline, district, builder, project search, data-quality |
| Promoter identity | `src/rera/analytics/promoters.py` | Conservative builder canonicalisation |
| API | `src/rera/api/app.py` | Read-only GET endpoints |
| Frontend | `frontend/` | Vite + React + TypeScript + ECharts SPA |

---

## Running

### 1. Backend (read-only API)

```powershell
pip install -e ".[api]"
rera serve --host 127.0.0.1 --port 8000
```

OpenAPI docs: http://127.0.0.1:8000/docs

The API uses `READ_ONLY_DATABASE_URL` when set (recommended), otherwise
`DATABASE_URL`. Prepare the least-privilege role once (as a superuser):

```sql
CREATE ROLE rera_readonly LOGIN PASSWORD 'rera_readonly';
GRANT CONNECT ON DATABASE rera TO rera_readonly;
GRANT USAGE ON SCHEMA public TO rera_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO rera_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO rera_readonly;
```

### 2. Builder canonicalisation (one-off / after new ingestions)

```powershell
rera promoters build            # idempotent
rera promoters build --dry-run  # preview
```

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxies /api → :8000)
npm run build      # production build into frontend/dist
```

---

## Pages

| Page | Contents |
|------|----------|
| **Overview** | KPIs (projects, units, sold, sell-through, units under development, completion passed); registrations over time; completion pipeline; status and type mix |
| **Find projects** | District → Taluk → Village drill-down; "registered in the last N months" window; newest-first results; best-effort taluk choropleth |
| **Districts** | Kerala choropleth; projects / sell-through by district; full district table; drill-down per district (type, taluks, top builders) |
| **Builders** | Top-15 chart; sortable leaderboard; concentration (top-10 share); builder detail with district footprint, type mix and projects |
| **Projects** | Search + filters (district/type/status) with pagination; project detail with promoter link, immutable snapshot history and change events |
| **History** | Cross-project change feed + trends (changes/month, by field, status transitions); project-level snapshot timeline |
| **Data & provenance** | Data-quality findings, ingestion runs, baseline, source caveats |

---

## API endpoints (all GET, read-only)

```
/api/health
/api/overview
/api/timeline?granularity=year|month
/api/districts
/api/districts/{district}
/api/builders?limit=&sort=projects|total_units|sold_units|districts
/api/builders/{promoter_id}
/api/projects?q=&district=&project_type=&project_status=&promoter_id=&limit=&offset=
/api/project?registration_number=...
/api/project/history?registration_number=...
/api/project/changes?registration_number=...
/api/filters
/api/runs?limit=
/api/baseline
/api/data-quality/summary
```

> The registration number contains `/`, so project detail endpoints take it as
> a query parameter rather than a path segment.

---

## Interface

* Responsive, public-facing layout with a sticky top bar and a global **search**
  that jumps straight to the Projects explorer.
* **Light/dark theme** toggle (remembered in the browser; charts re-theme too).
* Charts share an ECharts theme with soft gradients and rounded bars; KPI tiles
  and discovery panels (top districts / top builders) link into the detail pages.

## Analytical conventions

* **Derived metrics are labelled.** `overview.derived_metrics` lists them
  (sell-through, units under development, declared completion passed).
* **Neutral terminology.** The dashboard reports factual counts only. It never
  labels a project "delayed" or a promoter "bad".
* **Null units.** 167 `Plots` projects have no `total_units`; they are excluded
  from sell-through denominators and reported via `projects_without_units`.
* **Builder identity.** Names are canonicalised conservatively (trim / collapse
  spaces / upper / strip punctuation). Groups with more than one raw spelling
  are flagged `needs_review` and are **never** auto-merged with other groups.
  Raw spellings remain on each project.

---

## Map data & attribution

`frontend/public/kerala_districts.geojson` (14 Kerala districts) was derived
from the **geohacker/india** district dataset (GADM-style boundaries). District
names were mapped to canonical Kerala district names
(e.g. `Pattanamtitta` → `Pathanamthitta`).

> Verify the upstream licence before any redistribution. For a portfolio/
> non-commercial use this attribution is provided; make your own licence
> assessment before publishing.

### Taluk boundaries (best-effort)

`frontend/public/kerala_taluks.geojson` was derived from **GADM 4.1 ADM3**,
with a curated alias map from colonial-era GADM names to our source taluk names
(e.g. `Trivandrum` → `Thiruvananathapuram`, `Quilon` → `Kollam`, `Cochin` →
`Kochi`). Only **41** features map to taluks present in the dataset; unmatched
features are rendered **neutral (never guessed)**. Several taluks in the data
are post-1990 and have **no polygon** in GADM (e.g. Kanayannur, Attappadi
Tribal, Kondotty, Manjeshwaram, Ernad). **Villages are lists only** — no open
village-boundary dataset was available. GADM data is **non-commercial with
attribution**.

## Location API

```
GET /api/locations/taluks?district=
GET /api/locations/villages?district=&taluk=
GET /api/locations/by-taluk?district=
GET /api/locations/taluk?district=&taluk=
GET /api/locations/village?district=&taluk=&village=
GET /api/projects/new?district=&taluk=&village=&months=&limit=
```

`/api/projects` and `/api/filters` also accept `taluk`/`village` for cascading
filters and filtering.

## History API

```
GET /api/changes?district=&taluk=&field_name=&since=&limit=&offset=
GET /api/history/summary
GET /api/project/history?registration_number=...
GET /api/project/changes?registration_number=...
```

History is append-only: `project_snapshots` and `project_change_events` are never
modified or deleted. Charts populate as new exports are ingested; a single
baseline yields one snapshot per project.

---

## Testing

```powershell
python -m pytest            # includes tests/test_analytics.py and tests/test_api.py
cd frontend; npm run build  # type-check + production build
```

---

## Scope

This is a **local** dashboard: no authentication, not publicly deployed, and
read-only. Public deployment, auth and scheduled refresh are separate future
work.
