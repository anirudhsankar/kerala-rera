# Deployment (Vercel + Supabase + Render/Fly + GitHub Actions)

Target architecture:

```
Official export ──▶ GitHub Actions (scheduled) runs `rera update`
                     └─ download (if URL reachable) → ingest → snapshots/changes
                                                        └────────────▶ Supabase Postgres
Vercel (React SPA) ──▶ FastAPI API (Render/Fly) ──(read-only role)──────────┘
```

Nothing here is required for local development.

---

## 1. Supabase (PostgreSQL)

1. Create a project at supabase.com (free tier is enough).
2. From **Project settings → Database → Connection string**, copy **two** URLs:
   - **Pooler** (port `6543`, IPv4) — used by the API and the update job.
   - **Direct/session** (port `5432`) — used for migrations (`alembic`).
3. Create a least-privilege read-only role (run as the DB owner in the SQL editor):

   ```sql
   CREATE ROLE rera_readonly LOGIN PASSWORD '<strong-password>';
   GRANT USAGE ON SCHEMA public TO rera_readonly;
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO rera_readonly;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO rera_readonly;
   ```

4. Apply the schema and load the baseline from your machine:

   ```powershell
   $env:DATABASE_URL="postgresql+psycopg://<user>:<pass>@<direct-host>:5432/postgres"
   alembic upgrade head
   $env:DATABASE_URL="postgresql+psycopg://<user>:<pass>@<pooler-host>:6543/postgres"
   rera ingest --source-file data/raw/manual/project1.xlsx
   rera promoters build
   ```

   (Alternatively `pg_dump` the local DB and restore into Supabase. Re-ingesting is
   simpler and the dataset is small.)

---

## 2. API — Render (or Fly / Railway)

A `Dockerfile` and `render.yaml` are included at the repo root.

1. Create a new **Web Service** from this GitHub repo, runtime **Docker**.
2. Set environment variables:
   - `DATABASE_URL` = Supabase **pooler** URL (with `postgresql+psycopg://`)
   - `READ_ONLY_DATABASE_URL` = pooler URL for `rera_readonly`
   - `CORS_ORIGINS` = your Vercel domain(s), e.g. `https://kerala-rera.vercel.app`
3. Health check: `/api/health`.
4. Start command is in the Dockerfile: `uvicorn rera.api.app:app --host 0.0.0.0 --port $PORT`.

Fly alternative: `fly launch` (Dockerfile detected), set the same env vars, `fly deploy`.

---

## 3. Frontend — Vercel

1. Import the repo into Vercel.
2. **Root directory:** `frontend`
3. **Framework preset:** Vite (build `npm run build`, output `dist`).
4. Environment variable: `VITE_API_BASE=https://<your-api-host>` (no trailing slash).
5. `frontend/vercel.json` already adds the SPA rewrite for client-side routing.
6. Deploy, then make sure the API's `CORS_ORIGINS` includes the Vercel URL.

---

## 4. Scheduled updates — GitHub Actions

`.github/workflows/update.yml` runs monthly (03:00 UTC on the 1st) and can be
triggered manually (`workflow_dispatch`).

Add these **repository secrets** (Settings → Secrets and variables → Actions):

| Secret | Purpose |
|--------|---------|
| `SUPABASE_DATABASE_URL` | Pooler URL (`postgresql+psycopg://…`) for ingestion |
| `SUPABASE_MIGRATION_URL` | Direct/session URL for `alembic upgrade` (optional) |
| `RERA_EXPORT_URL` | Public export URL for automated download (optional) |

Behaviour:
- Runs `alembic upgrade head`, then `rera update` (download → ingest → rebuild promoters).
- `rera update` **skips** if the source checksum matches the last run.
- If `RERA_EXPORT_URL` returns the anti-bot challenge page, the job **fails safely**
  (no circumvention) — fall back to committing a manually downloaded export.

> **Full automation requires a reachable export URL.** Capture the actual download
> URL from your browser (F12 → Network) when you export, test it once
> (`python -m rera.cli.main inspect-file` won't work for URLs — use a plain GET in
> a browser tab or `curl`). If it returns the Prophaze JSON/JS challenge, automated
> download isn't permitted; keep the file in `data/raw/manual/` instead.

---

## 5. Secrets & safety

- Never commit secrets. `.env` is git-ignored; production values live in Render/Vercel/GitHub.
- The API serves **read-only** and should use the `rera_readonly` role.
- Supabase IPv4: prefer the **pooler** connection for app/jobs; use the direct URL for migrations.

---

## 6. Local development (unchanged)

```powershell
rera serve --host 127.0.0.1 --port 8000     # API
cd frontend; npm run dev                     # UI at http://localhost:5173 (proxies /api)
```
