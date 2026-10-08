FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies + package (src layout)
COPY pyproject.toml README.md ./
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./

RUN python -m pip install --upgrade pip && pip install -e ".[postgres,api]"

EXPOSE 8000

# Render/Fly provide $PORT; default to 8000 locally.
CMD ["sh", "-c", "uvicorn rera.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
