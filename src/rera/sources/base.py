"""Source adapter interface.

The pipeline is deliberately decoupled from any single acquisition mechanism.
Concrete adapters (local official-file export, future HTTP download, etc.)
implement :class:`ReraSource`. This matters because the K-RERA website
structure and access controls may change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


class SourceError(Exception):
    """Base class for source acquisition errors."""


class SourceUnavailableError(SourceError):
    """The source could not be reached (network, anti-bot, outage)."""


class SourceFormatError(SourceError):
    """A source artefact was retrieved but could not be parsed."""


@dataclass
class SourceMetadata:
    """Provenance metadata for a single collection."""

    source: str
    collection_method: str
    parser_version: str
    collected_at: datetime
    source_url: str | None = None
    source_reference: str | None = None
    file_name: str | None = None
    http_status: int | None = None
    record_count: int = 0
    checksum_sha256: str | None = None
    raw_bytes_size: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "source": self.source,
            "collection_method": self.collection_method,
            "parser_version": self.parser_version,
            "collected_at": self.collected_at.isoformat(),
            "source_url": self.source_url,
            "source_reference": self.source_reference,
            "file_name": self.file_name,
            "http_status": self.http_status,
            "record_count": self.record_count,
            "checksum_sha256": self.checksum_sha256,
            "raw_bytes_size": self.raw_bytes_size,
        }
        payload.update(self.extra)
        return payload


@dataclass
class FetchResult:
    """Raw records plus provenance returned by a source adapter."""

    records: list[dict[str, Any]]
    columns: list[str]
    metadata: SourceMetadata
    raw_bytes: bytes = b""


class ReraSource(ABC):
    """Interface implemented by all K-RERA source adapters."""

    name: str = "abstract"

    @abstractmethod
    def fetch_export(self) -> FetchResult:
        """Fetch the full project register export (records + metadata)."""

    def fetch_project_listing(self, **kwargs: Any) -> FetchResult:  # pragma: no cover
        raise NotImplementedError

    def fetch_project_details(self, project_reference: str, **kwargs: Any) -> FetchResult:
        raise NotImplementedError
