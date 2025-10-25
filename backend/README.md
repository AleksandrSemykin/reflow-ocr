# Reflow OCR – Backend

FastAPI service that powers OCR processing, session storage, and export orchestration for the Reflow OCR desktop application.

## Prerequisites

- Python 3.11
- [Poetry](https://python-poetry.org/) 1.7+

## Setup

```powershell
cd backend
poetry install
```

## Development Server

```powershell
poetry run uvicorn reflow_ocr.app:app --reload --port 8000
```

API will be available at `http://127.0.0.1:8000`. Interactive docs: `http://127.0.0.1:8000/docs`.

## Tests & Linting

```powershell
poetry run pytest
poetry run ruff check .
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REFLOW_ENV` | `development` | Sets environment mode (development/production/test). |
| `REFLOW_DATA_DIR` | Platform-specific app data path | Root directory for sessions, models, caches. |
| `REFLOW_LOG_LEVEL` | `INFO` | Logging verbosity. |

All configuration options live in `reflow_ocr/core/config.py`.
