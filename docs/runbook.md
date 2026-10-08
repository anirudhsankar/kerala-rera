# Operations Runbook

Day-to-day operation of the K-RERA data pipeline and dashboard.

## Monthly data refresh (manual download → automatic ingest)

The official export is behind an anti-bot challenge, so a **human downloads it in a
browser**; everything after that is automated.

1. **Download** the full, **unfiltered** register export from K-RERA (browser → Export).
   Endpoint (for reference):
   ```
   https://rera.kerala.gov.in/export-projects?project_name=&registration_number=&district=&taluk=&village=&work_status=&from=&to=
   ```
   > Use **no filters**. A filtered export would be treated as the full register
   > and would wrongly flag the other projects as "not seen".

2. **Save** it into `data/raw/manual/` using a dated name:
   ```
   data/raw/manual/krera_YYYY-MM.xlsx
   ```

3. **(Optional) commit** it to the repo (exports are tracked):
   ```powershell
   git add data/raw/manual/krera_YYYY-MM.xlsx
   git commit -m "data: K-RERA export YYYY-MM"
   git push
   ```

4. **Ingest** — either let the scheduled task do it, or run it now:
   ```powershell
   rera update                 # or: powershell -ExecutionPolicy Bypass -File scripts\update.ps1
   ```
   `rera update` picks the **newest** file in `data/raw/manual/`, ingests it, and
   rebuilds builder links. If the file is unchanged it prints
   `No new data: source checksum matches the last run; skipping.`

5. **Verify**:
   ```powershell
   rera status
   ```
   Dashboard: **History** page (new changes), **Data & provenance** (runs, baseline).

## Scheduled task

A Windows Scheduled Task runs `scripts\update.ps1` **daily at 09:00**; it no-ops
until a new export appears.

```powershell
# register / update the schedule
powershell -ExecutionPolicy Bypass -File scripts\register-schedule.ps1
powershell -ExecutionPolicy Bypass -File scripts\register-schedule.ps1 -Time "07:30"

# inspect
Get-ScheduledTask -TaskName "KeralaRERA-Update"
Get-ScheduledTaskInfo -TaskName "KeralaRERA-Update"

# remove
powershell -ExecutionPolicy Bypass -File scripts\register-schedule.ps1 -Remove
```

Logs: `data/logs/update.log`.

## What each ingest does

- Appends a new **snapshot** only for projects whose source values changed.
- Records **change events** (declared completion date, sold units, status, …).
- Flags projects absent from the export as `not_seen_in_latest_run` — **never deletes**.
- Preserves the raw file under `data/raw/YYYY/MM/DD/ingestion_run_<id>/` + `metadata.json`.
- Is **idempotent**: re-running the same file changes nothing.

## Rules & caveats

- **Unfiltered export only** for the pipeline (full reconciliation).
- Ingest **before** overwriting a file; use dated filenames (they avoid the issue).
- History starts at the **baseline** date; it grows with each refresh.
- The export has no "last modified" field, so every ingest is a full comparison.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| `No new data … skipping` | Expected if the file is unchanged. Confirm you saved a *new* export. |
| `Update failed while fetching source: Anti-bot challenge …` | `RERA_EXPORT_URL` is set to a shielded URL. Leave it empty and use the manual file. |
| Run status `PARTIAL` | Usually the known duplicate registration number; see **Data & provenance**. |
| Schedule didn't run | `Get-ScheduledTaskInfo`; ensure the venv exists and `rera.exe` path is correct. |
| No history/changes shown | Only a baseline has been ingested so far; ingest a newer export. |

## Configuration

`.env` (see `.env.example`): `DATABASE_URL`, `READ_ONLY_DATABASE_URL`,
`RERA_EXPORT_URL` (leave empty), `CORS_ORIGINS`, `LOG_LEVEL`. Never commit `.env`.

## Deployment

See [`deploy.md`](deploy.md) for Vercel + Supabase + Render/Fly + GitHub Actions.
