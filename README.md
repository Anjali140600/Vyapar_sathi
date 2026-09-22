# Vyapar Sathi

Vyapar Sathi is organized by responsibility so the active application is easy to navigate.

## Project structure

```text
backend/
  app/                 FastAPI routes, models, schemas, and API orchestration
  scripts/             Database and knowledge-base maintenance commands
  static/              Production frontend build served by FastAPI
  uploads/             Runtime user uploads (git-ignored)

frontend/
  src/                 React application source
  scripts/             Frontend build helpers
  package.json         Frontend dependencies and commands

python_services/
  rag/                 GST retrieval and ChromaDB data
  llm/                 Groq/Ollama model client
  routing/             Intent classification
  database_humanizer/  Database-result response formatting
  calculator_humanizer/Calculation-result response formatting
  cli.py               Standalone three-module assistant

docs/                  Project guides and PDF-generation scripts
examples/              Sample image and audio inputs
legacy/                Older prototypes kept for reference only
```

The root `.env` is shared by the backend and Python services. `requirements.txt` contains their shared Python dependencies.

## Run locally

Start the backend from the repository root:

```powershell
.\venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Start the frontend in a second terminal:

```powershell
cd frontend
npm run dev -- --host 0.0.0.0
```

Open <http://localhost:5173>. The frontend proxies `/api` requests to the backend on port 8000.

## Build the frontend

```powershell
cd frontend
npm run build
```

The build is written to `backend/static`, where FastAPI serves it.

## Standalone Python assistant

```powershell
.\venv\Scripts\python.exe -m python_services.cli
```

See the README inside each main directory for more detail.
