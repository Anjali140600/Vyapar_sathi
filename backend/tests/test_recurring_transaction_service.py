from datetime import date
import unittest

from backend.app.services.recurring_transaction_service import (
    next_occurrence_date,
    prepare_schedule,
)


class RecurringTransactionServiceTests(unittest.TestCase):
    def test_weekly_recurrence(self) -> None:
        self.assertEqual(
            next_occurrence_date(date(2026, 9, 7), "weekly"),
            date(2026, 9, 14),
        )

    def test_monthly_recurrence_handles_month_end(self) -> None:
        self.assertEqual(
            next_occurrence_date(date(2024, 1, 31), "monthly"),
            date(2024, 2, 29),
        )

    def test_yearly_recurrence_handles_leap_day(self) -> None:
        self.assertEqual(
            next_occurrence_date(date(2024, 2, 29), "yearly"),
            date(2025, 2, 28),
        )

    def test_non_recurring_schedule_clears_recurring_fields(self) -> None:
        self.assertEqual(
            prepare_schedule(
                date(2026, 9, 7),
                False,
                "monthly",
                date(2026, 10, 7),
            ),
            (None, None),
        )

    def test_recurring_schedule_derives_first_run_date(self) -> None:
        self.assertEqual(
            prepare_schedule(
                date(2026, 9, 7),
                True,
                "monthly",
                None,
            ),
            ("monthly", date(2026, 10, 7)),
        )


if __name__ == "__main__":
    unittest.main()
