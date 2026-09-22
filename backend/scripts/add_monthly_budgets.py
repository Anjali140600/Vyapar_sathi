"""Idempotently create the monthly budget table."""

from backend.app.core.database import engine
from backend.app.models.schema import MonthlyBudget


def run_migration() -> None:
    MonthlyBudget.__table__.create(bind=engine, checkfirst=True)
    print("Monthly budget migration complete.")


if __name__ == "__main__":
    run_migration()
