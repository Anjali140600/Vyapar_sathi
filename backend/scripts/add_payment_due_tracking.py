"""Idempotent MySQL migration for payment and udhaar tracking."""

from sqlalchemy import inspect, text

from backend.app.core.database import engine


COLUMN_STATEMENTS = {
    "amount_paid": (
        "ALTER TABLE transactions "
        "ADD COLUMN amount_paid DECIMAL(15,2) NOT NULL DEFAULT 0"
    ),
    "amount_due": (
        "ALTER TABLE transactions "
        "ADD COLUMN amount_due DECIMAL(15,2) NOT NULL DEFAULT 0"
    ),
    "due_date": "ALTER TABLE transactions ADD COLUMN due_date DATE NULL",
}


def run_migration() -> None:
    if engine.dialect.name != "mysql":
        raise RuntimeError("This migration currently supports the project's MySQL database.")

    with engine.begin() as connection:
        columns = {column["name"] for column in inspect(connection).get_columns("transactions")}
        added_payment_columns = False

        for name, statement in COLUMN_STATEMENTS.items():
            if name not in columns:
                connection.execute(text(statement))
                added_payment_columns = True
                print(f"Added transactions.{name}")

        if added_payment_columns:
            # Transactions created before this feature must not suddenly appear
            # as unpaid. They are migrated as fully settled.
            connection.execute(
                text(
                    "UPDATE transactions "
                    "SET amount_paid = amount, amount_due = 0, due_date = NULL"
                )
            )
            print("Marked existing transactions as fully paid")

        index_names = {
            index["name"]
            for index in inspect(connection).get_indexes("transactions")
        }
        if "ix_transactions_open_dues" not in index_names:
            connection.execute(
                text(
                    "CREATE INDEX ix_transactions_open_dues "
                    "ON transactions (user_id, amount_due, due_date)"
                )
            )
            print("Added open-dues lookup index")

    print("Payment/due tracking migration complete.")


if __name__ == "__main__":
    run_migration()
