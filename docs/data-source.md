# Data Source

## Primary source

Official Kerala Real Estate Regulatory Authority (K-RERA) public information.

* Base URL: `https://rera.kerala.gov.in/`
* Project register reference URL: `https://rera.kerala.gov.in/projects`
* Owner: Kerala Real Estate Regulatory Authority (Government of Kerala)

## Access reality (see `source-inspection.md`)

As of **2026-10-06**, the K-RERA website is protected by an active anti-bot
JavaScript/cookie challenge (Prophaze BotModule). All probed paths — including
`/projects` and `/robots.txt` — return HTTP 503 until the challenge is solved
in a browser.

Consequently this project **does not scrape the live site** and does **not**
attempt to bypass the protection. It uses the official export facility instead,
obtained by a human through normal browser use.

## Acquisition method: official export file import

1. A human opens K-RERA in a normal browser and locates the official project
   register / public search export facility.
2. The official export (CSV or XLSX) is downloaded.
3. The file is placed in `data/raw/manual/` (or any path passed via
   `--source-file`).
4. The pipeline imports it:

   ```powershell
   python -m rera.cli.main ingest            # uses the latest file in data/raw/manual/
   python -m rera.cli.main ingest --source-file path\to\export.xlsx
   ```

The original file is preserved byte-for-byte under
`data/raw/YYYY/MM/DD/ingestion_run_<id>/` together with a `metadata.json`
provenance file.

## Supported export formats

* CSV / TXT (comma-separated, header row required)
* XLSX / XLSM / XLS (sheet selectable; header row auto-detected)

Encoding is auto-detected for CSV (`utf-8-sig`, `utf-8`, `latin-1`). All values
are read as strings and preserved before normalisation.

### Confirmed official export (2026-10-06)

The first real export (`project1.xlsx`) is a single-sheet XLSX with **1681
rows** and 13 columns. See [`source-inspection.md`](source-inspection.md#7-confirmed-export-structure-official-file)
for the full confirmed mapping. Key point: the registration number is carried
in the column labelled **`Certificate No`** (`K-RERA/PRJ/...`), and unit counts
are labelled **`Total`** / **`Sold`**.

## Why not a live scraper

The project brief explicitly requires: *"Do not bypass CAPTCHA,
authentication, access controls, rate limits or other technical restrictions"*
and *"Do not attempt to circumvent anti-bot mechanisms."* The K-RERA site
imposes exactly such a mechanism, so automated collection is out of scope until
a legitimate, publicly accessible structured endpoint is confirmed.

## Future legitimate acquisition options

* A confirmed official CSV/XLSX/JSON export URL that responds without the
  challenge (e.g. from an allowlisted network).
* An official bulk-download or open-data publication (e.g. on `data.gov.in`),
  if one is confirmed to exist.
* A documented public API.

The pluggable `ReraSource` interface (`src/rera/sources/base.py`) allows any of
these to be added without touching the storage, normalisation or change
detection layers.

## Provenance

Every record carries source information:

* `projects.source_url`
* `project_snapshots.raw_record` (the full original row, verbatim)
* `ingestion_runs.source_reference`, `collection_method`, `parser_version`
* `data/raw/**/metadata.json` (URL/method/timestamp/HTTP status/checksum)
