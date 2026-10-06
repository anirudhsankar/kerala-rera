"""Ingestion primitives: collection, parsing, normalisation, validation."""

from rera.ingestion.change_detector import (
    ChangeEventData,
    detect_changes,
    normalized_values,
    project_values,
)
from rera.ingestion.collector import CollectedData, Collector, save_raw_artifact
from rera.ingestion.normalizer import (
    NormalizedProject,
    compute_source_hash,
    hashed_values,
    normalize_record,
)
from rera.ingestion.parser import ParseError, ParseResult, RawProjectRecord, parse_records
from rera.ingestion.quality import QualityIssue
from rera.ingestion.snapshot import build_snapshot
from rera.ingestion.validator import (
    detect_duplicate_registrations,
    validate_record,
)

__all__ = [
    "ChangeEventData",
    "detect_changes",
    "normalized_values",
    "project_values",
    "CollectedData",
    "Collector",
    "save_raw_artifact",
    "NormalizedProject",
    "compute_source_hash",
    "hashed_values",
    "normalize_record",
    "ParseError",
    "ParseResult",
    "RawProjectRecord",
    "parse_records",
    "QualityIssue",
    "build_snapshot",
    "detect_duplicate_registrations",
    "validate_record",
]
