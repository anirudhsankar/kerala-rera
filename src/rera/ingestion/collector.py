"""Raw data collection and preservation.

The collector wraps a :class:`ReraSource`, fetches the export and writes the
raw artefact plus a ``metadata.json`` provenance file to::

    data/raw/YYYY/MM/DD/ingestion_run_<id|dry-run>/
        <source_file>
        metadata.json

The raw artefact is stored byte-for-byte so any parsing can be reproduced.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from rera.config import get_settings
from rera.sources.base import FetchResult, ReraSource, SourceMetadata


@dataclass
class CollectedData:
    fetch: FetchResult
    raw_path: str | None


def _artifact_dir(base_path: Path, collected_at: datetime, run_id: int | None) -> Path:
    day = collected_at.strftime("%Y/%m/%d")
    label = f"ingestion_run_{run_id}" if run_id is not None else "dry_run"
    return base_path / day / label


def save_raw_artifact(
    metadata: SourceMetadata,
    raw_bytes: bytes,
    *,
    run_id: int | None,
    base_path: Path | None = None,
) -> str:
    """Persist the raw source artefact and its metadata; return the directory."""

    base_path = base_path or get_settings().raw_data_path
    directory = _artifact_dir(base_path, metadata.collected_at, run_id)
    directory.mkdir(parents=True, exist_ok=True)

    file_name = metadata.file_name or "source_export.bin"
    (directory / file_name).write_bytes(raw_bytes)

    meta_payload = metadata.to_dict()
    meta_payload["run_id"] = run_id
    (directory / "metadata.json").write_text(
        json.dumps(meta_payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return str(directory)


class Collector:
    """Fetch data from a source and preserve the raw artefact."""

    def __init__(self, *, raw_base_path: Path | None = None) -> None:
        self.raw_base_path = raw_base_path

    def collect(
        self, source: ReraSource, *, run_id: int | None = None, dry_run: bool = False
    ) -> CollectedData:
        fetch = source.fetch_export()
        raw_path = save_raw_artifact(
            fetch.metadata,
            fetch.raw_bytes,
            run_id=run_id,
            base_path=self.raw_base_path,
        )
        return CollectedData(fetch=fetch, raw_path=raw_path)
