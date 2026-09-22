"""Payment and udhaar calculations for transactions."""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models.schema import Transaction


INCOME_TYPES = {"sales", "service", "other_income", "income"}
MONEY_STEP = Decimal("0.01")


def _money(value: Decimal | float | int | str) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_STEP, rounding=ROUND_HALF_UP)


def calculate_payment_fields(
    total_amount: Decimal | float,
    amount_paid: Decimal | float | None,
    due_date: date | None,
) -> tuple[Decimal, Decimal, date | None]:
    """Validate paid money and derive the outstanding amount."""
    total = _money(total_amount)
    paid = total if amount_paid is None else _money(amount_paid)

    if total < 0:
        raise ValueError("Transaction amount cannot be negative.")
    if paid < 0:
        raise ValueError("Amount paid cannot be negative.")
    if paid > total:
        raise ValueError("Amount paid cannot exceed the transaction amount.")

    due = total - paid
    if due > 0 and due_date is None:
        raise ValueError("A due date is required when an amount is outstanding.")

    return paid, due, due_date if due > 0 else None


def due_direction(transaction_type: str | None) -> str:
    """Classify outstanding money as receivable or payable."""
    return "receivable" if (transaction_type or "").lower() in INCOME_TYPES else "payable"


class PaymentDueService:
    @staticmethod
    def record_payment(transaction: Transaction, payment_amount: float) -> None:
        payment = _money(payment_amount)
        current_paid = _money(transaction.amount_paid or 0)
        total = _money(transaction.amount)

        if payment <= 0:
            raise ValueError("Payment amount must be greater than zero.")
        if current_paid + payment > total:
            raise ValueError("Payment exceeds the outstanding amount.")

        transaction.amount_paid = current_paid + payment
        transaction.amount_due = total - transaction.amount_paid
        if transaction.amount_due == 0:
            transaction.due_date = None

    @staticmethod
    def outstanding_totals(db: Session, user_id: str) -> dict[str, float]:
        base_filters = (
            Transaction.user_id == user_id,
            Transaction.amount_due > 0,
        )
        receivables = db.query(func.sum(Transaction.amount_due)).filter(
            *base_filters,
            Transaction.type.in_(INCOME_TYPES),
        ).scalar() or 0
        payables = db.query(func.sum(Transaction.amount_due)).filter(
            *base_filters,
            ~Transaction.type.in_(INCOME_TYPES),
        ).scalar() or 0
        return {
            "receivables": float(receivables),
            "payables": float(payables),
        }
