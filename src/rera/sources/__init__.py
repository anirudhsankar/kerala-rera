"""Source adapters package."""

from rera.sources.base import (
    FetchResult,
    ReraSource,
    SourceError,
    SourceFormatError,
    SourceMetadata,
    SourceUnavailableError,
)
from rera.sources.krera import (
    KReraExportFileSource,
    KReraHttpSource,
    collection_method_for,
    inspect_krera_live,
)

__all__ = [
    "FetchResult",
    "ReraSource",
    "SourceError",
    "SourceFormatError",
    "SourceMetadata",
    "SourceUnavailableError",
    "KReraExportFileSource",
    "KReraHttpSource",
    "collection_method_for",
    "inspect_krera_live",
]
