"""Vercel Python entrypoint.

Exposes the FastAPI ASGI application for the `app` service. The project uses a
``src/`` layout, so add it to ``sys.path`` before importing the package.

Vercel loads the top-level ``app`` object from this module (see
``entrypoint: "index:app"`` in ``vercel.json``).
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rera.api.app import app  # noqa: E402

__all__ = ["app"]
