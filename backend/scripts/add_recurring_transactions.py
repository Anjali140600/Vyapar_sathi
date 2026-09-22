"""Idempotent MySQL migration for the recurring-transactions feature."""

from sqlalchemy import inspect, text

from backend.app.core.database import engine


COLUMN_STATEMENTS = {
    "is_recurring": (
        "ALTER TABLE transactions "
        "ADD COLUMN is_recurring BOOLEAN NOT NULL DEFAULT FALSE"
    ),
    "frequency": "ALTER TABLE transactions ADD COLUMN frequency VARCHAR(20) NULL",
    "next_run_date": "ALTER TABLE transactions ADD COLUMN next_run_date DATE NULL",
    "recurring_parent_id": (
        "ALTER TABLE transactions ADD COLUMN recurring_parent_id BIGINT NULL"
    ),
}


def run_migration() -> None:
    if engine.dialect.name != "mysql":
        raise RuntimeError("This migration currently supports the project's MySQL database.")

    with engine.begin() as connection:
        columns = {column["name"] for column in inspect(connection).get_columns("transactions")}
        for name, statement in COLUMN_STATEMENTS.items():
            if name not in columns:
                connection.execute(text(statement))
                print(f"Added transactions.{name}")

        inspector = inspect(connection)
        index_names = {
            index["name"] for index in inspector.get_indexes("transactions")
        }

        if "ix_transactions_recurring_due" not in index_names:
            connection.execute(
                text(
                    "CREATE INDEX ix_transactions_recurring_due "
                    "ON transactions (is_recurring, next_run_date)"
                )
            )
            print("Added recurring schedule index")

        if "uq_transactions_recurring_occurrence" not in index_names:
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX uq_transactions_recurring_occurrence "
                    "ON transactions (recurring_parent_id, date)"
                )
            )
            print("Added recurring occurrence uniqueness rule")

        foreign_keys = {
            foreign_key.get("name")
            for foreign_key in inspect(connection).get_foreign_keys("transactions")
        }
        if "fk_transactions_recurring_parent" not in foreign_keys:
            connection.execute(
                text(
                    "ALTER TABLE transactions "
                    "ADD CONSTRAINT fk_transactions_recurring_parent "
                    "FOREIGN KEY (recurring_parent_id) REFERENCES transactions(id) "
                    "ON DELETE SET NULL"
                )
            )
            print("Added recurring template foreign key")

    print("Recurring-transactions migration complete.")


if __name__ == "__main__":
    run_migration()
