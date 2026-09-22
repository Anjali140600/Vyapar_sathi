"""Idempotent migration from the legacy user role to enforced business roles."""

from sqlalchemy import inspect, text

from backend.app.core.database import engine


def run_migration() -> None:
    with engine.begin() as connection:
        columns = {column["name"] for column in inspect(connection).get_columns("users")}
        if "role" not in columns:
            connection.execute(
                text("ALTER TABLE users ADD COLUMN role VARCHAR(30) NOT NULL DEFAULT 'owner'")
            )
            print("Added users.role")

        connection.execute(
            text(
                "UPDATE users SET role = 'owner' "
                "WHERE role IS NULL OR TRIM(role) = '' OR LOWER(role) = 'user'"
            )
        )
        if engine.dialect.name == "mysql":
            connection.execute(
                text(
                    "ALTER TABLE users MODIFY COLUMN role "
                    "VARCHAR(30) NOT NULL DEFAULT 'owner'"
                )
            )
    print("User role migration complete. Existing accounts are owners.")


if __name__ == "__main__":
    run_migration()
