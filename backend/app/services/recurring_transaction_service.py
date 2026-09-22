"""Generation logic for recurring transaction templates."""

import asyncio
import calendar
import logging
from contextlib import suppress
from datetime import date, timedelta

from sqlalchemy.orm import Session

from backend.app.core.database import SessionLocal
from backend.app.models.schema import Transaction


logger = logging.getLogger(__name__)
SUPPORTED_FREQUENCIES = {"weekly", "monthly", "yearly"}


def next_occurrence_date(current: date, frequency: str) -> date:
    """Return the next weekly, monthly, or yearly occurrence date."""
    if frequency == "weekly":
        return current + timedelta(days=7)

    if frequency == "monthly":
        year = current.year + (1 if current.month == 12 else 0)
        month = 1 if current.month == 12 else current.month + 1
        day = min(current.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)

    if frequency == "yearly":
        day = min(current.day, calendar.monthrange(current.year + 1, current.month)[1])
        return date(current.year + 1, current.month, day)

    raise ValueError(f"Unsupported recurring frequency: {frequency}")


def prepare_schedule(
    transaction_date: date | None,
    is_recurring: bool,
    frequency: str | None,
    requested_next_run: date | None,
) -> tuple[str | None, date | None]:
    """Normalize recurrence fields before a transaction is saved."""
    if not is_recurring:
        return None, None

    if frequency not in SUPPORTED_FREQUENCIES:
        raise ValueError("Recurring transactions require a weekly, monthly, or yearly frequency.")

    first_date = requested_next_run or next_occurrence_date(
        transaction_date or date.today(),
        frequency,
    )
    return frequency, first_date


class RecurringTransactionService:
    """Creates due occurrences and advances their recurring templates."""

    @staticmethod
    def generate_due(
        db: Session,
        as_of: date | None = None,
        user_id: str | None = None,
    ) -> int:
        run_date = as_of or date.today()
        query = db.query(Transaction).filter(
            Transaction.is_recurring.is_(True),
            Transaction.next_run_date.isnot(None),
            Transaction.next_run_date <= run_date,
        )
        if user_id:
            query = query.filter(Transaction.user_id == user_id)

        templates = query.order_by(Transaction.next_run_date.asc()).all()
        generated_count = 0

        for template in templates:
            frequency = template.frequency
            if frequency not in SUPPORTED_FREQUENCIES:
                logger.warning(
                    "Skipping recurring transaction %s with invalid frequency %r",
                    template.id,
                    frequency,
                )
                continue

            due_date = template.next_run_date
            outstanding_amount = template.amount_due or 0
            payment_due_offset = (
                max((template.due_date - template.date).days, 0)
                if outstanding_amount > 0 and template.due_date and template.date
                else 0
            )
            occurrences_processed = 0

            # The limit prevents a malformed or very old schedule from creating
            # an unbounded number of rows in one scheduler pass.
            while due_date and due_date <= run_date and occurrences_processed < 120:
                exists = db.query(Transaction.id).filter(
                    Transaction.recurring_parent_id == template.id,
                    Transaction.date == due_date,
                ).first()

                if not exists:
                    db.add(
                        Transaction(
                            user_id=template.user_id,
                            amount=template.amount,
                            quantity=template.quantity,
                            category=template.category,
                            type=template.type,
                            gst_amount=template.gst_amount,
                            description=template.description,
                            date=due_date,
                            amount_paid=template.amount_paid,
                            amount_due=template.amount_due,
                            due_date=(
                                due_date + timedelta(days=payment_due_offset)
                                if outstanding_amount > 0
                                else None
                            ),
                            is_recurring=False,
                            recurring_parent_id=template.id,
                        )
                    )
                    generated_count += 1

                due_date = next_occurrence_date(due_date, frequency)
                template.next_run_date = due_date
                occurrences_processed += 1

        db.commit()
        return generated_count


async def run_recurring_scheduler(interval_seconds: int = 60) -> None:
    """Run the recurrence generator periodically without an extra dependency."""
    while True:
        db = SessionLocal()
        try:
            generated = RecurringTransactionService.generate_due(db)
            if generated:
                logger.info("Generated %s recurring transaction(s).", generated)
        except asyncio.CancelledError:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("Recurring transaction scheduler pass failed.")
        finally:
            db.close()

        await asyncio.sleep(interval_seconds)


async def stop_scheduler(task: asyncio.Task | None) -> None:
    if task is None:
        return
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
