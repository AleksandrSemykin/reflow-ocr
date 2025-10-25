# Reflow OCR – Frontend

Electron + React shell for the Reflow OCR desktop experience.

## Prerequisites

- Node.js 20+
- pnpm / npm (scripts assume npm, adjust if needed)

## Install

```powershell
cd frontend
npm install
```

## Development

```powershell
npm run dev
```

This spawns Vite (renderer) and Electron (main) processes simultaneously. Ensure the backend is running on `http://127.0.0.1:8000`.

## Build (renderer only for now)

```powershell
npm run build
```

Further packaging (electron-builder) will be added once the OCR pipeline is integrated.
