"""Structured (key=value) logging setup.

Produces log lines such as::

    2026-10-06T06:00:05+00:00 INFO records parsed records=1632

Any ``extra={...}`` fields passed to a logger call are rendered as key=value
pairs, which keeps logs machine-parseable without pulling in a heavy
dependency.
"""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime
from typing import Any

_STANDARD_ATTRS = set(logging.makeLogRecord({}).__dict__.keys()) | {
    "message",
    "asctime",
}


def _render_value(value: Any) -> str:
    text = str(value)
    if any(ch.isspace() for ch in text) or "=" in text:
        return '"' + text.replace('"', '\\"') + '"'
    return text


class StructuredFormatter(logging.Formatter):
    """Render a record as ``<iso timestamp> <LEVEL> <message> key=value...``."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=UTC).isoformat()
        line = f"{timestamp} {record.levelname} {record.getMessage()}"

        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_ATTRS and not key.startswith("_")
        }
        if extras:
            rendered = " ".join(
                f"{key}={_render_value(value)}" for key, value in sorted(extras.items())
            )
            line = f"{line} {rendered}"

        if record.exc_info:
            line = f"{line}\n{self.formatException(record.exc_info)}"
        return line


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger once with the structured formatter."""

    root = logging.getLogger()
    root.setLevel(level.upper())

    # Avoid duplicate handlers when called repeatedly (e.g. across tests).
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(StructuredFormatter())
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
