"""K-RERA source adapters.

Two adapters are provided:

* :class:`KReraExportFileSource` - ingests an *official* K-RERA export file
  (CSV/XLSX) that a human downloaded from the website in a normal browser.
  This is the primary, safest acquisition method for Phase 1 because it does
  not automate against, or attempt to bypass, the site's anti-bot protection.

* :class:`KReraHttpSource` - a deliberately non-operational placeholder for a
  future HTTP collector. Live HTTP collection is currently blocked by an
  active Prophaze BotModule JavaScript challenge; automating past it would be
  circumventing an anti-bot mechanism, which this project does not do. The
  adapter therefore raises :class:`SourceUnavailableError` for collection and
  only offers a polite, read-only ``inspect`` probe.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rera.config import get_settings
from rera.constants import COLLECTION_METHOD_FILE, COLLECTION_METHOD_HTTP
from rera.ingestion.parser import build_records_from_grid
from rera.sources.base import (
    FetchResult,
    ReraSource,
    SourceFormatError,
    SourceMetadata,
    SourceUnavailableError,
)

# Substrings that indicate the Prophaze BotModule challenge response.
_CHALLENGE_MARKERS = (
    "prophaze-botmodule-static-assets",
    "slowAES.decrypt",
    "document.cookie=\"BPC=",
    "BPC=",
)


class KReraExportFileSource(ReraSource):
    """Read an official K-RERA export file from disk.

    The file is treated as an opaque official artefact: its bytes are preserved
    for provenance and its rows are passed through unmodified to the parser.
    """

    name = "krera_export_file"

    def __init__(
        self,
        file_path: str | Path,
        *,
        source_url: str | None = None,
        parser_version: str | None = None,
        sheet_name: str | int | None = None,
        header_row: int | None = None,
    ) -> None:
        self.file_path = Path(file_path)
        self.source_url = source_url
        self.parser_version = parser_version or get_settings().parser_version
        self.sheet_name = sheet_name
        self.header_row = header_row
        self.sheet_names: list[str] = []
        self.last_header_row: int | None = None
        self.last_header_score: int | None = None

    def fetch_export(self) -> FetchResult:
        if not self.file_path.exists():
            raise SourceUnavailableError(f"Export file not found: {self.file_path}")

        raw_bytes = self.file_path.read_bytes()
        checksum = hashlib.sha256(raw_bytes).hexdigest()
        records, columns = self._read_records()

        metadata = SourceMetadata(
            source="K-RERA official export file",
            collection_method=COLLECTION_METHOD_FILE,
            parser_version=self.parser_version,
            collected_at=datetime.now(UTC),
            source_url=self.source_url,
            source_reference=str(self.file_path),
            file_name=self.file_path.name,
            http_status=None,
            record_count=len(records),
            checksum_sha256=checksum,
            raw_bytes_size=len(raw_bytes),
            extra={
                "sheet_names": self.sheet_names,
                "header_row": self.last_header_row,
                "header_score": self.last_header_score,
            },
        )
        return FetchResult(
            records=records, columns=columns, metadata=metadata, raw_bytes=raw_bytes
        )

    # -- internals ---------------------------------------------------------
    def read_grid(self) -> list[list[Any]]:
        """Read the export (selected/first sheet) into a grid of strings."""

        suffix = self.file_path.suffix.lower()
        try:
            import pandas as pd
        except ImportError as exc:  # pragma: no cover
            raise SourceFormatError("pandas is required to read export files") from exc

        if suffix in {".csv", ".txt"}:
            self.sheet_names = ["<csv>"]
            frame = self._read_delimited(pd)
        elif suffix in {".xlsx", ".xlsm", ".xls"}:
            try:
                sheets = pd.ExcelFile(self.file_path).sheet_names
                self.sheet_names = list(sheets)
                frame = pd.read_excel(
                    self.file_path,
                    sheet_name=self.sheet_name if self.sheet_name is not None else 0,
                    header=None,
                    dtype=str,
                    keep_default_na=False,
                )
            except Exception as exc:  # noqa: BLE001
                raise SourceFormatError(f"Could not read workbook: {exc}") from exc
        else:
            raise SourceFormatError(
                f"Unsupported export format '{suffix}'. Expected CSV or XLSX."
            )

        if frame is None or frame.empty:
            raise SourceFormatError("Export file contains no rows.")

        return [
            ["" if value is None else str(value) for value in row]
            for row in frame.values.tolist()
        ]

    def _read_records(self) -> tuple[list[dict[str, Any]], list[str]]:
        grid = self.read_grid()
        built = build_records_from_grid(grid, self.header_row)
        self.last_header_row = built.header_row
        self.last_header_score = built.header_score
        if not built.rows:
            raise SourceFormatError("Export file contains no data rows below the header.")
        return built.rows, built.columns

    def _read_delimited(self, pd: Any) -> Any:
        last_error: Exception | None = None
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return pd.read_csv(
                    self.file_path,
                    header=None,
                    dtype=str,
                    keep_default_na=False,
                    encoding=encoding,
                )
            except UnicodeDecodeError as exc:
                last_error = exc
                continue
            except Exception as exc:  # noqa: BLE001
                raise SourceFormatError(f"Could not read CSV: {exc}") from exc
        raise SourceFormatError(f"Could not decode CSV file: {last_error}")


def _looks_like_challenge(body: str) -> bool:
    return any(marker in body for marker in _CHALLENGE_MARKERS)


def inspect_krera_live(
    url: str | None = None,
    *,
    timeout: int | None = None,
) -> dict[str, Any]:
    """Polite, read-only probe of the live K-RERA site.

    Performs a *single* GET request and reports what is observed. It never
    attempts to solve or bypass the anti-bot challenge.
    """

    import httpx

    settings = get_settings()
    target = url or settings.rera_base_url
    timeout = timeout or settings.rera_timeout_seconds

    result: dict[str, Any] = {
        "url": target,
        "status_code": None,
        "anti_bot_challenge": False,
        "retrievable": False,
        "notes": [],
    }
    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=False,
            headers={"User-Agent": settings.rera_user_agent},
        ) as client:
            response = client.get(target)
        body = response.text[:20000]
        result["status_code"] = response.status_code
        result["content_type"] = response.headers.get("content-type")
        result["server"] = response.headers.get("server")
        if _looks_like_challenge(body):
            result["anti_bot_challenge"] = True
            result["notes"].append(
                "Prophaze BotModule JavaScript/cookie challenge detected. "
                "Automated collection is not performed (anti-bot bypass is out of scope)."
            )
        elif response.status_code == 200:
            result["retrievable"] = True
        else:
            result["notes"].append(f"Non-200 response: {response.status_code}")
    except Exception as exc:  # noqa: BLE001
        result["notes"].append(f"Request failed: {exc}")
    return result


class KReraHttpSource(ReraSource):
    """Placeholder HTTP adapter - disabled until legitimate access exists."""

    name = "krera_http"

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or get_settings().rera_base_url

    def fetch_export(self) -> FetchResult:
        raise SourceUnavailableError(
            "Live K-RERA HTTP collection is disabled: the site is protected by an "
            "active anti-bot challenge and this project does not bypass such controls. "
            "Provide an official export file via the manual import workflow instead."
        )

    def inspect(self) -> dict[str, Any]:
        return inspect_krera_live(self.base_url)


def collection_method_for(source: ReraSource) -> str:
    if isinstance(source, KReraExportFileSource):
        return COLLECTION_METHOD_FILE
    if isinstance(source, KReraHttpSource):
        return COLLECTION_METHOD_HTTP
    return source.name
