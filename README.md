# Reflow OCR

Проект настольного приложения с GUI (Electron + React) и локальным Python backend (FastAPI), предназначенного для высокоточного OCR и восстановления верстки (DOCX/PDF/Markdown).

## Структура репозитория

- `PLAN.md` — актуальная дорожная карта (фазы 0–8).
- `backend/` — FastAPI сервис (Poetry, Python 3.11).
- `frontend/` — Electron + React + Vite оболочка.

## Быстрый старт

### Backend
```powershell
cd backend
poetry install
poetry run uvicorn reflow_ocr.app:app --reload --port 8000
```

### Frontend
```powershell
cd frontend
npm install
npm run dev
```

По умолчанию renderer запускается на `http://127.0.0.1:5173`, а Electron окно автоматически подключается к дев-серверу. Backend слушает `http://127.0.0.1:8000`.

## Тесты

```powershell
cd backend
poetry run pytest
```

Линтеры: `poetry run ruff check .` и `npm run lint`.

## Лицензия

Apache-2.0 — см. `LICENSE`.
