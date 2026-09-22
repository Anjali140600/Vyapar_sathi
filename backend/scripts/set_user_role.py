"""Assign a role from a trusted terminal; users cannot promote themselves via API."""

import argparse

from sqlalchemy import func

from backend.app.core.database import SessionLocal
from backend.app.core.security import VALID_ROLES
from backend.app.models.schema import User


def set_role(email: str, role: str) -> None:
    normalized_role = role.strip().lower()
    if normalized_role not in VALID_ROLES:
        raise ValueError(f"Role must be one of: {', '.join(sorted(VALID_ROLES))}")

    db = SessionLocal()
    try:
        user = db.query(User).filter(
            func.lower(User.email) == email.strip().lower()
        ).first()
        if not user:
            raise ValueError("User not found")
        user.role = normalized_role
        db.commit()
        print(f"Updated {user.email} to role: {normalized_role}")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assign a Vyapar Sathi user role")
    parser.add_argument("email")
    parser.add_argument("role", choices=sorted(VALID_ROLES))
    arguments = parser.parse_args()
    set_role(arguments.email, arguments.role)
