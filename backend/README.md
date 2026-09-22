# Backend

This directory contains the FastAPI application and its runtime files.

- `app/api`: HTTP route handlers
- `app/core`: database and security configuration
- `app/models`: SQLAlchemy database models
- `app/schemas`: request and response schemas
- `app/services`: application orchestration and domain services
- `scripts`: database initialization, migration, and RAG ingestion utilities
- `static`: generated React production build
- `uploads`: runtime upload storage

Run from the repository root:

```powershell
.\venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

## Recurring-transactions migration

Run this once for an existing database before starting the updated backend:

```powershell
.\venv\Scripts\python.exe -m backend.scripts.add_recurring_transactions
```

The migration is idempotent, so rerunning it does not duplicate columns or indexes.

## Payment/due tracking migration

Run this once for an existing database:

```powershell
.\venv\Scripts\python.exe -m backend.scripts.add_payment_due_tracking
```

Existing transactions are preserved as fully paid. New transactions can then
store partial payments and due dates.
